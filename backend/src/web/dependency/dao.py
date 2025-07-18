from typing import Any, Generator
from fastapi import Depends
from fsspec import AbstractFileSystem
from sqlalchemy.engine import Engine
from sqlmodel import Session
from src.web.dependency.auth import get_current_user, common_engine_dep, get_common_session
from src.app.model.user import User
from src.app.dao.expense import expenseDao
from src.app.dao.entity import contactDao, customerDao, supplierDao
from src.app.dao.backup import backupDao, initDao
from src.app.dao.connection import CommonDaoAccess, get_storage_fs, \
    session_factory, engine_factory, UserDaoAccess
from src.app.dao.accounts import chartOfAcctDao, acctDao
from src.app.dao.files import fileDao, configDao
from src.app.dao.fx import fxDao
from src.app.dao.invoice import invoiceDao, itemDao
from src.app.dao.journal import journalDao
from src.app.dao.payment import paymentDao
from src.app.dao.property import propertyDao, propertyTransactionDao
from src.app.dao.shares import stockIssueDao, stockRepurchaseDao, dividendDao


def yield_session(current_user: User = Depends(get_current_user)) -> Generator[Session, None, None]:
    # TODO: extend to multiple db
    db_name = current_user.user_id
    session_gen_func = session_factory(db_name)
    yield from session_gen_func()

def yield_engine(current_user: User = Depends(get_current_user)) -> Generator[Engine, None, None]:
    # TODO: extend to multiple db
    db_name = current_user.user_id
    engine_gen_func = engine_factory(db_name)
    yield from engine_gen_func()

def yield_file_fs() -> AbstractFileSystem:
    return get_storage_fs('files')
    
def yield_backup_fs() -> AbstractFileSystem:
    return get_storage_fs('backup')

def get_common_dao_access(
    common_engine: common_engine_dep,
    common_session: Session = Depends(get_common_session),
) -> CommonDaoAccess:
    return CommonDaoAccess(
        common_engine=common_engine,
        common_session=common_session,
        file_fs=get_storage_fs('files'),
        backup_fs=get_storage_fs('backup')
    )

def get_user_dao_access(
    common_engine: common_engine_dep,
    common_session: Session = Depends(get_common_session),
    current_user: User = Depends(get_current_user),
    user_engine: Engine = Depends(yield_engine),
    user_session: Session = Depends(yield_session),
) -> UserDaoAccess:
    # for user DAO access that requires login
    return UserDaoAccess(
        user=current_user,
        file_fs=get_storage_fs('files'),
        backup_fs=get_storage_fs('backup'),
        common_engine=common_engine,
        user_engine=user_engine,
        common_session=common_session,
        user_session=user_session
    )

def get_config_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> configDao:
    return configDao(dao_access=dao_access)

def get_file_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> fileDao:
    return fileDao(dao_access=dao_access)

def get_backup_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> backupDao:
    return backupDao(dao_access=dao_access)

def get_fx_dao(
    dao_access: CommonDaoAccess = Depends(get_common_dao_access)
) -> fxDao:
    return fxDao(dao_access=dao_access)

def get_acct_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> acctDao:    
    return acctDao(dao_access=dao_access)

def get_chart_of_acct_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> chartOfAcctDao:
    return chartOfAcctDao(dao_access=dao_access)

def get_contact_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> contactDao:
    return contactDao(dao_access=dao_access)

def get_customer_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> customerDao:
    return customerDao(dao_access=dao_access)

def get_supplier_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> supplierDao:
    return supplierDao(dao_access=dao_access)

def get_expense_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> expenseDao:
    return expenseDao(dao_access=dao_access)

def get_item_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> itemDao:
    return itemDao(dao_access=dao_access)

def get_invoice_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> invoiceDao:
    return invoiceDao(dao_access=dao_access)

def get_journal_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> journalDao:
    return journalDao(dao_access=dao_access)

def get_payment_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> paymentDao:
    return paymentDao(dao_access=dao_access)

def get_property_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> propertyDao:
    return propertyDao(dao_access=dao_access)


def get_property_transaction_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> propertyTransactionDao:
    return propertyTransactionDao(dao_access=dao_access)

def get_stock_issue_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> stockIssueDao:
    return stockIssueDao(dao_access=dao_access)

def get_stock_repurchase_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> stockRepurchaseDao:
    return stockRepurchaseDao(dao_access=dao_access) 

def get_dividend_dao(
    dao_access: UserDaoAccess = Depends(get_user_dao_access)
) -> dividendDao:
    return dividendDao(dao_access=dao_access)