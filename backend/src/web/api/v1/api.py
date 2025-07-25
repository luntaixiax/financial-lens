from fastapi import APIRouter
from src.web.api.v1.endpoints import (
    sample,
    misc,
    entity,
    acct,
    journal,
    item,
    sales,
    purchase,
    expense,
    property,
    shares,
    reporting,
    management,
    settings
)

api_router = APIRouter()
api_router.include_router(management.router)
api_router.include_router(settings.router)
api_router.include_router(sample.router)
api_router.include_router(misc.router)
api_router.include_router(entity.router)
api_router.include_router(acct.router)
api_router.include_router(journal.router)
api_router.include_router(item.router)
api_router.include_router(sales.router)
api_router.include_router(purchase.router)
api_router.include_router(expense.router)
api_router.include_router(property.router)
api_router.include_router(reporting.router)
api_router.include_router(shares.router)