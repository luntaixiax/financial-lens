from datetime import datetime
import pytest
import os

@pytest.mark.skip(reason="not testing it online")
def test_backup():
    from src.app.dao.backup import backupDao
    
    backup_id=datetime.now().strftime('%Y%m%dT%H%M%S')
    
    backupDao.backup_database(backup_id)
    backupDao.backup_files(backup_id)
    backupDao.restore_database(backup_id)
    backupDao.restore_files(backup_id)
    
    print(backupDao.list_backup_ids())