from fastapi import APIRouter, Depends
from src.app.model.entity import Contact
from src.app.model.enums import CurType
from src.app.service.misc import SettingService
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.entity import EntityService
from src.app.service.item import ItemService
from src.app.service.sales import SalesService
from src.app.service.purchase import PurchaseService
from src.app.service.expense import ExpenseService
from src.app.service.property import PropertyService
from src.app.service.shares import SharesService
from src.web.dependency.service import get_acct_service, get_journal_service, \
    get_entity_service, get_item_service, get_sales_service, get_purchase_service, \
    get_expense_service, get_property_service, get_setting_service, get_shares_service

router = APIRouter(prefix="/sample", tags=["sample"])

@router.post("/create_sample")
def create_sample(
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    entity_service: EntityService = Depends(get_entity_service),
    item_service: ItemService = Depends(get_item_service),
    sales_service: SalesService = Depends(get_sales_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
    expense_service: ExpenseService = Depends(get_expense_service),
    property_service: PropertyService = Depends(get_property_service),
    shares_service: SharesService = Depends(get_shares_service),
    setting_service: SettingService = Depends(get_setting_service)
):
    # set base settings
    setting_service.create_sample()
    # create additional sample accounts
    if not setting_service.is_setup():
        # create basic account structure *standard
        acct_service.init()
        setting_service.confirm_setup()
    
    acct_service.create_sample()
    # create sample journals
    journal_service.create_sample()
    # create sample customer
    entity_service.create_sample()
    # crete item items
    item_service.create_sample()
    # create sample sales invoice
    sales_service.create_sample()
    # create sample purchase invoice
    purchase_service.create_sample()
    # create sample expense
    expense_service.create_sample()
    # create property sample
    property_service.create_sample()
    # create shares sample
    shares_service.create_sample()
    

@router.delete("/clear_sample")
def clear_sample(
    acct_service: AcctService = Depends(get_acct_service),
    journal_service: JournalService = Depends(get_journal_service),
    entity_service: EntityService = Depends(get_entity_service),
    item_service: ItemService = Depends(get_item_service),
    sales_service: SalesService = Depends(get_sales_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
    expense_service: ExpenseService = Depends(get_expense_service),
    property_service: PropertyService = Depends(get_property_service),
    shares_service: SharesService = Depends(get_shares_service)
):
    
    acct_service.clear_sample()
    journal_service.clear_sample()
    entity_service.clear_sample()
    item_service.clear_sample()
    sales_service.clear_sample()
    purchase_service.clear_sample()
    expense_service.clear_sample()
    property_service.clear_sample()
    shares_service.clear_sample()
    
