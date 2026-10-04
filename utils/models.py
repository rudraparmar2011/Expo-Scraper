from datetime import date
from typing import Optional

from pydantic import BaseModel, HttpUrl, model_validator


class Expo(BaseModel):
    source: str
    source_url: HttpUrl
    name: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    fees: Optional[float] = None  # None = free or unknown
    currency: Optional[str] = None
    organizer: Optional[str] = None
    website: Optional[str] = None

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.start_date, self.end_date = self.end_date, self.start_date
        return self
