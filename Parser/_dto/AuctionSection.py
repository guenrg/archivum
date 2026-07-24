from dataclasses import dataclass
from .AuctionListing import AuctionListingDto

@dataclass(slots=True)
class AuctionSectionDto:
    sectionTitle: str
    listings: list[AuctionListingDto]
