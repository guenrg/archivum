import json
import os
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud import LlamaCloud

from _db import get_supabase_client, get_auction_company_id, save_catalog
from _dto import AuctionCatalogDto, AuctionDetailsDto, AuctionSectionDto, AuctionListingDto

INPUT_DIR = Path("Input")
OUTPUT_DIR = Path("Output")


def get_client() -> LlamaCloud:
    """Create a LlamaCloud client using the API key from the environment."""
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY is not set. Add it to your .env file or environment.")
    
    return LlamaCloud(api_key=api_key)


def get_extract_config_id() -> str:
    """Read the saved Extract (v2) configuration ID from the environment."""
    config_id = os.getenv("LLAMA_EXTRACT_CONFIG_ID")
    if not config_id:
        raise ValueError("LLAMA_EXTRACT_CONFIG_ID is not set. Add it to your .env file or environment.")
    return config_id


def extract_file(client: LlamaCloud, config_id: str, file_path: Path) -> dict:
    """Upload a file and run LlamaExtract (v2) on it, returning the extracted data as a dict."""
    # Upload the file to LlamaCloud
    uploaded = client.files.create(file=file_path, purpose="extract")

    # Run the extraction job with the saved configuration and wait for completion
    job = client.extract.run(
        file_input=uploaded.id,
        configuration_id=config_id,
    )

    if str(job.status).upper() not in ("SUCCESS", "COMPLETED"):
        raise RuntimeError(f"Extraction job {job.id} finished with status '{job.status}': {job.error_message}")

    result = job.extract_result
    if result is None:
        raise RuntimeError(f"Extraction job {job.id} completed but returned no result.")
    if isinstance(result, list):
        # Per-page/per-record extractions return a list; a single-document
        # catalog extraction is expected to yield one record.
        if len(result) == 1:
            return result[0]
        raise RuntimeError(f"Extraction job {job.id} returned {len(result)} records; expected a single document result.")
    return result


def save_raw_json(data: dict, output_path: Path) -> None:
    """Save the raw extracted JSON to the output folder."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def map_to_catalog_dto(data: dict) -> AuctionCatalogDto:
    """Map raw extracted JSON into an AuctionCatalogDto."""
    publication_details = data.get("publication_details", {}) or {}
    details = AuctionDetailsDto(
        publicationNumber=publication_details.get("publication_number", ""),
        publicationDate=publication_details.get("publication_date", ""),
    )

    sections = []
    for section in data.get("sections", []) or []:
        listings = [
            AuctionListingDto(
                lotNumber=listing.get("lot_number", ""),
                description=listing.get("description", ""),
                condition=listing.get("condition", ""),
            )
            for listing in section.get("listings", []) or []
        ]
        sections.append(
            AuctionSectionDto(
                sectionTitle=section.get("section_title", ""),
                listings=listings,
            )
        )

    return AuctionCatalogDto(details=details, sections=sections)


def main():
    load_dotenv()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_DIR.exists():
        print(f"Error: Input directory '{INPUT_DIR}' does not exist.")
        return

    print("Connecting to LlamaCloud...")
    client = get_client()
    config_id = get_extract_config_id()
    print(f"Using extract configuration: {config_id}")

    print("Connecting to Supabase...")
    supabase_client = get_supabase_client()
    company_id = get_auction_company_id()
    print(f"Using auction company ID: {company_id}")

    catalogs: list[AuctionCatalogDto] = []
    files_processed = 0

    for file_path in INPUT_DIR.iterdir():
        if not file_path.is_file():
            continue

        print(f"\nProcessing: {file_path.name}")
        try:
            # Extract structured data via LlamaExtract (v2)
            data = extract_file(client, config_id, file_path)

            # Save the raw extracted JSON to the output folder
            output_file_path = OUTPUT_DIR / f"{file_path.stem}.json"
            save_raw_json(data, output_file_path)
            print(f"Saved extracted JSON to: {output_file_path}")

            # Map extracted data into DTOs
            catalog = map_to_catalog_dto(data)
            catalogs.append(catalog)
            print(
                f"Mapped catalog: publication {catalog.details.publicationNumber}, "
                f"{len(catalog.sections)} section(s)"
            )

            files_processed += 1
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    # Persist catalogs to Supabase
    catalogs_saved = 0
    for catalog in catalogs:
        try:
            auction_id = save_catalog(supabase_client, catalog, company_id)
            listing_count = sum(len(section.listings) for section in catalog.sections)
            print(
                f"Saved auction {auction_id} to Supabase "
                f"(publication {catalog.details.publicationNumber}, {listing_count} listing(s))"
            )
            catalogs_saved += 1
        except Exception as e:
            print(f"Error saving catalog (publication {catalog.details.publicationNumber}) to Supabase: {e}")

    print(f"\nFinished processing. Total files successfully extracted: {files_processed}")
    print(f"Total catalogs saved to Supabase: {catalogs_saved}")


if __name__ == "__main__":
    main()