from dataclasses import dataclass
from .auction_details import AuctionDetailsDto
from .auction_section import AuctionSectionDto


@dataclass(slots=True)
class AuctionCatalogDto:
    details: AuctionDetailsDto
    sections: list[AuctionSectionDto]
