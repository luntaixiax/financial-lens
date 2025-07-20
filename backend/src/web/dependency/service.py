from fastapi import Depends
from src.app.dao.files import fileDao
from src.app.dao.config import configDao
from src.app.dao.fx import fxDao
from src.app.dao.entity import contactDao, customerDao, supplierDao
from src.app.dao.journal import journalDao
from src.app.dao.expense import expenseDao
from src.app.dao.shares import dividendDao, stockIssueDao, stockRepurchaseDao
from src.app.dao.property import propertyDao, propertyTransactionDao
from src.app.dao.invoice import itemDao, invoiceDao
from src.app.dao.payment import paymentDao
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.dao.backup import adminBackupDao, backupDao
from src.app.dao.init import initDao
from src.app.service.shares import SharesService
from src.app.service.reporting import ReportingService
from src.app.service.property import PropertyService
from src.app.service.settings import ConfigService
from src.app.service.item import ItemService
from src.app.service.sales import SalesService
from src.app.service.purchase import PurchaseService
from src.app.service.files import FileService
from src.app.service.fx import FxService
from src.app.service.journal import JournalService
from src.app.service.expense import ExpenseService
from src.app.service.entity import EntityService
from src.app.service.acct import AcctService
from src.app.service.settings import BackupService
from src.app.service.management import AdminBackupService, InitService
from src.web.dependency.auth import get_init_dao
from src.web.dependency.dao import get_acct_dao, get_chart_of_acct_dao, \
    get_backup_dao, get_contact_dao, get_customer_dao, get_dividend_dao, get_expense_dao, \
    get_file_dao, get_fx_dao, get_item_dao, get_journal_dao, get_property_dao, \
    get_property_transaction_dao, get_stock_issue_dao, get_stock_repurchase_dao, \
    get_supplier_dao, get_config_dao, get_payment_dao, get_invoice_dao, get_admin_backup_dao

def get_init_service(
    init_dao: initDao = Depends(get_init_dao)
) -> InitService:
    return InitService(init_dao=init_dao)

def get_backup_service(
    backup_dao: backupDao = Depends(get_backup_dao)
) -> BackupService:
    return BackupService(backup_dao=backup_dao)

def get_file_service(
    file_dao: fileDao = Depends(get_file_dao)
) -> FileService:
    return FileService(file_dao=file_dao)

def get_setting_service(
    file_service: FileService = Depends(get_file_service),
    config_dao: configDao = Depends(get_config_dao)
) -> ConfigService:
    return ConfigService(file_service=file_service, config_dao=config_dao)

def get_fx_service(
    fx_dao: fxDao = Depends(get_fx_dao),
    setting_service: ConfigService = Depends(get_setting_service)
) -> FxService:
    # FX dao is common, but service is user specific
    return FxService(fx_dao=fx_dao, setting_service=setting_service)

def get_acct_service(
    acct_dao: acctDao = Depends(get_acct_dao),
    chart_of_acct_dao: chartOfAcctDao = Depends(get_chart_of_acct_dao),
    setting_service: ConfigService = Depends(get_setting_service)
) -> AcctService:
    return AcctService(
        acct_dao=acct_dao, 
        chart_of_acct_dao=chart_of_acct_dao,
        setting_service=setting_service
    )
    
def get_journal_service(
    journal_dao: journalDao = Depends(get_journal_dao),
    acct_service: AcctService = Depends(get_acct_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> JournalService:
    return JournalService(
        journal_dao=journal_dao, 
        acct_service=acct_service,
        setting_service=setting_service
    )

def get_entity_service(
    contact_dao: contactDao = Depends(get_contact_dao),
    customer_dao: customerDao = Depends(get_customer_dao),
    supplier_dao: supplierDao = Depends(get_supplier_dao)
) -> EntityService:
    return EntityService(
        contact_dao=contact_dao,
        customer_dao=customer_dao,
        supplier_dao=supplier_dao
    )
    
def get_expense_service(
    expense_dao: expenseDao = Depends(get_expense_dao),
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    fx_service: FxService = Depends(get_fx_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> ExpenseService:
    return ExpenseService(
        expense_dao=expense_dao,
        acct_service=acct_service,
        journal_service=journal_service,
        fx_service=fx_service,
        setting_service=setting_service
    )
    
def get_item_service(
    item_dao: itemDao = Depends(get_item_dao),
    acct_service: AcctService = Depends(get_acct_service),
) -> ItemService:
    return ItemService(
        item_dao=item_dao,
        acct_service=acct_service,
    )
    
def get_property_service(
    property_dao: propertyDao = Depends(get_property_dao),
    property_transaction_dao: propertyTransactionDao = Depends(get_property_transaction_dao),
    fx_service: FxService = Depends(get_fx_service),
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
) -> PropertyService:
    return PropertyService(
        property_dao=property_dao,
        property_transaction_dao=property_transaction_dao,
        fx_service=fx_service,
        acct_service=acct_service,
        journal_service=journal_service,
    )

def get_purchase_service(
    invoice_dao: invoiceDao = Depends(get_invoice_dao),
    payment_dao: paymentDao = Depends(get_payment_dao),
    item_service: ItemService = Depends(get_item_service),
    entity_service: EntityService = Depends(get_entity_service),
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    fx_service: FxService = Depends(get_fx_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> PurchaseService:
    return PurchaseService(
        invoice_dao=invoice_dao,
        payment_dao=payment_dao,
        item_service=item_service,
        entity_service=entity_service,
        acct_service=acct_service,
        journal_service=journal_service,
        fx_service=fx_service,
        setting_service=setting_service
    )
    
def get_sales_service(
    invoice_dao: invoiceDao = Depends(get_invoice_dao),
    payment_dao: paymentDao = Depends(get_payment_dao),
    item_service: ItemService = Depends(get_item_service),
    entity_service: EntityService = Depends(get_entity_service),
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    fx_service: FxService = Depends(get_fx_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> SalesService:
    return SalesService(
        invoice_dao=invoice_dao,
        payment_dao=payment_dao,
        item_service=item_service,
        entity_service=entity_service,
        acct_service=acct_service,
        journal_service=journal_service,
        fx_service=fx_service,
        setting_service=setting_service
    )
    
def get_shares_service(
    stock_issue_dao: stockIssueDao = Depends(get_stock_issue_dao),
    stock_repurchase_dao: stockRepurchaseDao = Depends(get_stock_repurchase_dao),
    dividend_dao: dividendDao = Depends(get_dividend_dao),
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    fx_service: FxService = Depends(get_fx_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> SharesService:
    return SharesService(
        stock_issue_dao=stock_issue_dao,
        stock_repurchase_dao=stock_repurchase_dao,
        dividend_dao=dividend_dao,
        acct_service=acct_service,
        journal_service=journal_service,
        fx_service=fx_service,
        setting_service=setting_service
    )
    
def get_reporting_service(
    journal_service: JournalService = Depends(get_journal_service),
    acct_service: AcctService = Depends(get_acct_service),
    setting_service: ConfigService = Depends(get_setting_service)
) -> ReportingService:
    return ReportingService(
        journal_service=journal_service,
        acct_service=acct_service,
        setting_service=setting_service
    )
    
def get_admin_backup_service(
    backup_dao: adminBackupDao = Depends(get_admin_backup_dao)
) -> AdminBackupService:
    return AdminBackupService(backup_dao=backup_dao)