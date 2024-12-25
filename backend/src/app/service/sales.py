from datetime import date
import math
from typing import Tuple
from src.app.utils.tools import get_base_cur
from src.app.service.item import ItemService
from src.app.service.entity import EntityService
from src.app.dao.invoice import itemDao, invoiceDao
from src.app.dao.payment import paymentDao
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
from src.app.model.payment import PaymentItem, Payment


class SalesService:
    
    @classmethod
    def create_sample(cls):
        invoice = Invoice(
            invoice_id='inv-sales',
            invoice_num='INV-001',
            invoice_dt=date(2024, 1, 1),
            due_dt=date(2024, 1, 5),
            entity_type=EntityType.CUSTOMER,
            entity_id='cust-sample',
            subject='General Consulting - Jan 2024',
            currency=CurType.USD,
            invoice_items=[
                InvoiceItem(
                    item=ItemService.get_item('item-consul'),
                    quantity=5,
                    description="Programming"
                ),
                InvoiceItem(
                    item=ItemService.get_item('item-meet'),
                    quantity=10,
                    description="Meeting Around",
                    discount_rate=0.05,
                )
            ],
            shipping=10,
            note="Thanks for business"
        )
        cls.add_invoice(invoice)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_invoice('inv-sales')

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
            jrn_src=JournalSrc.SALES,
            note=invoice.note
        )
        journal.reduce_entries()
        return journal
    
    @classmethod
    def create_journal_from_payment(cls, payment: Payment) -> Journal:
        cls._validate_payment(payment)
        
        entries = []
        
        # AR/AP offset amount, expressed in base currency
        ar_offset_raw_base = 0
        for payment_item in payment.payment_items:
            _invoice, _jrn_id  = invoiceDao.get(payment_item.invoice_id)
            amount_base = FxService.convert(
                amount=payment_item.payment_amount_raw, # amount deducted in invoice currency
                src_currency=_invoice.currency, # invoice currency
                # for A/R, A/P offset by payment, it should reflect amount at invoice date
                cur_dt=_invoice.invoice_dt, # convert fx at invoice date # TODO: convert at invoice date or payment date?
            )
            ar_offset_raw_base += amount_base
        
        ar = Entry(
            entry_type=EntryType.CREDIT, # offset A/R is credit entry
            acct=AcctService.get_account(SystemAcctNumber.ACCT_RECEIV),
            amount=ar_offset_raw_base, # amount in base currency
            amount_base=ar_offset_raw_base, # amount in base currency
            description=f'account receivable offset, converting to base currency using fx rate at invoice date'
        )
        entries.append(ar)
        
        # payment fee entry
        fee_amount_base = FxService.convert(
            amount=payment.payment_fee,
            src_currency=payment.currency, # payment currency
            cur_dt=payment.payment_dt, # convert at payment date
        )
        fee = Entry(
            entry_type=EntryType.DEBIT, # fee is expense, debit entry
            acct=AcctService.get_account(SystemAcctNumber.BANK_FEE), # debit to bank fee
            cur_incexp=payment.currency, # payment currency
            amount=payment.payment_fee, # in payment currency
            amount_base=fee_amount_base, # converted to base currency
            description='bank fee charged for payment'
        )
        entries.append(fee)
        
        # bank transfer entry (payment account)
        net_pmt = payment.net_payment
        pmt_amount_base = FxService.convert(
            amount=net_pmt, # total payment before fee
            src_currency=payment.currency, # payment currency
            cur_dt=payment.payment_dt, # convert at payment date
        )
        pmt = Entry(
            entry_type=EntryType.DEBIT, # payment receive is debit entry
            acct=AcctService.get_account(payment.payment_acct_id), # debit to payment account
            cur_incexp=payment.currency, # payment currency
            amount=net_pmt, # in payment currency
            amount_base=pmt_amount_base, # converted to base currency
            description='total payment received (net of fee)'
        )
        entries.append(pmt)
        
        # add fx gain/loss
        gain = (pmt_amount_base + fee_amount_base) - ar_offset_raw_base # received more than A/R
        fx_gain = Entry(
            entry_type=EntryType.CREDIT, # fx gain is credit
            acct=AcctService.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
            cur_incexp=get_base_cur(),
            amount=gain, # gain is already expressed in base currency
            amount_base=gain, # gain is already expressed in base currency
            description='fx gain' if gain >=0 else 'fx loss'
        )
        entries.append(fx_gain)
        
        # create journal
        journal = Journal(
            jrn_date=payment.payment_dt,
            entries=entries,
            jrn_src=JournalSrc.PAYMENT,
            note=payment.note
        )
        journal.reduce_entries()
        return journal
        
    
    @classmethod
    def _validate_item(cls, item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = AcctService.get_account(item.default_acct_id)
        # invoice to customer, the acct type must be of income type
        if not default_item_acct.acct_type in (AcctType.INC, ):
            raise NotMatchWithSystemError(
                message=f"Default acct type of sales invoice item must be of Income type, get {default_item_acct.acct_type}"
            )
            
    @classmethod
    def _validate_invoice(cls, invoice: Invoice):
        # validate direction
        if not invoice.entity_type == EntityType.CUSTOMER:
            raise OpNotPermittedError('Sales invoice should only be created for customer')
        # validate customer exist
        try:
            EntityService.get_customer(invoice.entity_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Customer id {invoice.entity_id} does not exist",
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
                try:
                    cls._validate_item(invoice_item.item)
                except NotExistError as e:
                    raise FKNotExistError(
                        f"Account Id {invoice_item.item.default_acct_id} of Item {invoice_item.item} does not exist",
                        details=e.details
                    )
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
                    f"Account {invoice_item.acct_id} of Invoice Item {invoice_item} does not exist",
                    details=e.details
                )
                
    @classmethod
    def _validate_payment(cls, payment: Payment):
        # validate direction
        if not payment.entity_type == EntityType.CUSTOMER:
            raise OpNotPermittedError('Sales payment should only be created for customer')
        
        # validate payment account id exist
        try:
            payment_acct = AcctService.get_account(payment.payment_acct_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Account {payment.payment_acct_id} of Payment {payment} does not exist",
                details=e.details
            )
        
        # validate payment items
        for payment_item in payment.payment_items:
            # validate invoice exist or not
            try:
                _invoice, _jrn_id  = invoiceDao.get(payment_item.invoice_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Invoice Id {payment_item.invoice_id} of payment item {payment_item} does not exist",
                    details=e.details
                )
            
            # validate invoice direction
            if not _invoice.entity_type == EntityType.CUSTOMER:
                raise OpNotPermittedError('Invoice used in sales payment should only be related customer')

            # validate payment and payment amount raw
            if payment_acct.currency == _invoice.currency:
                # if invoice currency equals payment currency, the amount should equal
                if not math.isclose(payment_item.payment_amount, payment_item.payment_amount_raw, rel_tol=1e-6):
                    raise OpNotPermittedError(
                        f'Same payment and invoice currency ({payment_acct.currency}), payment_amount should equal to payment_amount_raw',
                        details=f'payment item amount not expected: {payment_item}'
                    )
            
    
    @classmethod
    def add_invoice(cls, invoice: Invoice):
        
        # see if invoice already exist
        try:
            _invoice, _jrn_id  = invoiceDao.get(invoice.invoice_id)
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
            invoice, jrn_id = invoiceDao.get(invoice_id)
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
            invoice, jrn_id  = invoiceDao.get(invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice_id} does not exist',
                details=e.details
            )
            
        # remove invoice first
        invoiceDao.remove(invoice_id)
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
        
        
    @classmethod
    def update_invoice(cls, invoice: Invoice):
        cls._validate_invoice(invoice)
        # only delete if validation passed
        # cls.delete_invoice(invoice.invoice_id)
        # cls.add_invoice(invoice)
        
        # get existing journal id
        try:
            _invoice, jrn_id  = invoiceDao.get(invoice.invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {_invoice.invoice_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_invoice(invoice)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update invoice
        try:
            invoiceDao.update(
                journal_id=journal.journal_id, # use new journal id
                invoice=invoice
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Invoice element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
        
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
            entity_type=EntityType.CUSTOMER,
            invoice_ids=invoice_ids,
            invoice_nums=invoice_nums,
            entity_ids=customer_ids,
            min_dt=min_dt,
            max_dt=max_dt,
            subject_keyword=subject_keyword,
            currency=currency,
            min_amount=min_amount,
            max_amount=max_amount,
            num_invoice_items=num_invoice_items
        ) 
        