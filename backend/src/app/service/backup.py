
from datetime import datetime
from src.app.dao.backup import backupDao


class BackupService:
    
    def __init__(self, backup_dao: backupDao):
        self.backup_dao = backup_dao
    
    def list_backup_ids(self) -> list[str]:
        return self.backup_dao.list_backup_ids()
    
    def backup(self, backup_id: str | None) -> str:
        # use current timestamp if not given backup id
        backup_id = backup_id or datetime.now().strftime('%Y%m%dT%H%M%S')
        
        # backup database
        self.backup_dao.backup_database(backup_id)
        # backup files
        self.backup_dao.backup_files(backup_id)
        
        return backup_id
    
    def restore(self, backup_id: str):
        
        # restore files
        self.backup_dao.restore_files(backup_id)
        # restore database
        self.backup_dao.restore_database(backup_id)
        