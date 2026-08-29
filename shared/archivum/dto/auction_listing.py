from dataclasses import dataclass


@dataclass(slots=True)
class AuctionListingDto:
    lotNumber: str
    description: str
    condition: str
