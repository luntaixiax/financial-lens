import logging
from pathlib import Path
import pytest
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from src.app.dao.orm import SQLModel

# @pytest.fixture(scope='module')
# def engine():
#     from src.app.dao.connection import get_engine

#     engine = get_engine()
#     SQLModel.metadata.create_all(engine)
    
#     yield engine

@pytest.fixture(scope='module')
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
    SQLModel.metadata.create_all(engine)
    
    yield engine
        
    # rename to backup so effectively remove it from main
    # renamed = Path() / 'backup.db'
    # renamed.unlink(missing_ok=True)
    # cur_path.rename(renamed)
        
    