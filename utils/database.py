"""
utils/database.py
-----------------
Database layer for the Expo Scraper project.

Responsibilities:
    - Create SQLAlchemy engine + sessionmaker
    - Define the `expos` table as an ORM model
    - init_db()        -> create tables
    - save_expos(...)  -> upsert (dedupe on source_url)
    - get_expos(...)   -> filtered query returning list[dict]
    - count_expos()    -> quick row count
    - delete_all_expos() -> wipe table (dev only)

Design notes:
    - Uses SQLAlchemy 2.x style (DeclarativeBase, Mapped, mapped_column)
    - Works with SQLite (dev) and PostgreSQL (prod) without code changes
    - Upsert is done in Python for portability (SQLite + Postgres)
    - All public functions open/close their own session (safe for CLI use)
    - Logging uses loguru `{}` style (NOT printf `%s`)
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterable, Iterator, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from config.settings import DB_URL, SQL_ECHO
from utils.logger import get_logger

log = get_logger(__name__)


# ===========================================================================
# Engine + Session
# ===========================================================================
def _make_engine(url: str = DB_URL, echo: bool = SQL_ECHO) -> Engine:
    """Create the SQLAlchemy engine with sensible defaults."""
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # Needed for SQLite when used from multiple threads (Streamlit)
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    return engine


ENGINE: Engine = _make_engine()
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Context manager that commits on success and rolls back on error.

    Usage:
        with session_scope() as s:
            s.add(obj)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ===========================================================================
# ORM Base + Model
# ===========================================================================
class Base(DeclarativeBase):
    pass


class ExpoTable(Base):
    """ORM model for the `expos` table."""

    __tablename__ = "expos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Source identity
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)

    # Core fields
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    sub_category: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Location
    venue: Mapped[Optional[str]] = mapped_column(String(300))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(120))
    state: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[Optional[str]] = mapped_column(String(120))

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Money
    fees: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(10))

    # Contact / info
    organizer: Mapped[Optional[str]] = mapped_column(String(300))
    contact_email: Mapped[Optional[str]] = mapped_column(String(200))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(1000))

    # Extra
    image_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Housekeeping
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    event_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Helpful indexes for the dashboard
    __table_args__ = (
        Index("idx_expos_city", "city"),
        Index("idx_expos_category", "category"),
        Index("idx_expos_start_date", "start_date"),
        Index("idx_expos_source", "source"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM row to a plain dict (JSON-safe)."""
        return {
            "id": self.id,
            "source": self.source,
            "source_url": self.source_url,
            "name": self.name,
            "category": self.category,
            "sub_category": self.sub_category,
            "description": self.description,
            "venue": self.venue,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "fees": self.fees,
            "currency": self.currency,
            "organizer": self.organizer,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "website": self.website,
            "image_url": self.image_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ExpoTable id={self.id} name={self.name!r} city={self.city!r}>"


# ===========================================================================
# Public API
# ===========================================================================
def init_db() -> None:
    """Create all tables if they don't exist. Safe to call multiple times."""
    Base.metadata.create_all(bind=ENGINE)
    log.info("Database initialised at {}", DB_URL)


def _to_columns(record: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize an incoming dict so it only contains valid ORM columns
    and coerces date-strings into date objects.
    """
    valid_cols = {c.name for c in ExpoTable.__table__.columns}
    data = {k: v for k, v in record.items() if k in valid_cols}

    for key in ("start_date", "end_date"):
        val = data.get(key)
        if isinstance(val, str) and val:
            try:
                data[key] = datetime.fromisoformat(val).date()
            except ValueError:
                data[key] = None
        elif isinstance(val, datetime):
            data[key] = val.date()

    return data


def save_expos(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    """
    Upsert a batch of expo dicts into the DB.

    Dedupe key: `source_url`. Existing rows are updated only if the incoming
    `event_hash` differs (or if no hash was provided and any field changed).

    Returns a summary dict: {"inserted": n, "updated": n, "skipped": n}
    """
    inserted = updated = skipped = 0

    with session_scope() as session:
        for raw in records:
            data = _to_columns(raw)
            url = data.get("source_url")
            if not url:
                log.warning("Skipping record without source_url: {}", data.get("name"))
                skipped += 1
                continue

            existing: ExpoTable | None = session.execute(
                select(ExpoTable).where(ExpoTable.source_url == url)
            ).scalar_one_or_none()

            if existing is None:
                session.add(ExpoTable(**data))
                inserted += 1
                continue

            incoming_hash = data.get("event_hash")
            if incoming_hash and existing.event_hash == incoming_hash:
                skipped += 1
                continue

            # Update mutable fields on the existing row
            for key, value in data.items():
                if key in {"id", "scraped_at"}:
                    continue
                setattr(existing, key, value)
            updated += 1

    log.info(
        "save_expos -> inserted={} updated={} skipped={}",
        inserted,
        updated,
        skipped,
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def get_expos(
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    start_after: Optional[date] = None,
    end_before: Optional[date] = None,
    max_fee: Optional[float] = None,
    limit: Optional[int] = None,
    order_by: str = "start_date",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    """
    Query expos with optional filters. Returns list of dicts (JSON-safe).

    All filters are AND-combined.
    """
    stmt = select(ExpoTable)

    if city:
        stmt = stmt.where(ExpoTable.city.ilike(f"%{city}%"))
    if state:
        stmt = stmt.where(ExpoTable.state.ilike(f"%{state}%"))
    if country:
        stmt = stmt.where(ExpoTable.country.ilike(f"%{country}%"))
    if category:
        stmt = stmt.where(ExpoTable.category.ilike(f"%{category}%"))
    if source:
        stmt = stmt.where(ExpoTable.source == source)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (ExpoTable.name.ilike(like))
            | (ExpoTable.description.ilike(like))
            | (ExpoTable.venue.ilike(like))
        )
    if start_after:
        stmt = stmt.where(ExpoTable.start_date >= start_after)
    if end_before:
        stmt = stmt.where(ExpoTable.end_date <= end_before)
    if max_fee is not None:
        stmt = stmt.where(
            (ExpoTable.fees.is_(None)) | (ExpoTable.fees <= max_fee)
        )

    order_col = getattr(ExpoTable, order_by, ExpoTable.start_date)
    stmt = stmt.order_by(order_col.asc() if ascending else order_col.desc())

    if limit:
        stmt = stmt.limit(limit)

    with session_scope() as session:
        rows = session.execute(stmt).scalars().all()
        return [r.to_dict() for r in rows]


def count_expos() -> int:
    """Return total number of rows in the expos table."""
    with session_scope() as session:
        return int(session.execute(select(func.count(ExpoTable.id))).scalar_one())


def delete_all_expos() -> int:
    """
    Delete every row from expos. Use only in dev/tests.
    Returns number of rows deleted.
    """
    with session_scope() as session:
        count = session.execute(select(func.count(ExpoTable.id))).scalar_one()
        session.query(ExpoTable).delete()
    log.warning("Deleted {} rows from expos", count)
    return int(count)


def list_cities() -> list[str]:
    """Return distinct cities present in the DB."""
    with session_scope() as session:
        rows = session.execute(
            select(ExpoTable.city).where(ExpoTable.city.isnot(None)).distinct()
        ).scalars().all()
        return sorted(c for c in rows if c)


def list_categories() -> list[str]:
    """Return distinct categories present in the DB."""
    with session_scope() as session:
        rows = session.execute(
            select(ExpoTable.category).where(ExpoTable.category.isnot(None)).distinct()
        ).scalars().all()
        return sorted(c for c in rows if c)


def list_sources() -> list[str]:
    """Return distinct sources present in the DB."""
    with session_scope() as session:
        rows = session.execute(
            select(ExpoTable.source).distinct()
        ).scalars().all()
        return sorted(c for c in rows if c)


# ===========================================================================
# Self-test
# ===========================================================================
if __name__ == "__main__":
    init_db()

    sample = [
        {
            "source": "exhibition_globe",
            "source_url": "https://example.com/test-ahmedabad-expo",
            "name": "Demo Tech Expo 2026",
            "category": "Technical",
            "sub_category": "Technology & IT",
            "description": "A sample expo for testing the pipeline.",
            "venue": "Mahatma Mandir",
            "address": "Sector 13, Gandhinagar",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "country": "India",
            "start_date": "2026-10-15",
            "end_date": "2026-10-18",
            "fees": 500.0,
            "currency": "INR",
            "organizer": "Demo Org",
            "website": "https://example.com",
        },
        {
            "source": "exhibition_globe",
            "source_url": "https://example.com/test-vadodara-food-expo",
            "name": "Vadodara Food Festival 2026",
            "category": "Non-Technical",
            "sub_category": "Food & Agriculture",
            "description": "Annual food festival in Vadodara.",
            "venue": "Sayaji Baug",
            "city": "Vadodara",
            "state": "Gujarat",
            "country": "India",
            "start_date": "2026-11-20",
            "end_date": "2026-11-22",
            "fees": 0.0,
            "currency": "INR",
        },
    ]

    print("Upserting 2 sample records...")
    print(save_expos(sample))

    print("\nTotal rows:", count_expos())
    print("Cities:", list_cities())
    print("Categories:", list_categories())
    print("Sources:", list_sources())

    rows = get_expos(city="Ahmedabad")
    print(f"\nFound {len(rows)} in Ahmedabad:")
    for r in rows:
        print(f" - {r['name']} | {r['city']} | {r['start_date']} | {r['category']}")