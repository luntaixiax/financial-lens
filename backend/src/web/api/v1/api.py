from fastapi import APIRouter
from src.web.api.v1.endpoints import test

api_router = APIRouter()
api_router.include_router(test.router)