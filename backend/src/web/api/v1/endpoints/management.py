from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from src.app.service.backup import BackupService
from src.web.dependency.service import get_backup_service

router = APIRouter(prefix="/management", tags=["management"])

@router.post("/init_db")
def init_db(
    backup_service: BackupService = Depends(get_backup_service)
):
    backup_service.init_db()
    
@router.get("/list_backup_ids")
def list_backup_ids(
    backup_service: BackupService = Depends(get_backup_service)
) -> list[str]:
    return backup_service.list_backup_ids()

@router.post("/backup")
def backup(
    backup_id: str | None = None,
    backup_service: BackupService = Depends(get_backup_service)
) -> str:
    return backup_service.backup(backup_id)

@router.post("/restore")
def restore(
    backup_id: str,
    backup_service: BackupService = Depends(get_backup_service)
):
    backup_service.restore(backup_id)
