import logging
import pytest
from unittest import mock
from pathlib import Path
import sqlalchemy
from src.app.dao.orm import SQLModel


@pytest.fixture(scope='module')
def engine():
    # setup a sqlite database
    cur_path = Path() / 'test.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    SQLModel.metadata.create_all(engine)
    logging.info("Created SQLite Engine: ", engine)
    
    yield engine
        
    # TODO: delete the sqlite db
    

@pytest.fixture(scope='module')
def engine_with_test_choa(engine):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine
        
        from src.app.service.chart_of_accounts import AcctService
        
        AcctService.init()
        
    yield engine