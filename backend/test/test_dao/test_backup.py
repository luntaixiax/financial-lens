from datetime import datetime
import pytest
import os

@pytest.mark.skip(reason="not testing it online")
def test_backup():
    from src.app.dao.backup import dataDao
    
    backup_id=datetime.now().strftime('%Y%m%dT%H%M%S')
    
    dataDao.backup_database(backup_id)
    dataDao.backup_files(backup_id)
    dataDao.restore_database(backup_id)
    dataDao.restore_files(backup_id)
    
    print(dataDao.list_backup_ids())