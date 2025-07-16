import logging
from pathlib import Path
import pytest
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqlmodel import Session

@pytest.fixture(scope='session')
def settings():
    from src.app.model.enums import CurType
    
    return {
        'preferences': {
            'base_cur': CurType.CAD,
            'default_sales_tax_rate': 0.13,
            'par_share_price': 0.01,
        }
    }

@pytest.fixture(scope='session')
def engine():
    from src.app.dao.orm import SQLModelWithSort
    
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
    
    # setup a sqlite database
    cur_path = Path() / 'test.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    if not database_exists(engine.url):
        create_database(engine.url)
        
    SQLModelWithSort.metadata.create_all(engine)
    
    yield engine
    
    drop_database(engine.url)
        
@pytest.fixture(scope='session')
def test_session(engine):
    """Create a test session for each test"""
    with Session(engine) as session:
        yield session
        

#### DAO objects####

@pytest.fixture(scope='session')
def test_contact_dao(test_session):
    from src.app.dao.entity import contactDao
    return contactDao(test_session)

@pytest.fixture(scope='session')
def test_customer_dao(test_session):
    from src.app.dao.entity import customerDao
    return customerDao(test_session)

@pytest.fixture(scope='session')
def test_item_dao(test_session):
    from src.app.dao.invoice import itemDao
    return itemDao(test_session)

@pytest.fixture(scope='session')
def test_invoice_dao(test_session):
    from src.app.dao.invoice import invoiceDao
    return invoiceDao(test_session) 

@pytest.fixture(scope='session')
def test_journal_dao(test_session):
    from src.app.dao.journal import journalDao
    return journalDao(test_session)
    
@pytest.fixture(scope='session')
def test_acct_dao(test_session):
    from src.app.dao.accounts import acctDao
    return acctDao(test_session)

@pytest.fixture(scope='session')
def test_chart_of_acct_dao(test_session):
    from src.app.dao.accounts import chartOfAcctDao
    return chartOfAcctDao(test_session)

### Service objects ###

@pytest.fixture(scope='session')
def acct_service(test_acct_dao, test_chart_of_acct_dao):
    from src.app.service.acct import AcctService
    
    return AcctService(
        acct_dao=test_acct_dao,
        chart_of_acct_dao=test_chart_of_acct_dao,
    )