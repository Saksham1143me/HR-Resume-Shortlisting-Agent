import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from loguru import logger

from models import CandidateScore, HROverride
from utils import config 


OVERRIDE_LOG_PATH = config.LOGS_DIR / "hr_overrides.jsonl"


def apply_hr_override(
    score: CandidateScore,
    hr_user: str,
    new_total: float,
    new_recommendation: Literal["HIRE", "MAYBE", "NO_HIRE"],
    reason: str,
) -> CandidateScore:
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Override reason must be at least 10 characters. This is mandatory for compliance.")

    if not (0.0 <= new_total <= 10.0):
        raise ValueError(f"Override total must be between 0 and 10. Got: {new_total}")

    override = HROverride(
        overridden_by=hr_user,
        reason=reason.strip(),
        original_total=score.weighted_total,
        overridden_total=round(new_total, 2),
        overridden_recommendation=new_recommendation,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    score.hr_override = override

    _log_override(score, override)

    logger.info(
        f"🔧 HR Override: candidate={score.candidate_id} | "
        f"{score.weighted_total} → {new_total} | "
        f"rec={new_recommendation} | by={hr_user}"
    )

    return score


def _log_override(score: CandidateScore, override: HROverride) -> None:
    log_entry = {
        "timestamp": override.timestamp,
        "candidate_id": score.candidate_id,
        "candidate_name": score.full_name,
        "overridden_by": override.overridden_by,
        "original_total": override.original_total,
        "overridden_total": override.overridden_total,
        "original_recommendation": score.recommendation,
        "overridden_recommendation": override.overridden_recommendation,
        "reason": override.reason,
    }

    with open(OVERRIDE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def get_override_log() -> list[dict]:
    if not OVERRIDE_LOG_PATH.exists():
        return []

    entries = []
    with open(OVERRIDE_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Corrupt override log entry skipped.")

    return entries