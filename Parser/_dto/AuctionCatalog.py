from dataclasses import dataclass
from .AuctionDetails import AuctionDetailsDto
from .AuctionSection import AuctionSectionDto

@dataclass(slots=True)
class AuctionCatalogDto:
    details: AuctionDetailsDto
    sections: list[AuctionSectionDto]