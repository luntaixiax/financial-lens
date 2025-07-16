from datetime import datetime
import pytest
import os

@pytest.mark.skip(reason="not testing it online")
def test_backup(test_data_dao):
    
    backup_id=datetime.now().strftime('%Y%m%dT%H%M%S')
    
    test_data_dao.backup_database(backup_id)
    test_data_dao.backup_files(backup_id)
    test_data_dao.restore_database(backup_id)
    test_data_dao.restore_files(backup_id)
    
    print(test_data_dao.list_backup_ids())