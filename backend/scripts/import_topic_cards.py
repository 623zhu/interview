"""Upsert topic cards from backend/data/topic_cards.json."""

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

SEED_PATH = BACKEND_DIR / "data" / "topic_cards.json"

def load_cards() -> list[TopicCard]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("seed file must be a JSON array")
    return [TopicCard.model_validate(item) for item in raw]


async def import_cards() -> None:
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
        f"imported {len(cards)} cards: "
        f"created={created} updated={updated} skipped={skipped}"
    )


if __name__ == "__main__":
    asyncio.run(import_cards())
