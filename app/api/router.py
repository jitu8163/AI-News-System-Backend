from fastapi import APIRouter
from app.api import admin, auth, keywords, articles, dashboard

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(keywords.router)
api_router.include_router(articles.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
