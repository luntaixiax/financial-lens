from datetime import date
from typing import Tuple
from src.app.service.journal import JournalService
from src.app.dao.property import propertyDao, propertyTransactionDao
from src.app.service.fx import FxService
from src.app.model.const import SystemAcctNumber
from src.app.model.journal import Entry, Journal
from src.app.model.enums import AcctType, EntryType, JournalSrc, PropertyTransactionType, PropertyType
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError, FKNotExistError, NotMatchWithSystemError
from src.app.service.acct import AcctService
from src.app.model.accounts import Account
from src.app.model.property import _PropertyPriceBrief, Property, PropertyTransaction


class PropertyService:
    
    @classmethod
    def create_sample(cls):
        property = Property(
            property_id='exp-prop1',
            property_name='Computer',
            property_type=PropertyType.EQUIP,
            pur_dt=date(2024, 1, 3),
            pur_price=10000,
            pur_acct_id='acct-fbank'
        )
        depreciation = PropertyTransaction(
            trans_id='exp-proptrans-1',
            property_id='exp-prop1',
            trans_dt=date(2024, 2, 1),
            trans_type=PropertyTransactionType.DEPRECIATION,
            trans_amount=500
        )
        cls.add_property(property)
        cls.add_property_trans(depreciation)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_property_trans(trans_id='exp-proptrans-1')
        cls.delete_property(property_id='exp-prop1')
        
    @classmethod
    def _validate_property(cls, property: Property) -> Property:
        # validate if pur_acct_id is of balance sheet account
        try:
            pur_acct: Account = AcctService.get_account(
                property.pur_acct_id
            )
        except NotExistError as e:
            raise FKNotExistError(
                f"Purchase Account Id {property.pur_acct_id} does not exist",
                details=e.details
            )

        if not pur_acct.acct_type in (AcctType.AST, AcctType.LIB, AcctType.EQU):
            raise NotMatchWithSystemError(
                message=f"Purchase acct type of property must be of Balance sheet type, get {pur_acct.acct_type}"
            )
            
        return property
    
    @classmethod
    def _validate_propertytrans(cls, property_trans: PropertyTransaction) -> PropertyTransaction:
        # validate if property exist
        try:
            property, _ = cls.get_property_journal(property_trans.property_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Property {property_trans.property_id} does not exist",
                details=e.details
            )
        else:
            # validate if transaction is after property purchase date
            if property_trans.trans_dt < property.pur_dt:
                raise NotMatchWithSystemError(
                    message=f"Transaction happend before property purchase date",
                    details=f"Transaction date: {property_trans.trans_dt}, Purchase date: {property.pur_dt}"
                )
        return property_trans
            
    @classmethod
    def create_journal_from_property(cls, property: Property) -> Journal:
        cls._validate_property(property)
        
        entries = []
        pur_acct: Account = AcctService.get_account(
            property.pur_acct_id
        )
        amount_base=FxService.convert_to_base(
            amount=property.pur_price,
            src_currency=pur_acct.currency, # purchase currency
            cur_dt=property.pur_dt, # convert fx at purchase date
        )
        property_entry = Entry(
            entry_type=EntryType.DEBIT, # pp&e is debit
            acct=AcctService.get_account(SystemAcctNumber.PPNE),
            cur_incexp=None, # balance sheet item should not have currency
            amount=property.pur_price, # amount in raw currency
            # amount in base currency
            amount_base=amount_base,
            description=f"Property purchased"
        )
        purchase_entry = Entry(
            entry_type=EntryType.CREDIT, # credit to payment account
            acct=pur_acct,
            cur_incexp=None, # balance sheet item should not have currency
            amount=property.pur_price, # amount in raw currency
            # amount in base currency
            amount_base=amount_base,
            description=f"Payment for purchase property"
        )
        entries.append(property_entry)
        entries.append(purchase_entry)
        
        # create journal
        journal = Journal(
            jrn_date=property.pur_dt,
            entries=entries,
            jrn_src=JournalSrc.PPNE,
            note=f"Purchase {property.property_type.name} property {property.property_name}"
        )
        journal.reduce_entries()
        return journal
    
    @classmethod
    def create_journal_from_property_trans(cls, property_trans: PropertyTransaction) -> Journal:
        cls._validate_propertytrans(property_trans)
        
        entries = []
        property, _ = cls.get_property_journal(property_trans.property_id)
        pur_acct: Account = AcctService.get_account(
            property.pur_acct_id
        )
        amount_base=FxService.convert_to_base(
            amount=property_trans.trans_amount,
            src_currency=pur_acct.currency, # purchase currency
            cur_dt=property_trans.trans_dt, # convert fx at transaction date
        )
        if property_trans.trans_type == PropertyTransactionType.DEPRECIATION:
            # accumulate depreciation/impairment of pp&e is credit
            property_entry_type = EntryType.CREDIT
            gainloss_entry_type = EntryType.DEBIT
            gainloss_acct = AcctService.get_account(SystemAcctNumber.DEPRECIATION)
        elif property_trans.trans_type == PropertyTransactionType.IMPAIRMENT:
            property_entry_type = EntryType.CREDIT
            gainloss_entry_type = EntryType.DEBIT
            gainloss_acct = AcctService.get_account(SystemAcctNumber.IMPAIRMENT)
        elif property_trans.trans_type == PropertyTransactionType.APPRECIATION:
            # accumulate appreciation of pp&e is debit
            property_entry_type = EntryType.DEBIT
            gainloss_entry_type = EntryType.CREDIT
            gainloss_acct = AcctService.get_account(SystemAcctNumber.APPRECIATION)
        else:
            raise NotMatchWithSystemError(f"Property transaction type not supported: {property_trans.trans_type}")
        
        property_entry = Entry(
            entry_type=property_entry_type , 
            acct=AcctService.get_account(SystemAcctNumber.ACC_ADJ), # accumulative adjustment
            cur_incexp=None, # balance sheet item should not have currency
            amount=property_trans.trans_amount, # amount in raw currency
            # amount in base currency
            amount_base=amount_base,
            description=f"Property value {property_trans.trans_type.name}"
        )
        gainloss_entry = Entry(
            entry_type=gainloss_entry_type , 
            acct=gainloss_acct, # depending on type of transaction, record in different loss/gain account
            cur_incexp=pur_acct.currency, # use raw currency
            amount=property_trans.trans_amount, # amount in raw currency
            # amount in base currency
            amount_base=amount_base,
            description=f"Property value {property_trans.trans_type.name}"
        )
        entries.append(property_entry)
        entries.append(gainloss_entry)
        
        # create journal
        journal = Journal(
            jrn_date=property_trans.trans_dt,
            entries=entries,
            jrn_src=JournalSrc.PPNE,
            note=f"Property value adjustment: {property_trans.trans_type.name} of property {property.property_name}"
        )
        journal.reduce_entries()
        return journal
    
    @classmethod
    def add_property(cls, property: Property):
        # see if property already exist
        try:
            _property, _jrn_id  = propertyDao.get(property.property_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_property(property)
            
            # add journal first
            journal = cls.create_journal_from_property(property)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add property
            try:
                propertyDao.add(journal_id = journal.journal_id, property = property)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of property does not exist: {property}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'Property already exist, change one please',
                    details=f"{property}"
                )
            
        else:
            raise AlreadyExistError(
                f"Property id {property.property_id} already exist",
                details=f"Property: {_property}, journal_id: {_jrn_id}"
            )
            
    @classmethod
    def add_property_trans(cls, property_trans: PropertyTransaction):
        # see if property transaction already exist
        try:
            _property_trans, _jrn_id  = propertyTransactionDao.get(property_trans.trans_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_propertytrans(property_trans)
            
            # add journal first
            journal = cls.create_journal_from_property_trans(property_trans)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add property
            try:
                propertyTransactionDao.add(
                    journal_id = journal.journal_id, 
                    property_trans = property_trans
                )
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of property transaction does not exist: {property_trans}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'Property transaction already exist, change one please',
                    details=f"{property_trans}"
                )
            
        else:
            raise AlreadyExistError(
                f"Property transaction id {property_trans.trans_id} already exist",
                details=f"Property transaction: {_property_trans}, journal_id: {_jrn_id}"
            )
            
    @classmethod
    def get_property_journal(cls, property_id: str) -> Tuple[Property, Journal]:
        try:
            property, jrn_id = propertyDao.get(property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {property_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_property(property)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return property, journal
    
    @classmethod
    def get_property_trans_journal(cls, trans_id: str) -> Tuple[PropertyTransaction, Journal]:
        try:
            property_trans, jrn_id = propertyTransactionDao.get(trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {trans_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_property_trans(property_trans)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return property_trans, journal
    
    @classmethod
    def delete_property(cls, property_id: str):
        # remove journal first
        # get journal
        try:
            property, jrn_id  = propertyDao.get(property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {property_id} does not exist',
                details=e.details
            )
            
        # remove property first
        propertyDao.remove(property_id)
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def delete_property_trans(cls, trans_id: str):
        # remove journal first
        # get journal
        try:
            property, jrn_id  = propertyTransactionDao.get(trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {trans_id} does not exist',
                details=e.details
            )
            
        # remove property first
        propertyTransactionDao.remove(trans_id)
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def update_property(cls, property: Property):
        cls._validate_property(property)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _property, jrn_id  = propertyDao.get(property.property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {_property.property_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_property(property)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update property
        try:
            propertyDao.update(
                journal_id=journal.journal_id, # use new journal id
                property=property
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Property element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
        
    @classmethod
    def update_property_trans(cls, property_trans: PropertyTransaction):
        cls._validate_propertytrans(property_trans)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _property_trans, jrn_id  = propertyTransactionDao.get(property_trans.trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {property_trans.trans_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_property_trans(property_trans)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update property
        try:
            propertyTransactionDao.update(
                journal_id=journal.journal_id, # use new journal id
                property_trans=property_trans
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Property element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
        
    @classmethod
    def list_properties(cls) -> list[Property]:
        return propertyDao.list_properties()
    
    @classmethod
    def get_acc_stat(cls, property_id: str, rep_dt: date) -> _PropertyPriceBrief:
        try:
            stat = propertyTransactionDao.get_acc_stat(
                property_id=property_id,
                rep_dt=rep_dt
            )
        except NotExistError as e:
            raise NotExistError(
                message=f"Given property {property_id} not exist or purchased after {rep_dt}",
                details=e.details
            )
        return stat
    
    @classmethod
    def list_transactions(cls, property_id: str) -> list[PropertyTransaction]:
        return propertyTransactionDao.list_transactions(property_id)
    