from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import Response

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/router_test")
def router_test() -> str:
    return "Hello, router tester here"
