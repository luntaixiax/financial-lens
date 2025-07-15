from datetime import date
import math
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
    
    def __init__(self, property_dao: propertyDao, property_transaction_dao: propertyTransactionDao, 
                 fx_service: FxService, acct_service: AcctService, journal_service: JournalService):
        self.property_dao = property_dao
        self.property_transaction_dao = property_transaction_dao
        self.fx_service = fx_service
        self.acct_service = acct_service
        self.journal_service = journal_service
    
    def create_sample(self):
        property = Property(
            property_id='exp-prop1',
            property_name='Computer',
            property_type=PropertyType.EQUIP,
            pur_dt=date(2024, 1, 3),
            pur_price=10000,
            tax=700,
            pur_acct_id='acct-fbank',
            note='A computer',
            receipts=['A.pdf', 'B.pdf']
        )
        depreciation = PropertyTransaction(
            trans_id='exp-proptrans-1',
            property_id='exp-prop1',
            trans_dt=date(2024, 2, 1),
            trans_type=PropertyTransactionType.DEPRECIATION,
            trans_amount=500
        )
        self.add_property(property)
        self.add_property_trans(depreciation)
        
    def clear_sample(self):
        self.delete_property_trans(trans_id='exp-proptrans-1')
        self.delete_property(property_id='exp-prop1')
        
    def _validate_property(self, property: Property) -> Property:
        # validate if pur_acct_id is of balance sheet account
        try:
            pur_acct: Account = self.acct_service.get_account(
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
    
    def _validate_propertytrans(self, property_trans: PropertyTransaction) -> PropertyTransaction:
        # validate if property exist
        try:
            property, _ = self.get_property_journal(property_trans.property_id)
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
            
    def create_journal_from_property(self, property: Property) -> Journal:
        self._validate_property(property)
        
        entries = []
        pur_acct: Account = self.acct_service.get_account(
            property.pur_acct_id
        )
        # book value of cost
        amount_base=self.fx_service.convert_to_base(
            amount=property.pur_cost, # type: ignore
            src_currency=pur_acct.currency, # type: ignore # purchase currency
            cur_dt=property.pur_dt, # convert fx at purchase date
        )
        property_entry = Entry(
            entry_type=EntryType.DEBIT, # pp&e is debit
            acct=self.acct_service.get_account(SystemAcctNumber.PPNE), 
            cur_incexp=None, # balance sheet item should not have currency
            amount=amount_base, # amount in raw currency
            # amount in base currency
            amount_base=amount_base,
            description=f"Property purchased"
        )
        entries.append(property_entry)
        # sales tax
        if not math.isclose(property.tax, 0):
            amount_tax=self.fx_service.convert_to_base(
                amount=property.tax,
                src_currency=pur_acct.currency, # type: ignore # purchase currency
                cur_dt=property.pur_dt, # convert fx at purchase date
            )
            tax_entry = Entry(
                entry_type=EntryType.DEBIT, # tax is debit
                acct=self.acct_service.get_account(SystemAcctNumber.INPUT_TAX),
                cur_incexp=None, # balance sheet item should not have currency
                amount=amount_tax, # amount in raw currency
                # amount in base currency
                amount_base=amount_tax,
                description=f"Sales Tax"
            )
            entries.append(tax_entry)
        else:
            amount_tax = 0.0
        
        purchase_entry = Entry(
            entry_type=EntryType.CREDIT, # credit to payment account
            acct=pur_acct,
            cur_incexp=None, # balance sheet item should not have currency
            amount=property.pur_price, # amount in raw currency
            # amount in base currency
            amount_base=amount_base + amount_tax,
            description=f"Payment for purchase property"
        )
        
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
    
    def create_journal_from_property_trans(self, property_trans: PropertyTransaction) -> Journal:
        self._validate_propertytrans(property_trans)
        
        entries = []
        property, _ = self.get_property_journal(property_trans.property_id)
        pur_acct: Account = self.acct_service.get_account(
            property.pur_acct_id
        )
        amount_base=self.fx_service.convert_to_base(
            amount=property_trans.trans_amount,
            src_currency=pur_acct.currency, # type: ignore # purchase currency
            cur_dt=property_trans.trans_dt, # convert fx at transaction date
        )
        if property_trans.trans_type == PropertyTransactionType.DEPRECIATION:
            # accumulate depreciation/impairment of pp&e is credit
            property_entry_type = EntryType.CREDIT
            gainloss_entry_type = EntryType.DEBIT
            gainloss_acct = self.acct_service.get_account(SystemAcctNumber.DEPRECIATION)
        elif property_trans.trans_type == PropertyTransactionType.IMPAIRMENT:
            property_entry_type = EntryType.CREDIT
            gainloss_entry_type = EntryType.DEBIT
            gainloss_acct = self.acct_service.get_account(SystemAcctNumber.IMPAIRMENT)
        elif property_trans.trans_type == PropertyTransactionType.APPRECIATION:
            # accumulate appreciation of pp&e is debit
            property_entry_type = EntryType.DEBIT
            gainloss_entry_type = EntryType.CREDIT
            gainloss_acct = self.acct_service.get_account(SystemAcctNumber.APPRECIATION)
        else:
            raise NotMatchWithSystemError(f"Property transaction type not supported: {property_trans.trans_type}")
        
        property_entry = Entry(
            entry_type=property_entry_type , 
            acct=self.acct_service.get_account(SystemAcctNumber.ACC_ADJ), # accumulative adjustment
            cur_incexp=None, # balance sheet item should not have currency
            amount=amount_base, # amount in raw currency
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
    
    def add_property(self, property: Property):
        # see if property already exist
        try:
            _property, _jrn_id  = self.property_dao.get(property.property_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_property(property)
            
            # add journal first
            journal = self.create_journal_from_property(property)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add property
            try:
                self.property_dao.add(journal_id = journal.journal_id, property = property)
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
            
    def add_property_trans(self, property_trans: PropertyTransaction):
        # see if property transaction already exist
        try:
            _property_trans, _jrn_id  = self.property_transaction_dao.get(property_trans.trans_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_propertytrans(property_trans)
            
            # add journal first
            journal = self.create_journal_from_property_trans(property_trans)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add property
            try:
                self.property_transaction_dao.add(
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
            
    def get_property_journal(self, property_id: str) -> Tuple[Property, Journal]:
        try:
            property, jrn_id = self.property_dao.get(property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {property_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_property(property)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return property, journal
    
    def get_property_trans_journal(self, trans_id: str) -> Tuple[PropertyTransaction, Journal]:
        try:
            property_trans, jrn_id = self.property_transaction_dao.get(trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {trans_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_property_trans(property_trans)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return property_trans, journal
    
    def delete_property(self, property_id: str):
        # remove journal first
        # get journal
        try:
            property, jrn_id  = self.property_dao.get(property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {property_id} does not exist',
                details=e.details
            )
            
        # remove property first
        try:
            self.property_dao.remove(property_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"property {property_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            self.journal_service.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    def delete_property_trans(self, trans_id: str):
        # remove journal first
        # get journal
        try:
            property, jrn_id  = self.property_transaction_dao.get(trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {trans_id} does not exist',
                details=e.details
            )
            
        # remove property first
        try:
            self.property_transaction_dao.remove(trans_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Property transaction {trans_id} have dependency cannot be deleted",
                details=e.details
            )
            
        # then remove journal
        try:
            self.journal_service.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    def update_property(self, property: Property):
        self._validate_property(property)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _property, jrn_id  = self.property_dao.get(property.property_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property id {property.property_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_property(property)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update property
        try:
            self.property_dao.update(
                journal_id=journal.journal_id, # use new journal id
                property=property
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Property element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def update_property_trans(self, property_trans: PropertyTransaction):
        self._validate_propertytrans(property_trans)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _property_trans, jrn_id  = self.property_transaction_dao.get(property_trans.trans_id)
        except NotExistError as e:
            raise NotExistError(
                f'Property transaction id {property_trans.trans_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_property_trans(property_trans)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update property
        try:
            self.property_transaction_dao.update(
                journal_id=journal.journal_id, # use new journal id
                property_trans=property_trans
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Property element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def list_properties(self) -> list[Property]:
        return self.property_dao.list_properties()
    
    def get_acc_stat(self, property_id: str, rep_dt: date) -> _PropertyPriceBrief:
        try:
            stat = self.property_transaction_dao.get_acc_stat(
                property_id=property_id,
                rep_dt=rep_dt
            )
        except NotExistError as e:
            raise NotExistError(
                message=f"Given property {property_id} not exist or purchased after {rep_dt}",
                details=e.details
            )
        return stat
    
    def list_transactions(self, property_id: str) -> list[PropertyTransaction]:
        return self.property_transaction_dao.list_transactions(property_id)
    