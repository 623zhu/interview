"""Upsert topic cards from backend/data/topic_cards/*.json."""

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import settings
from app.infrastructure.mysql import create_engine, create_mysql_session_factory
from app.models.topic_cards import TopicCard as TopicCardRow
from app.schemas.topic_cards import TopicCard

SEED_DIR = BACKEND_DIR / "data" / "topic_cards"


def seed_files() -> list[Path]:
    if not SEED_DIR.is_dir():
        raise FileNotFoundError(f"seed directory not found: {SEED_DIR}")
    files = sorted(path for path in SEED_DIR.glob("*.json") if path.is_file())
    if not files:
        raise FileNotFoundError(f"no JSON seed files in {SEED_DIR}")
    return files


def load_cards() -> list[TopicCard]:
    cards: list[TopicCard] = []
    seen: set[str] = set()
    for path in seed_files():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must be a JSON array")
        for item in raw:
            card = TopicCard.model_validate(item)
            if card.key in seen:
                raise ValueError(f"duplicate key {card.key!r} in {path.name}")
            seen.add(card.key)
            cards.append(card)
    return cards


async def import_cards() -> None:
    files = seed_files()
    cards = load_cards()
    engine = create_engine(settings)
    session_factory = create_mysql_session_factory(engine)
    created = updated = skipped = 0
    async with session_factory() as session:
        for card in cards:
            digest = card.content_hash()
            payload = card.model_dump()
            result = await session.execute(
                select(TopicCardRow).where(TopicCardRow.key == card.key)
            )
            row = result.scalar_one_or_none()
            if row is None:
                session.add(TopicCardRow(**payload, content_hash=digest))
                created += 1
                continue
            if row.content_hash == digest and row.status == card.status:
                skipped += 1
                continue
            for field, value in payload.items():
                setattr(row, field, value)
            row.content_hash = digest
            updated += 1
        await session.commit()
    await engine.dispose()
    print(
        f"imported {len(cards)} cards from {len(files)} files: "
        f"created={created} updated={updated} skipped={skipped}"
    )


if __name__ == "__main__":
    asyncio.run(import_cards())
