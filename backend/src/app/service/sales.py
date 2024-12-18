from datetime import date
from typing import Tuple
from src.app.service.entity import EntityService
from src.app.dao.invoice import itemDao, invoiceDao
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.const import SystemAcctNumber
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntryType
from src.app.model.invoice import _InvoiceBrief, Invoice, Item
from src.app.model.journal import Journal, Entry


class SalesService:
    
    @classmethod
    def create_journal_from_invoice(cls, invoice: Invoice) -> Journal:
        cls._validate_invoice(invoice)
        
        entries = []
        # create sales invoice entries
        for invoice_item in invoice.invoice_items:
            # get the invoice item account for journal entry line item
            item_acct_id = invoice_item.acct_id # the account id for this entry
            item_acct: Account = AcctService.get_account(item_acct_id)
            
            # validate the item account must be of income type
            if not item_acct.acct_type == AcctType.INC:
                raise NotMatchWithSystemError(
                    message=f"Acct type of invoice item must be of Income type, get {item_acct.acct_type}"
                )
            
            # assemble the entry item
            entry = Entry(
                entry_type=EntryType.CREDIT, # income is credit entry
                acct=item_acct,
                cur_incexp=invoice.currency, # income currency is invoice currency
                amount=invoice_item.amount_pre_tax, # amount in raw currency
                # amount in base currency
                amount_base=FxService.convert(
                    amount=invoice_item.amount_pre_tax,
                    src_currency=invoice.currency, # invoice currency
                    cur_dt=invoice.invoice_dt, # convert fx at invoice date
                ),
                description=invoice_item.description
            )
            entries.append(entry)
        
        # add tax (use base currency)
        tax_amount_base_cur = FxService.convert(
            amount=invoice.tax_amount, # total tax across all items
            src_currency=invoice.currency, # invoice currency
            cur_dt=invoice.invoice_dt, # convert fx at invoice date
        )
        tax = Entry(
            entry_type=EntryType.CREDIT, # tax is credit entry
            # tax account is output tax -- predefined
            acct=AcctService.get_account(SystemAcctNumber.OUTPUT_TAX),
            amount=tax_amount_base_cur, # amount in raw currency
            # amount in base currency
            amount_base=tax_amount_base_cur,
            description=f'output tax in base currency'
        )
        entries.append(tax)
        
        # add shipping entry (use raw currency)
        shipping = Entry(
            entry_type=EntryType.CREDIT, # shipping is credit entry
            # shipping account -- predefined
            acct=AcctService.get_account(SystemAcctNumber.SHIP_CHARGE),
            cur_incexp=invoice.currency, # shipping currency is invoice currency
            amount=invoice.shipping, # amount in raw currency
            # amount in base currency
            amount_base = FxService.convert(
                amount=invoice.shipping, # total shipping across all items
                src_currency=invoice.currency, # invoice currency
                cur_dt=invoice.invoice_dt, # convert fx at invoice date
            ),
            description=f'shipping charge'
        )
        entries.append(shipping)
        
        # add account receivable (use base currency)
        ar_base_cur = FxService.convert(
            amount=invoice.total, # total after tax and shipping
            src_currency=invoice.currency, # invoice currency
            cur_dt=invoice.invoice_dt, # convert fx at invoice date
        )
        ar = Entry(
            entry_type=EntryType.DEBIT, # A/R is debit entry
            # A/R is output tax -- predefined
            acct=AcctService.get_account(SystemAcctNumber.ACCT_RECEIV),
            amount=ar_base_cur, # amount in base currency
            amount_base=ar_base_cur, # amount in base currency
            description=f'account receivable in base currency'
        )
        entries.append(ar)
        
        # create journal
        journal = Journal(
            jrn_date=invoice.invoice_dt,
            entries=entries,
            is_manual=False,
            note=invoice.note
        )
        journal.reduce_entries()
        return journal
    
    @classmethod
    def _validate_item(cls, item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = AcctService.get_account(item.default_acct_id)
        if not default_item_acct.acct_type in (AcctType.INC, AcctType.EXP):
            raise NotMatchWithSystemError(
                message=f"Default acct type of invoice item must be of Income/Expense type, get {default_item_acct.acct_type}"
            )
            
    @classmethod
    def _validate_invoice(cls, invoice: Invoice):
        # validate customer exist
        try:
            EntityService.get_customer(invoice.customer_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Customer id {invoice.customer_id} does not exist",
                details=e.details
            )
        
        # validate invoice_items
        for invoice_item in invoice.invoice_items:
            # validate item exist
            try:
                item = itemDao.get(invoice_item.item.item_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Item {invoice_item.item} does not exist",
                    details=e.details
                )
            else:
                # validate item
                cls._validate_item(invoice_item.item)
                # validate each item if no change from database
                if item != invoice_item.item:
                    raise NotMatchWithSystemError(
                        f"Item not match with database",
                        details=f'Database version: {item}, your version: {invoice_item.item}'
                    )
            # validate account id exist
            try:
                AcctService.get_account(invoice_item.acct_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Account {invoice_item.acct_id} does not exist",
                    details=e.details
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
    def add_invoice(cls, invoice: Invoice):
        
        # see if invoice already exist
        try:
            _jrn_id, _invoice = invoiceDao.get(invoice.invoice_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_invoice(invoice)
            # add journal first
            journal = cls.create_journal_from_invoice(invoice)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
            
            # add invoice
            try:
                invoiceDao.add(journal_id = journal.journal_id, invoice = invoice)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of invoice does not exist: {invoice}',
                    details=e.details
                )
            
        else:
            raise AlreadyExistError(
                f"Invoice id {invoice.invoice_id} already exist",
                details=f"Invoice: {_invoice}, journal_id: {_jrn_id}"
            )
            
    @classmethod
    def get_invoice_journal(cls, invoice_id: str) -> Tuple[Invoice, Journal]:
        try:
            jrn_id, invoice = invoiceDao.get(invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_invoice(invoice)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return invoice, journal
    
    @classmethod
    def delete_invoice(cls, invoice_id: str):
        # remove journal first
        # get journal
        try:
            jrn_id, invoice = invoiceDao.get(invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice_id} does not exist',
                details=e.details
            )
        
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
        # then remove invoice

        invoiceDao.remove(invoice_id)
        
    @classmethod
    def update_invoice(cls, invoice: Invoice):
        cls._validate_invoice(invoice)
        # only delete if validation passed
        cls.delete_invoice(invoice.invoice_id)
        cls.add_invoice(invoice)
        
        
    @classmethod
    def list_invoice(
        cls,
        limit: int = 50,
        offset: int = 0,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        customer_ids: list[str] | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        subject_keyword: str = '',
        currency: CurType | None = None,
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_invoice_items: int | None = None
    ) -> list[_InvoiceBrief]:
        return invoiceDao.list(
            limit=limit,
            offset=offset,
            invoice_ids=invoice_ids,
            invoice_nums=invoice_nums,
            customer_ids=customer_ids,
            min_dt=min_dt,
            max_dt=max_dt,
            subject_keyword=subject_keyword,
            currency=currency,
            min_amount=min_amount,
            max_amount=max_amount,
            num_invoice_items=num_invoice_items
        ) 
        