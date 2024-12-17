from typing import Tuple
from src.app.dao.invoice import itemDao, invoiceDao
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.const import SystemAcctNumber
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, EntryType
from src.app.model.invoice import Invoice, Item
from src.app.model.journal import Journal, Entry


class SalesService:
    
    @classmethod
    def create_journal_from_invoice(cls, invoice: Invoice) -> Journal:
        # TODO: validate invoice first (e.g., item account id)
        
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
    def _validate_item(item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = AcctService.get_account(item.default_acct_id)
        if not default_item_acct.acct_type in (AcctType.INC, AcctType.EXP):
            raise NotMatchWithSystemError(
                message=f"Default acct type of invoice item must be of Income/Expense type, get {default_item_acct.acct_type}"
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
    def remove_item(cls, item_id: str):
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
        cls.delete_invoice(invoice.invoice_id)
        cls.add_invoice(invoice)
        
        