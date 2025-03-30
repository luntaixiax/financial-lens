from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import Response


router = APIRouter(prefix="/test", tags=["test"])

@router.get("/router_test")
def router_test() -> str:
    return "Hello, router tester here"

@router.post("/init_sample")
def init():
    from src.app.dao.orm import SQLModelWithSort
    from src.app.dao.connection import get_engine
    from src.app.service.acct import AcctService
    from src.app.service.journal import JournalService
    from src.app.service.entity import EntityService
    from src.app.service.item import ItemService
    from src.app.service.sales import SalesService
    from src.app.service.purchase import PurchaseService
    from src.app.service.expense import ExpenseService
    from src.app.service.property import PropertyService
    
    SQLModelWithSort.metadata.create_all(get_engine())
    # create basic account structure *standard
    AcctService.init()
    # create additional sample accounts
    AcctService.create_sample()
    # create sample journals
    JournalService.create_sample()
    # create sample customer
    EntityService.create_sample()
    # crete item items
    ItemService.create_sample()
    # create sample sales invoice
    SalesService.create_sample()
    # create sample purchase invoice
    PurchaseService.create_sample()
    # create sample expense
    ExpenseService.create_sample()
    # create property sample
    PropertyService.create_sample()
    

@router.delete("/clear_sample")
def init():
    from src.app.dao.connection import get_engine
    from src.app.service.acct import AcctService
    from src.app.service.journal import JournalService
    from src.app.service.entity import EntityService
    from src.app.service.item import ItemService
    from src.app.service.sales import SalesService
    from src.app.service.purchase import PurchaseService
    from src.app.service.expense import ExpenseService
    from src.app.service.property import PropertyService
    
    ExpenseService.clear_sample()
    SalesService.clear_sample()
    PurchaseService.clear_sample()
    ItemService.clear_sample()
    JournalService.clear_sample()
    EntityService.clear_sample()
    PropertyService.clear_sample()
    AcctService.clear_sample()
    
    
