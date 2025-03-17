
from datetime import datetime
from src.app.dao.backup import backupDao


class BackupService:
    
    @classmethod
    def list_backup_ids(cls) -> list[str]:
        return backupDao.list_backup_ids()
    
    @classmethod
    def backup(cls, backup_id: str | None) -> str:
        # use current timestamp if not given backup id
        backup_id = backup_id or datetime.now().strftime('%Y%m%dT%H%M%S')
        
        # backup database
        backupDao.backup_database(backup_id)
        # backup files
        backupDao.backup_files(backup_id)
        
        return backup_id
    
    @classmethod
    def restore(cls, backup_id: str):
        
        # restore files
        backupDao.restore_files(backup_id)
        # restore database
        backupDao.restore_database(backup_id)
        