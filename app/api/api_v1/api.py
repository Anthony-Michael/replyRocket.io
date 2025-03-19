from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, campaigns, emails, follow_ups, stats, users, health, db_monitor

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(follow_ups.router, prefix="/follow-ups", tags=["follow-ups"])
api_router.include_router(stats.router, prefix="/stats", tags=["statistics"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(db_monitor.router, prefix="/db-monitor", tags=["database", "admin"]) 