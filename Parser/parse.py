import json
from pathlib import Path

from dotenv import load_dotenv

from _core import extract_file, get_client, get_extract_config_id, map_to_catalog_dto
from _db import get_supabase_client, get_auction_company_id, save_catalog
from _dto import AuctionCatalogDto

INPUT_DIR = Path("Input")
OUTPUT_DIR = Path("Output")


def save_raw_json(data: dict, output_path: Path) -> None:
    """Save the raw extracted JSON to the output folder."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


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