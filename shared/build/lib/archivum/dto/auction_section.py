from dataclasses import dataclass
from .auction_listing import AuctionListingDto


@dataclass(slots=True)
class AuctionSectionDto:
    sectionTitle: str
    listings: list[AuctionListingDto]
