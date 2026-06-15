"""
Daily score persistence.

Bridges the pure scoring engine (scoring.py) and the DailyScore table
(database.py). On each chat we recompute the user's MAI scores from their latest
user_service context and upsert today's row — keeping the current day fresh while
accruing one snapshot per day for drift baselines (SCORING.md Rule 14) and any
future dashboard/trend views.

Fail-safe: any DB error falls back to an in-memory computation so the chat flow
is never broken (mirrors user_context's fail-open behavior).
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from database import db_manager, DailyScore
from scoring import (
    compute_scores,
    deserialize_scores,
    format_scores_block,
    inputs_from_context,
    serialize_scores,
)

logger = logging.getLogger(__name__)


def upsert_daily_scores(
    ctx: Optional[Dict[str, Any]],
    core_user_uuid: Optional[str],
    on_date: Optional[date] = None,
) -> str:
    """Compute scores from ctx, persist today's snapshot, return the prompt block.

    Without a user identity (anonymous chat) scores are computed but not stored.
    """
    scores = compute_scores(inputs_from_context(ctx))
    block = format_scores_block(scores)

    if not core_user_uuid:
        return block

    on_date = on_date or date.today()
    try:
        with db_manager.get_session() as session:
            row = (
                session.query(DailyScore)
                .filter_by(core_user_uuid=core_user_uuid, score_date=on_date)
                .first()
            )
            payload = serialize_scores(scores)
            if row:
                row.scores = payload  # refresh today's snapshot
            else:
                session.add(
                    DailyScore(
                        core_user_uuid=core_user_uuid,
                        score_date=on_date,
                        scores=payload,
                    )
                )
    except Exception as e:
        logger.warning("Failed to persist daily scores for %s: %s", core_user_uuid, e)

    return block


def get_daily_scores(
    core_user_uuid: str, on_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """Return a stored day's serialized scores, or None if absent."""
    if not core_user_uuid:
        return None
    on_date = on_date or date.today()
    try:
        with db_manager.get_session() as session:
            row = (
                session.query(DailyScore)
                .filter_by(core_user_uuid=core_user_uuid, score_date=on_date)
                .first()
            )
            return row.scores if row else None
    except Exception as e:
        logger.warning("Failed to read daily scores for %s: %s", core_user_uuid, e)
        return None


def get_score_history(
    core_user_uuid: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return up to `days` most recent stored daily snapshots, oldest first.

    Intended for drift baselines and trend views.
    """
    if not core_user_uuid:
        return []
    try:
        with db_manager.get_session() as session:
            rows = (
                session.query(DailyScore)
                .filter_by(core_user_uuid=core_user_uuid)
                .order_by(DailyScore.score_date.desc())
                .limit(days)
                .all()
            )
            return [r.to_dict() for r in reversed(rows)]
    except Exception as e:
        logger.warning("Failed to read score history for %s: %s", core_user_uuid, e)
        return []
