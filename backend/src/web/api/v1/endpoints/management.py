from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import Response
from src.app.service.backup import BackupService


router = APIRouter(prefix="/management", tags=["management"])

@router.post("/init_db")
def init_db():
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
    

@router.get("/list_backup_ids")
def list_backup_ids() -> list[str]:
    return BackupService.list_backup_ids()

@router.post("/backup")
def backup(backup_id: str | None = None) -> str:
    return BackupService.backup(backup_id)

@router.post("/restore")
def restore(backup_id: str):
    BackupService.restore(backup_id)
