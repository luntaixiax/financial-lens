from typing import Generator
from fastapi import Depends
from s3fs import S3FileSystem
from sqlalchemy.engine import Engine
from sqlmodel import Session
from src.app.dao.expense import expenseDao
from src.app.dao.entity import contactDao, customerDao, supplierDao
from src.app.dao.backup import dataDao
from src.app.dao.connection import yield_file_fs, yield_backup_fs, session_factory, engine_factory
from src.app.dao.accounts import chartOfAcctDao, acctDao
from src.app.dao.files import fileDao, configDao
from src.app.dao.fx import fxDao
from src.app.dao.invoice import invoiceDao, itemDao
from src.app.dao.journal import journalDao
from src.app.dao.payment import paymentDao
from src.app.dao.property import propertyDao, propertyTransactionDao
from src.app.dao.shares import stockIssueDao, stockRepurchaseDao, dividendDao

def yield_session() -> Generator[Session, None, None]:
    # TODO: extend to multiple db
    session_gen_func = session_factory('finlens')
    yield from session_gen_func()

def yield_engine() -> Generator[Engine, None, None]:
    # TODO: extend to multiple db
    engine_gen_func = engine_factory('finlens')
    yield from engine_gen_func()
    
def get_config_dao(
    file_fs: S3FileSystem = Depends(yield_file_fs)
) -> configDao:
    return configDao(file_fs=file_fs)

def get_file_dao(
    session: Session = Depends(yield_session), 
    file_fs: S3FileSystem = Depends(yield_file_fs)
) -> fileDao:
    return fileDao(session=session, file_fs=file_fs)

def get_backup_dao(
    engine: Engine = Depends(yield_engine), 
    backup_fs: S3FileSystem = Depends(yield_backup_fs),
    file_fs: S3FileSystem = Depends(yield_file_fs)
) -> dataDao:
    return dataDao(primary_engine=engine, backup_fs=backup_fs, file_fs=file_fs)

def get_fx_dao(
    session: Session = Depends(yield_session) # switch to another db session
) -> fxDao:
    return fxDao(session=session)

def get_acct_dao(
    session: Session = Depends(yield_session)
) -> acctDao:    
    return acctDao(session=session)

def get_chart_of_acct_dao(
    engine: Engine = Depends(yield_engine)
) -> chartOfAcctDao:
    return chartOfAcctDao(engine=engine)

def get_contact_dao(
    session: Session = Depends(yield_session)
) -> contactDao:
    return contactDao(session=session)

def get_customer_dao(
    session: Session = Depends(yield_session)
) -> customerDao:
    return customerDao(session=session)

def get_supplier_dao(
    session: Session = Depends(yield_session)
) -> supplierDao:
    return supplierDao(session=session)

def get_expense_dao(
    session: Session = Depends(yield_session)
) -> expenseDao:
    return expenseDao(session=session)

def get_item_dao(
    session: Session = Depends(yield_session)
) -> itemDao:
    return itemDao(session=session)

def get_invoice_dao(
    session: Session = Depends(yield_session)
) -> invoiceDao:
    return invoiceDao(session=session)

def get_journal_dao(
    session: Session = Depends(yield_session),
    engine: Engine = Depends(yield_engine)
) -> journalDao:
    return journalDao(session=session, engine=engine)

def get_payment_dao(
    session: Session = Depends(yield_session)
) -> paymentDao:
    return paymentDao(session=session)

def get_property_dao(
    session: Session = Depends(yield_session)
) -> propertyDao:
    return propertyDao(session=session)


def get_property_transaction_dao(
    session: Session = Depends(yield_session)
) -> propertyTransactionDao:
    return propertyTransactionDao(session=session)

def get_stock_issue_dao(
    session: Session = Depends(yield_session)
) -> stockIssueDao:
    return stockIssueDao(session=session)

def get_stock_repurchase_dao(
    session: Session = Depends(yield_session)
) -> stockRepurchaseDao:
    return stockRepurchaseDao(session=session) 

def get_dividend_dao(
    session: Session = Depends(yield_session)
) -> dividendDao:
    return dividendDao(session=session)