from fastapi import APIRouter
from app.api.v1 import auth, users, game, battle, admin, health, questions_admin, analytics_admin

api_v1_router = APIRouter()

# Include all domain routers
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(game.router)
api_v1_router.include_router(battle.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(questions_admin.router)
api_v1_router.include_router(analytics_admin.router)
api_v1_router.include_router(health.router)

