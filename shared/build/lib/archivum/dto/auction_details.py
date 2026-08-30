from dataclasses import dataclass


@dataclass(slots=True)
class AuctionDetailsDto:
    publicationNumber: str
    publicationDate: str
