from pathlib import Path
import tempfile
from unittest import mock
import pytest
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqlmodel import Session


@pytest.fixture(scope='module')
def test_user():
    from src.app.model.user import User
    
    return User(
        username='test',
        is_admin=True,
    )

@pytest.fixture(scope='module')
def engine(test_user):
    from src.app.dao.orm import SQLModelWithSort
    
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
    
    # setup a sqlite database for user specific collection
    user_db_name = f'{test_user.user_id}.db'
    cur_path = Path() / user_db_name
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    if not database_exists(engine.url):
        create_database(engine.url)
        
    SQLModelWithSort.create_table_within_collection(
        collection='user_specific',
        engine=engine
    )
    
    yield engine
    
    drop_database(engine.url)
    
@pytest.fixture(scope='module')
def common_engine():
    from src.app.dao.orm import SQLModelWithSort
    
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
    
    # setup a sqlite database for user specific collection
    cur_path = Path() / 'common.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    if not database_exists(engine.url):
        create_database(engine.url)
        
    SQLModelWithSort.create_table_within_collection(
        collection='common',
        engine=engine
    )
    
    yield engine
    
    drop_database(engine.url)
    
@pytest.fixture(scope='module')
def testing_bucket_path():
    # TODO: switch to in-memory file system
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        bucket_path = (Path(tmpdirname) / 'testing').as_posix()

        yield bucket_path
    
@pytest.fixture(scope='module')
def storage_fs(testing_bucket_path):
    from fsspec.implementations.memory import MemoryFileSystem
    from fsspec.implementations.local import LocalFileSystem
    # TODO: switch to in-memory file system
    fs = MemoryFileSystem() # in-memory file system
    fs.mkdirs(testing_bucket_path, exist_ok=True)
    
    yield fs
    
    fs.rm(testing_bucket_path, recursive=True)
    
@pytest.fixture(scope='module')
def test_common_dao_access(common_engine, storage_fs):
    from src.app.dao.connection import CommonDaoAccess
    
    with Session(common_engine) as common_session:
        yield CommonDaoAccess(
            common_engine=common_engine,
            common_session=common_session,
            file_fs=storage_fs,
            backup_fs=storage_fs
        )
    
@pytest.fixture(scope='module')
def test_dao_access(engine, common_engine, storage_fs, test_user):
    from src.app.dao.connection import UserDaoAccess
    with (
        Session(common_engine) as common_session, 
        Session(engine) as user_session
    ):
        user_dao_access = UserDaoAccess(
            user_engine=engine,
            common_engine=common_engine,
            common_session=common_session,
            user_session=user_session,
            file_fs=storage_fs,
            backup_fs=storage_fs,
            user=test_user
        )
        
        yield user_dao_access
    
@pytest.fixture(scope='module')
def test_setting_service(test_dao_access):
    from src.app.service.settings import ConfigService
    from src.app.service.files import FileService
    from src.app.dao.config import configDao
    from src.app.dao.files import fileDao
    from src.app.model.enums import CurType
    
    setting_service = ConfigService(
        file_service=FileService(file_dao=fileDao(test_dao_access)),
        config_dao=configDao(test_dao_access)
    )
    
    with (
        mock.patch.object(setting_service, "get_base_currency", return_value=CurType.CAD),
        mock.patch.object(setting_service, "get_default_tax_rate", return_value=0.13),
        mock.patch.object(setting_service, "get_par_share_price", return_value=0.01),
    ):
        
        assert setting_service.get_base_currency() == CurType.CAD
        
        
        yield setting_service
    
#### DAO objects####

@pytest.fixture(scope='module')
def test_fx_dao(test_dao_access):
    from src.app.dao.fx import fxDao
    
    return fxDao(test_dao_access)

@pytest.fixture(scope='module')
def test_backup_dao(test_dao_access):
    from src.app.dao.backup import backupDao
    return backupDao(test_dao_access)

@pytest.fixture(scope='module')
def test_contact_dao(test_dao_access):
    from src.app.dao.entity import contactDao
    return contactDao(test_dao_access)

@pytest.fixture(scope='module')
def test_customer_dao(test_dao_access):
    from src.app.dao.entity import customerDao
    return customerDao(test_dao_access)

@pytest.fixture(scope='module')
def test_supplier_dao(test_dao_access):
    from src.app.dao.entity import supplierDao
    return supplierDao(test_dao_access)

@pytest.fixture(scope='module')
def test_item_dao(test_dao_access):
    from src.app.dao.invoice import itemDao
    return itemDao(test_dao_access)

@pytest.fixture(scope='module')
def test_invoice_dao(test_dao_access):
    from src.app.dao.invoice import invoiceDao
    return invoiceDao(test_dao_access) 

@pytest.fixture(scope='module')
def test_journal_dao(test_dao_access):
    from src.app.dao.journal import journalDao
    return journalDao(test_dao_access)
    
@pytest.fixture(scope='module')
def test_acct_dao(test_dao_access):
    from src.app.dao.accounts import acctDao
    return acctDao(test_dao_access)

