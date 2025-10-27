from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, facebook, tiktok, instagram, social_auth, llm, analytics
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(facebook.router)
api_router.include_router(tiktok.router)
api_router.include_router(instagram.router)
api_router.include_router(social_auth.router)
api_router.include_router(llm.router)
api_router.include_router(analytics.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
