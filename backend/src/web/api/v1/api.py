from fastapi import APIRouter
from src.web.api.v1.endpoints import (
    test,
    misc,
    entity,
    acct,
    journal,
    item,
    sales,
    purchase,
    expense
)

api_router = APIRouter()
api_router.include_router(test.router)
api_router.include_router(misc.router)
api_router.include_router(entity.router)
api_router.include_router(acct.router)
api_router.include_router(journal.router)
api_router.include_router(item.router)
api_router.include_router(sales.router)
api_router.include_router(purchase.router)
api_router.include_router(expense.router)