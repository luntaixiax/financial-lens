from fastapi import APIRouter
from src.web.api.v1.endpoints import test
from src.web.api.v1.endpoints import entity
from src.web.api.v1.endpoints import acct

api_router = APIRouter()
api_router.include_router(test.router)
api_router.include_router(entity.router)
api_router.include_router(acct.router)