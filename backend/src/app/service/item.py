from datetime import date
from typing import Tuple
from src.app.service.entity import EntityService
from src.app.dao.invoice import itemDao, invoiceDao
from src.app.model.exceptions import OpNotPermittedError, AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, \
    NotExistError, NotMatchWithSystemError
from src.app.model.const import SystemAcctNumber
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, UnitType
from src.app.model.invoice import _InvoiceBrief, Invoice, InvoiceItem, Item
from src.app.model.journal import Journal, Entry

class ItemService:
    
    @classmethod
    def create_sample(cls):
        item_consult = Item(
            item_id='item-consul',
            name='Item - Consulting',
            item_type=ItemType.SERVICE,
            entity_type=EntityType.CUSTOMER,
            unit=UnitType.HOUR,
            unit_price=100,
            currency=CurType.USD,
            default_acct_id='acct-consul'
        )
        item_meeting = Item(
            item_id='item-meet',
            name='Item - Meeting',
            item_type=ItemType.SERVICE,
            entity_type=EntityType.CUSTOMER,
            unit=UnitType.HOUR,
            unit_price=75,
            currency=CurType.USD,
            default_acct_id='acct-consul'
        )
        item_sales = Item(
            item_id='item-sales',
            name='Item - Purchase',
            item_type=ItemType.SERVICE,
            entity_type=EntityType.SUPPLIER,
            unit=UnitType.PIECE,
            unit_price=500,
            currency=CurType.USD,
            default_acct_id='acct-cogs'
        )
        
        cls.add_item(item_consult)
        cls.add_item(item_meeting)
        cls.add_item(item_sales)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_item('item-consul')
        cls.delete_item('item-meet')
        cls.delete_item('item-sales')
        
    @classmethod
    def _validate_item(cls, item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = AcctService.get_account(item.default_acct_id)
        # invoice to customer, the acct type must be of income type
        if not default_item_acct.acct_type in (AcctType.INC, AcctType.EXP):
            raise NotMatchWithSystemError(
                message=f"Default acct type of sales invoice item must be of Income/Expense type, get {default_item_acct.acct_type}"
            )
        
    @classmethod
    def add_item(cls, item: Item):
        cls._validate_item(item)
        try:
            itemDao.add(item)
        except AlreadyExistError as e:
            raise AlreadyExistError(
                f'item {item} already exist',
                details=e.details
            )
            
    @classmethod
    def update_item(cls, item: Item):
        cls._validate_item(item)
        # cannot update unit type and item type
        _item = cls.get_item(item.item_id)
        if _item.unit != item.unit or _item.item_type != item.item_type:
            raise NotMatchWithSystemError(
                f"Item unit and type cannot change",
                details=f'Database version: {_item}, your version: {item}'
            )
        
        try:
            itemDao.update(item)
        except NotExistError as e:
            raise NotExistError(
                f'item id {item.item_id} not exist',
                details=e.details
            )
            
    @classmethod
    def delete_item(cls, item_id: str):
        try:
            itemDao.remove(item_id)
        except NotExistError as e:
            raise NotExistError(
                f'item id {item_id} not exist',
                details=e.details
            )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f'item {item_id} used in some invoice',
                details=e.details
            )
            
    @classmethod
    def get_item(cls, item_id: str) -> Item:
        try:
            item = itemDao.get(item_id)
        except NotExistError as e:
            raise NotExistError(
                f'item id {item_id} not exist',
                details=e.details
            )
        return item
    
    @classmethod
    def list_item(cls, entity_type: EntityType) -> list[Item]:
        return itemDao.list_item(entity_type=entity_type)