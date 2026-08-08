import os
import re
from datetime import datetime

from supabase import Client, create_client

from _dto import AuctionCatalogDto


def get_supabase_client() -> Client:
    """Create a Supabase client using credentials from the environment."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url:
        raise ValueError("SUPABASE_URL is not set. Add it to your .env file or environment.")
    if not key:
        raise ValueError("SUPABASE_KEY is not set. Add it to your .env file or environment.")

    return create_client(url, key)


def get_auction_company_id() -> int:
    """Read the auction company ID (bigint) from the environment."""
    company_id = os.getenv("AUCTION_COMPANY_ID")
    if not company_id:
        raise ValueError("AUCTION_COMPANY_ID is not set. Add it to your .env file or environment.")
    return int(company_id)


def _parse_auction_number(publication_number: str) -> int | None:
    """Extract an integer auction number from the publication number, if possible."""
    match = re.search(r"\d+", publication_number or "")
    return int(match.group()) if match else None


def _parse_auction_date(publication_date: str) -> str | None:
    """Try to parse the publication date into an ISO timestamp; return None if not parseable."""
    if not publication_date:
        return None

    formats = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %Y", "%m/%d/%Y")
    for fmt in formats:
        try:
            return datetime.strptime(publication_date.strip(), fmt).isoformat()
        except ValueError:
            continue
    return None


def _compose_lot_description(section_title: str, description: str, condition: str) -> str:
    """Prepend the section title and append the condition to the lot description."""
    parts = [part.strip() for part in (section_title, description, condition) if part and part.strip()]
    return " — ".join(parts)


def save_catalog(client: Client, catalog: AuctionCatalogDto, company_id: int) -> str:
    """Persist an auction catalog to Supabase. Returns the new auction's UUID."""
    auction_row = {
        "company_id": company_id,
        "auction_number": _parse_auction_number(catalog.details.publicationNumber),
        "date": _parse_auction_date(catalog.details.publicationDate),
    }

    auction_response = client.table("auction").insert(auction_row).execute()
    if not auction_response.data:
        raise RuntimeError("Failed to insert auction row: no data returned from Supabase.")

    auction_id = auction_response.data[0]["id"]

    listing_rows = []
    for section in catalog.sections:
        for listing in section.listings:
            listing_rows.append(
                {
                    "auction_id": auction_id,
                    "lot_number": listing.lotNumber,
                    "lot_description": _compose_lot_description(
                        section.sectionTitle, listing.description, listing.condition
                    ),
                }
            )

    if listing_rows:
        client.table("auction_listings").insert(listing_rows).execute()

    return auction_id