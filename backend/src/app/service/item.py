from src.app.dao.invoice import itemDao
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError, NotMatchWithSystemError
from src.app.service.acct import AcctService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntityType, ItemType, UnitType
from src.app.model.invoice import Item

class ItemService:
    
    def __init__(self, item_dao: itemDao, acct_service: AcctService):
        self.item_dao = item_dao
        self.acct_service = acct_service
        
    def create_sample(self):
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
        
        self.add_item(item_consult)
        self.add_item(item_meeting)
        self.add_item(item_sales)
        
    def clear_sample(self):
        self.delete_item('item-consul')
        self.delete_item('item-meet')
        self.delete_item('item-sales')
        
    def _validate_item(self, item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = self.acct_service.get_account(item.default_acct_id)
        # invoice to customer, the acct type must be of income type
        if not default_item_acct.acct_type in (AcctType.INC, AcctType.EXP):
            raise NotMatchWithSystemError(
                message=f"Default acct type of sales invoice item must be of Income/Expense type, get {default_item_acct.acct_type}"
            )
        
    def add_item(self, item: Item):
        self._validate_item(item)
        try:
            self.item_dao.add(item)
        except AlreadyExistError as e:
            raise AlreadyExistError(
                f'item {item} already exist',
                details=e.details
            )
            
    def update_item(self, item: Item):
        self._validate_item(item)
        # cannot update unit type and item type
        _item = self.get_item(item.item_id)
        if _item.unit != item.unit or _item.item_type != item.item_type:
            raise NotMatchWithSystemError(
                f"Item unit and type cannot change",
                details=f'Database version: {_item}, your version: {item}'
            )
        
        try:
            self.item_dao.update(item)
        except NotExistError as e:
            raise NotExistError(
                f'item id {item.item_id} not exist',
                details=e.details
            )
            
    def delete_item(self, item_id: str):
        try:
            self.item_dao.remove(item_id)
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
            
    def get_item(self, item_id: str) -> Item:
        try:
            item = self.item_dao.get(item_id)
        except NotExistError as e:
            raise NotExistError(
                f'item id {item_id} not exist',
                details=e.details
            )
        return item
    
    def list_item(self, entity_type: EntityType) -> list[Item]:
        return self.item_dao.list_item(entity_type=entity_type)