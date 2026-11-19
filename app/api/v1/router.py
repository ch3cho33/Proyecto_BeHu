"""Agregador de routers v1."""

from fastapi import APIRouter

from app.api.v1.accounts import router as accounts_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.education import router as education_router
from app.api.v1.goals import router as goals_router
from app.api.v1.kyc import router as kyc_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.supervision import router as supervision_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.transfers import router as transfers_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(supervision_router)
api_v1_router.include_router(transfers_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(budgets_router)
api_v1_router.include_router(goals_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(scoring_router)
api_v1_router.include_router(education_router)
api_v1_router.include_router(kyc_router)
