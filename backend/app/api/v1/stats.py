"""
Aggregated cost and usage statistics endpoint.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import Job
from app.schemas.job import CostStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/costs", response_model=CostStatsResponse)
def get_cost_stats(db: Session = Depends(get_db)) -> CostStatsResponse:
    """Returns aggregated cost telemetry across all completed jobs."""
    total_jobs: int = db.query(Job).count()
    completed_jobs: int = db.query(Job).filter(Job.status == "DONE").count()

    total_spend: float = db.query(func.sum(Job.actual_cost_usd)).scalar() or 0.0
    total_in_tokens: int = db.query(func.sum(Job.input_tokens)).scalar() or 0
    total_out_tokens: int = db.query(func.sum(Job.output_tokens)).scalar() or 0
    total_whisper_mins: float = db.query(func.sum(Job.whisper_minutes)).scalar() or 0.0

    # Model spend breakdown
    model_rows = (
        db.query(Job.model_used, func.sum(Job.actual_cost_usd))
        .group_by(Job.model_used)
        .all()
    )
    spend_by_model = {model: round(spend or 0.0, 4) for model, spend in model_rows}

    return CostStatsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        total_spend_usd=round(total_spend, 4),
        total_input_tokens=total_in_tokens,
        total_output_tokens=total_out_tokens,
        total_whisper_minutes=round(total_whisper_mins, 2),
        spend_by_model=spend_by_model,
    )
