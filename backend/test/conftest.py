import logging
from pathlib import Path
from unittest import mock
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
        
    SQLModelWithSort.create_table_within_collection(
        collection='user_specific',
        engine=engine
    )
    
    yield engine
    
    drop_database(engine.url)
        
@pytest.fixture(scope='session')
def test_session(engine):
    """Create a test session for each test"""
    with Session(engine) as session:
        yield session
        
@pytest.fixture(scope='module')
def session_with_basic_choa(test_session, test_acct_service, settings):
    with mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_settings.return_value = settings
        
        from src.app.model.enums import AcctType

        print("Init basic Acct and COA...")
        test_acct_service.init()
        
        yield test_session
        
        print("Tearing down Acct and COA...")
        # clean up (delete all accounts)
        for acct_type in AcctType:
            charts = test_acct_service.get_charts(acct_type)
            for chart in charts:
                accts = test_acct_service.get_accounts_by_chart(chart)
                for acct in accts:
                    test_acct_service.delete_account(
                        acct_id=acct.acct_id,
                        ignore_nonexist=True,
                        restrictive=False
                    )
                    
            # clean up (delete all chart of accounts)
            test_acct_service.delete_coa(acct_type)
            
@pytest.fixture(scope='module')
def session_with_sample_choa(session_with_basic_choa, test_acct_service, settings):
   with mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_settings.return_value = settings
        
        print("Adding sample Acct and COA...")
        test_acct_service.create_sample()
        
        yield session_with_basic_choa
        
#### DAO objects####

@pytest.fixture(scope='session')
def test_fx_dao(test_session):
    from src.app.dao.fx import fxDao
    return fxDao(test_session)

@pytest.fixture(scope='session')
def test_contact_dao(test_session):
    from src.app.dao.entity import contactDao
    return contactDao(test_session)

@pytest.fixture(scope='session')
def test_customer_dao(test_session):
    from src.app.dao.entity import customerDao
    return customerDao(test_session)

@pytest.fixture(scope='session')
def test_supplier_dao(test_session):
    from src.app.dao.entity import supplierDao
    return supplierDao(test_session)

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
def test_entity_service(test_contact_dao, test_customer_dao, test_supplier_dao):
    from src.app.service.entity import EntityService
    
    return EntityService(
        contact_dao=test_contact_dao,
        customer_dao=test_customer_dao,
        supplier_dao=test_supplier_dao,
    )

@pytest.fixture(scope='session')
def test_acct_service(test_acct_dao, test_chart_of_acct_dao):
    from src.app.service.acct import AcctService
    
    return AcctService(
        acct_dao=test_acct_dao,
        chart_of_acct_dao=test_chart_of_acct_dao,
    )
    
@pytest.fixture(scope='session')
def test_journal_service(test_journal_dao, test_acct_service):
    from src.app.service.journal import JournalService
    
    return JournalService(
        journal_dao=test_journal_dao,
        acct_service=test_acct_service,
    )
    
@pytest.fixture(scope='session')
def test_fx_service(test_fx_dao):
    from src.app.service.fx import FxService
    
    return FxService(
        fx_dao=test_fx_dao,
    )
    
@pytest.fixture(scope='session')
def test_expense_service(test_expense_dao, test_fx_service, test_acct_service, test_journal_service):
    from src.app.service.expense import ExpenseService
    
    return ExpenseService(
        expense_dao=test_expense_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
    )
    
@pytest.fixture(scope='session')
def test_property_service(test_property_dao, test_property_trans_dao, test_fx_service, test_acct_service, test_journal_service):
    from src.app.service.property import PropertyService
    
    return PropertyService(
        property_dao=test_property_dao,
        property_transaction_dao=test_property_trans_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
    )
    
@pytest.fixture(scope='session')
def test_sales_service(test_invoice_dao, test_payment_dao, test_fx_service, 
        test_acct_service, test_journal_service, test_item_service, test_entity_service):
    from src.app.service.sales import SalesService
    
    return SalesService(
        invoice_dao=test_invoice_dao,
        payment_dao=test_payment_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
        item_service=test_item_service,
        entity_service=test_entity_service,
    )
    
@pytest.fixture(scope='session')
def test_item_service(test_item_dao, test_acct_service):
    from src.app.service.item import ItemService
    
    return ItemService(
        item_dao=test_item_dao,
        acct_service=test_acct_service,    
    )

@pytest.fixture(scope='session')
def test_shares_service(test_stock_issue_dao, test_stock_repurchase_dao, test_stock_dividend_dao, test_fx_service, test_acct_service, test_journal_service):
    from src.app.service.shares import SharesService
    
    return SharesService(
        stock_issue_dao=test_stock_issue_dao,
        stock_repurchase_dao=test_stock_repurchase_dao,
        dividend_dao=test_stock_dividend_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
    )