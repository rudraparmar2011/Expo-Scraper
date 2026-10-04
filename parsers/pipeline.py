"""Raw scraped dict -> validated Expo (clean -> normalise -> validate -> city filter)."""
from typing import Optional

from pydantic import ValidationError

from config import settings
from parsers.cleaner import (clean_fee, clean_text, detect_currency,
                             parse_date_range, parse_single_date)
from parsers.normalizer import classify, normalize_city, state_for_city
from utils.logger import logger
from utils.models import Expo


def build_expo(raw: dict, source: str, default_city: Optional[str] = None,
               target_cities: Optional[list] = None) -> Optional[Expo]:
    name = clean_text(raw.get("name"))
    url = clean_text(raw.get("source_url"))
    if not name or not url:
        return None

    city = normalize_city(raw.get("city")) or normalize_city(default_city)
    if target_cities and city not in target_cities:
        logger.debug(f"Skipping '{name}' (city={city})")
        return None

    if raw.get("date_text"):
        start, end = parse_date_range(raw["date_text"])
    else:
        start, end = parse_single_date(raw.get("start_date")), parse_single_date(raw.get("end_date"))
        end = end or start

    fee_raw = raw.get("fees")
    fee = clean_fee(fee_raw)
    currency = clean_text(raw.get("currency")) or detect_currency(fee_raw)
    if fee is not None and not currency:
        currency = settings.DEFAULT_CURRENCY

    description = clean_text(raw.get("description"), settings.DESCRIPTION_MAX_CHARS)
    category, sub = clean_text(raw.get("category")), clean_text(raw.get("sub_category"))
    if not category:
        category, auto_sub = classify(name, description)
        sub = sub or auto_sub

    state = clean_text(raw.get("state")) or state_for_city(city)
    country = clean_text(raw.get("country"))
    if (not country or country.upper() == "IN") and state_for_city(city):
        country = settings.DEFAULT_COUNTRY

    try:
        return Expo(
            source=source, source_url=url, name=name, category=category, sub_category=sub,
            description=description, venue=clean_text(raw.get("venue")),
            address=clean_text(raw.get("address")), city=city, state=state, country=country,
            start_date=start, end_date=end, fees=fee, currency=currency,
            organizer=clean_text(raw.get("organizer")), website=clean_text(raw.get("website")),
        )
    except ValidationError as exc:
        logger.warning(f"Dropping invalid record '{name}': {exc.errors()[0]['msg']}")
        return None
