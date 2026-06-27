from fastapi import APIRouter
from app.api.v1 import jobs, stats

api_router = APIRouter()
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
