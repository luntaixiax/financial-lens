from datetime import datetime
from unittest import mock
import pytest
import os

#@pytest.mark.skip(reason="not testing it online")
def test_backup(test_backup_dao, testing_bucket_path):
    
    with (
        mock.patch("src.app.dao.backup.get_files_bucket") as mocker_file_bucket,
        mock.patch("src.app.dao.backup.get_backup_bucket") as mocker_backup_bucket
    ):
        mocker_file_bucket.return_value = testing_bucket_path
        mocker_backup_bucket.return_value = testing_bucket_path
            
        backup_id=datetime.now().strftime('%Y%m%dT%H%M%S')
        
        test_backup_dao.backup_database(backup_id)
        test_backup_dao.backup_files(backup_id)
        test_backup_dao.restore_database(backup_id)
        test_backup_dao.restore_files(backup_id)
        
        backup_ids = test_backup_dao.list_backup_ids()
        assert len(backup_ids) == 1
        assert backup_id in backup_ids