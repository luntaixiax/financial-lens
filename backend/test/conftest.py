import logging
from pathlib import Path
import pytest
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from src.app.dao.orm import SQLModelWithSort

@pytest.fixture(scope='session')
def settings():
    return {
        'preferences': {
            'base_cur': 'CAD',
            'default_sales_tax_rate': 0.13
        }
    }

@pytest.fixture(scope='session')
def engine():
    
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
    
    # setup a sqlite database
    cur_path = Path() / 'test.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    SQLModelWithSort.metadata.create_all(engine)
    
    yield engine
        
    # rename to backup so effectively remove it from main
    # renamed = Path() / 'backup.db'
    # renamed.unlink(missing_ok=True)
    # cur_path.rename(renamed)
        
    