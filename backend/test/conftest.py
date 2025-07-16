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
def test_journal_dao(test_session, engine):
    from src.app.dao.journal import journalDao
    return journalDao(test_session, engine)
    
@pytest.fixture(scope='session')
def test_acct_dao(test_session):
    from src.app.dao.accounts import acctDao
    return acctDao(test_session)

@pytest.fixture(scope='session')
def test_chart_of_acct_dao(engine):
    from src.app.dao.accounts import chartOfAcctDao
    return chartOfAcctDao(engine)

@pytest.fixture(scope='session')
def test_expense_dao(test_session):
    from src.app.dao.expense import expenseDao
    return expenseDao(test_session)

@pytest.fixture(scope='session')
def test_payment_dao(test_session):
    from src.app.dao.payment import paymentDao
    return paymentDao(test_session)

@pytest.fixture(scope='session')
def test_property_dao(test_session):
    from src.app.dao.property import propertyDao
    return propertyDao(test_session)

@pytest.fixture(scope='session')
def test_property_trans_dao(test_session):
    from src.app.dao.property import propertyTransactionDao
    return propertyTransactionDao(test_session)

@pytest.fixture(scope='session')
def test_stock_issue_dao(test_session):
    from src.app.dao.shares import stockIssueDao
    return stockIssueDao(test_session)

@pytest.fixture(scope='session')
def test_stock_repurchase_dao(test_session):
    from src.app.dao.shares import stockRepurchaseDao
    return stockRepurchaseDao(test_session)

@pytest.fixture(scope='session')
def test_stock_dividend_dao(test_session):
    from src.app.dao.shares import dividendDao
    return dividendDao(test_session)

### Service objects ###

@pytest.fixture(scope='session')
def test_acct_service(test_acct_dao, test_chart_of_acct_dao):
    from src.app.service.acct import AcctService
    
    return AcctService(
        acct_dao=test_acct_dao,
        chart_of_acct_dao=test_chart_of_acct_dao,
    )