from pathlib import Path

from llama_cloud import LlamaCloud

from archivum.config import get_key
from archivum.dto import AuctionCatalogDto, AuctionDetailsDto, AuctionSectionDto, AuctionListingDto


def get_client() -> LlamaCloud:
    """Create a LlamaCloud client using the API key from App Configuration."""
    api_key = get_key("llama_cloud_api_key")
    return LlamaCloud(api_key=api_key)


def get_extract_config_id() -> str:
    """Read the saved Extract (v2) configuration ID from App Configuration."""
    return get_key("llama_extract_config_id")


def extract_bytes(client: LlamaCloud, config_id: str, file_bytes: bytes, filename: str) -> dict:
    """Upload file bytes and run LlamaExtract (v2), returning the extracted data as a dict."""
    # Upload the file content to LlamaCloud
    uploaded = client.files.create(file=(filename, file_bytes), purpose="extract")

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


def extract_file(client: LlamaCloud, config_id: str, file_path: Path) -> dict:
    """Read a local file and run LlamaExtract (v2) on it, returning the extracted data as a dict."""
    return extract_bytes(client, config_id, file_path.read_bytes(), file_path.name)


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