@pytest.fixture(scope='module')
def test_chart_of_acct_dao(test_dao_access):
    from src.app.dao.accounts import chartOfAcctDao
    return chartOfAcctDao(test_dao_access)

@pytest.fixture(scope='module')
def test_expense_dao(test_dao_access):
    from src.app.dao.expense import expenseDao
    return expenseDao(test_dao_access)

@pytest.fixture(scope='module')
def test_payment_dao(test_dao_access):
    from src.app.dao.payment import paymentDao
    return paymentDao(test_dao_access)

@pytest.fixture(scope='module')
def test_property_dao(test_dao_access):
    from src.app.dao.property import propertyDao
    return propertyDao(test_dao_access)

@pytest.fixture(scope='module')
def test_property_trans_dao(test_dao_access):
    from src.app.dao.property import propertyTransactionDao
    return propertyTransactionDao(test_dao_access)

@pytest.fixture(scope='module')
def test_stock_issue_dao(test_dao_access):
    from src.app.dao.shares import stockIssueDao
    return stockIssueDao(test_dao_access)

@pytest.fixture(scope='module')
def test_stock_repurchase_dao(test_dao_access):
    from src.app.dao.shares import stockRepurchaseDao
    return stockRepurchaseDao(test_dao_access)

@pytest.fixture(scope='module')
def test_stock_dividend_dao(test_dao_access):
    from src.app.dao.shares import dividendDao
    return dividendDao(test_dao_access)

### Service objects ###

@pytest.fixture(scope='module')
def test_entity_service(test_contact_dao, test_customer_dao, test_supplier_dao):
    from src.app.service.entity import EntityService
    
    return EntityService(
        contact_dao=test_contact_dao,
        customer_dao=test_customer_dao,
        supplier_dao=test_supplier_dao,
    )

@pytest.fixture(scope='module')
def test_acct_service(test_acct_dao, test_chart_of_acct_dao, test_setting_service):
    from src.app.service.acct import AcctService
    
    return AcctService(
        acct_dao=test_acct_dao,
        chart_of_acct_dao=test_chart_of_acct_dao,
        setting_service=test_setting_service,
    )
    
@pytest.fixture(scope='module')
def test_journal_service(test_journal_dao, test_acct_service, test_setting_service):
    from src.app.service.journal import JournalService
    
    return JournalService(
        journal_dao=test_journal_dao,
        acct_service=test_acct_service,
        setting_service=test_setting_service,
    )
    
@pytest.fixture(scope='module')
def test_fx_service(test_fx_dao, test_setting_service):
    from src.app.service.fx import FxService
    
    return FxService(
        fx_dao=test_fx_dao,
        setting_service=test_setting_service,
    )
    
@pytest.fixture(scope='module')
def test_expense_service(test_expense_dao, test_fx_service, test_acct_service, 
                         test_journal_service, test_setting_service):
    from src.app.service.expense import ExpenseService
    
    return ExpenseService(
        expense_dao=test_expense_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
        setting_service=test_setting_service,
    )
    
@pytest.fixture(scope='module')
def test_property_service(test_property_dao, test_property_trans_dao, 
                          test_fx_service, test_acct_service, test_journal_service):
    from src.app.service.property import PropertyService
    
    return PropertyService(
        property_dao=test_property_dao,
        property_transaction_dao=test_property_trans_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
    )
    
@pytest.fixture(scope='module')
def test_sales_service(test_invoice_dao, test_payment_dao, test_fx_service, 
        test_acct_service, test_journal_service, test_item_service, 
        test_entity_service, test_setting_service):
    from src.app.service.sales import SalesService
    
    return SalesService(
        invoice_dao=test_invoice_dao,
        payment_dao=test_payment_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
        item_service=test_item_service,
        entity_service=test_entity_service,
        setting_service=test_setting_service,
    )
    
@pytest.fixture(scope='module')
def test_item_service(test_item_dao, test_acct_service):
    from src.app.service.item import ItemService
    
    return ItemService(
        item_dao=test_item_dao,
        acct_service=test_acct_service,    
    )

@pytest.fixture(scope='module')
def test_shares_service(test_stock_issue_dao, test_stock_repurchase_dao, 
                        test_stock_dividend_dao, test_fx_service, test_acct_service, 
                        test_journal_service, test_setting_service):
    from src.app.service.shares import SharesService
    
    return SharesService(
        stock_issue_dao=test_stock_issue_dao,
        stock_repurchase_dao=test_stock_repurchase_dao,
        dividend_dao=test_stock_dividend_dao,
        fx_service=test_fx_service,
        acct_service=test_acct_service,
        journal_service=test_journal_service,
        setting_service=test_setting_service,
    )
        
@pytest.fixture(scope='module')
def session_with_basic_choa(test_dao_access, test_acct_service):
        
    from src.app.model.enums import AcctType

    print("Init basic Acct and COA...")
    test_acct_service.init()
    
    yield test_dao_access
    
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
def session_with_sample_choa(session_with_basic_choa, test_acct_service):
        
    print("Adding sample Acct and COA...")
    test_acct_service.create_sample()
    
    yield session_with_basic_choa
