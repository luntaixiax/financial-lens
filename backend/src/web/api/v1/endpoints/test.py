from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import Response


router = APIRouter(prefix="/test", tags=["test"])

@router.get("/router_test")
def router_test() -> str:
    return "Hello, router tester here"

@router.post("/init")
def init():
    from src.app.dao.orm import SQLModel
    from src.app.dao.connection import get_engine
    from src.app.service.acct import AcctService
    from src.app.service.journal import JournalService
    
    SQLModel.metadata.create_all(get_engine())
    # create basic account structure *standard
    AcctService.init()
    # create additional sample accounts
    AcctService.create_sample()
    # create sample journals
    JournalService.create_sample()
