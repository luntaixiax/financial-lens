from fastapi import APIRouter
from src.web.api.v1.endpoints import (
    test,
    entity,
    acct,
    journal,
    sales,
    expense
)

api_router = APIRouter()
api_router.include_router(test.router)
api_router.include_router(entity.router)
api_router.include_router(acct.router)
api_router.include_router(journal.router)
api_router.include_router(sales.router)
api_router.include_router(expense.router)