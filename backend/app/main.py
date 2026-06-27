from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.router import api_router
from app.db.base import Base
from app.db.session import engine

# Auto-create tables if missing
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[DB] Initial table creation skipped or deferring to migrations: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
