from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import Response

router = APIRouter(prefix="/management", tags=["management"])

@router.post("/init_db")
def init_db():
    from src.app.dao.orm import SQLModelWithSort
    from src.app.dao.connection import get_engine
    
    SQLModelWithSort.metadata.create_all(get_engine())
    
@router.get("/list_backup_ids")
def list_backup_ids() -> list[str]:
    from src.app.service.backup import BackupService
    
    return BackupService.list_backup_ids()

@router.post("/backup")
def backup(backup_id: str | None = None) -> str:
    from src.app.service.backup import BackupService
    
    return BackupService.backup(backup_id)

@router.post("/restore")
def restore(backup_id: str):
    from src.app.service.backup import BackupService
    
    BackupService.restore(backup_id)
