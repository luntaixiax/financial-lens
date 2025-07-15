from datetime import date
import math
from typing import Tuple
from src.app.utils.tools import get_base_cur
from src.app.service.item import ItemService
from src.app.service.entity import EntityService
from src.app.dao.invoice import invoiceDao
from src.app.dao.payment import paymentDao
from src.app.model.exceptions import OpNotPermittedError, AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, \
    NotExistError, NotMatchWithSystemError
from src.app.model.const import SystemAcctNumber
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, UnitType
from src.app.model.invoice import _InvoiceBalance, _InvoiceBrief, GeneralInvoiceItem, Invoice, InvoiceItem, Item
from src.app.model.journal import Journal, Entry
from src.app.model.payment import _PaymentBrief, PaymentItem, Payment


class SalesService:
    
    def __init__(
            self, 
            invoice_dao: invoiceDao, payment_dao: paymentDao, 
            item_service: ItemService, entity_service: EntityService,
            acct_service: AcctService, journal_service: JournalService,
            fx_service: FxService
        ):
        self.invoice_dao = invoice_dao
        self.payment_dao = payment_dao
        self.item_service = item_service
        self.acct_service = acct_service
        self.journal_service = journal_service
        self.fx_service = fx_service
        self.entity_service = entity_service
        
    def create_sample(self):
        # add invoice
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
                    acct_id='',
                    item=self.item_service.get_item('item-consul'),
                    quantity=5,
                    description="Programming"
                ),
                InvoiceItem(
                    acct_id='',
                    item=self.item_service.get_item('item-meet'),
                    quantity=10,
                    description="Meeting Around",
                    discount_rate=0.05,
                )
            ],
            ginvoice_items=[
                GeneralInvoiceItem(
                    incur_dt=date(2023, 12, 10),
                    acct_id='acct-meal',
                    currency=CurType.EUR,
                    amount_pre_tax_raw=100,
                    amount_pre_tax=120,
                    tax_rate=0.05,
                    description='Meal for business trip'
                )
            ],
            shipping=10,
            note="Thanks for business"
        )
        self.add_invoice(invoice)
        # add payment
        payment = Payment(
            payment_id='pmt-sales',
            payment_num='PMT-001',
            payment_dt=date(2024, 1, 4),
            entity_type=EntityType.CUSTOMER,
            payment_items=[
                PaymentItem(
                    payment_item_id='pmtitem-1',
                    invoice_id='inv-sales',
                    payment_amount=135,
                    payment_amount_raw=100
                )
            ],
            payment_acct_id='acct-bank',
            payment_fee=2,
            ref_num='#12345',
            note='payment from client'
        )
        self.add_payment(payment)
        
    def clear_sample(self):
        self.delete_payment('pmt-sales')
        self.delete_invoice('inv-sales')

    def create_journal_from_invoice(self, invoice: Invoice) -> Journal:
        self._validate_invoice(invoice)
        
        entries = []
        # create sales invoice item entries
        for invoice_item in invoice.invoice_items:
            # get the invoice item account for journal entry line item
            item_acct: Account = self.acct_service.get_account(invoice_item.acct_id)
            
            # assemble the entry item
            entry = Entry(
                entry_type=EntryType.CREDIT, # income is credit entry
                acct=item_acct,
                cur_incexp=invoice.currency, # income currency is invoice currency
                amount=invoice_item.amount_pre_tax, # amount in raw currency # type: ignore
                # amount in base currency
                amount_base=self.fx_service.convert_to_base(
                    amount=invoice_item.amount_pre_tax, # type: ignore
                    src_currency=invoice.currency, # invoice currency
                    cur_dt=invoice.invoice_dt, # convert fx at invoice date
                ),
                description=invoice_item.description
            )
            entries.append(entry)
            
        # create general invoice item entries
        for ginvoice_item in invoice.ginvoice_items:
            gitem_acct: Account = self.acct_service.get_account(ginvoice_item.acct_id)
            # amount incured in base currency @ incur date
            amount_base_incur = self.fx_service.convert_to_base(
                amount=ginvoice_item.amount_pre_tax_raw,# amount in incur currency
                src_currency=ginvoice_item.currency, # incur currency
                cur_dt=ginvoice_item.incur_dt, # convert fx at incur date
            )
            # amount in base currency @ invoice date (this is the total amount should be credit that make it balance)
            amount_base_invoice = self.fx_service.convert_to_base(
                amount=ginvoice_item.amount_pre_tax,# amount in invoice currency
                src_currency=invoice.currency, # invoice currency
                cur_dt=invoice.invoice_dt, # convert fx at invoice date # TODO
            )
            # assemble the entry item (reverse the original journal entry)
            gitem = Entry(
                entry_type=EntryType.CREDIT, # income is credit entry (does not matter if it is income or expense)
                acct=gitem_acct,
                cur_incexp=ginvoice_item.currency, # income currency is incur currency (reverse record)
                amount=ginvoice_item.amount_pre_tax_raw, # amount in incur currency
                # amount in base currency
                amount_base=amount_base_incur, # amount incured in base currency @ incur date
                description=ginvoice_item.description
            )
            entries.append(gitem)
            
            # add fx gain/loss
            gain = amount_base_invoice - amount_base_incur # invoiced more than incurred is gain
            fx_gain = Entry(
                entry_type=EntryType.CREDIT, # fx gain is credit
                acct=self.acct_service.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
                cur_incexp=get_base_cur(),
                amount=gain, # gain is already expressed in base currency
                amount_base=gain, # gain is already expressed in base currency
                description='fx gain' if gain >=0 else 'fx loss'
            )
            entries.append(fx_gain)
        
        # add tax (use base currency)
        tax_amount_base_cur = self.fx_service.convert_to_base(
            amount=invoice.tax_amount, # total tax across all items # type: ignore
            src_currency=invoice.currency, # invoice currency
            cur_dt=invoice.invoice_dt, # convert fx at invoice date
        )
        tax = Entry(
            entry_type=EntryType.CREDIT, # tax is credit entry
            # tax account is output tax -- predefined
            acct=self.acct_service.get_account(SystemAcctNumber.OUTPUT_TAX),
            cur_incexp=None,
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
            acct=self.acct_service.get_account(SystemAcctNumber.SHIP_CHARGE),
            cur_incexp=invoice.currency, # shipping currency is invoice currency
            amount=invoice.shipping, # amount in raw currency
            # amount in base currency
            amount_base = self.fx_service.convert_to_base(
                amount=invoice.shipping, # total shipping across all items
                src_currency=invoice.currency, # invoice currency
                cur_dt=invoice.invoice_dt, # convert fx at invoice date
            ),
            description=f'shipping charge'
        )
        entries.append(shipping)
        
        # add account receivable (use base currency)
        ar_base_cur = self.fx_service.convert_to_base(
            amount=invoice.total, # total after tax and shipping # type: ignore
            src_currency=invoice.currency, # invoice currency
            cur_dt=invoice.invoice_dt, # convert fx at invoice date
        )
        ar = Entry(
            entry_type=EntryType.DEBIT, # A/R is debit entry
            # A/R is output tax -- predefined
            acct=self.acct_service.get_account(SystemAcctNumber.ACCT_RECEIV),
            cur_incexp=None,
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
    
    def create_journal_from_payment(self, payment: Payment) -> Journal:
        self._validate_payment(payment)
        
        payment_acct = self.acct_service.get_account(payment.payment_acct_id)
        entries = []
        
        # AR/AP offset amount, expressed in base currency
        ar_offset_raw_base = 0
        for payment_item in payment.payment_items:
            _invoice, _jrn_id  = self.invoice_dao.get(payment_item.invoice_id)
            amount_base = self.fx_service.convert_to_base(
                amount=payment_item.payment_amount_raw, # amount deducted in invoice currency
                src_currency=_invoice.currency, # invoice currency
                # for A/R, A/P offset by payment, it should reflect amount at invoice date
                cur_dt=_invoice.invoice_dt, # convert fx at invoice date # TODO: convert at invoice date or payment date?
            )
            ar_offset_raw_base += amount_base
        
        ar = Entry(
            entry_type=EntryType.CREDIT, # offset A/R is credit entry
            acct=self.acct_service.get_account(SystemAcctNumber.ACCT_RECEIV),
            cur_incexp=None,
            amount=ar_offset_raw_base, # amount in base currency
            amount_base=ar_offset_raw_base, # amount in base currency
            description=f'account receivable offset, converting to base currency using fx rate at invoice date'
        )
        entries.append(ar)
        
        # payment fee entry
        fee_amount_base = self.fx_service.convert_to_base(
            amount=payment.payment_fee,
            src_currency=payment_acct.currency, # type: ignore payment currency 
            cur_dt=payment.payment_dt, # convert at payment date
        )
        fee = Entry(
            entry_type=EntryType.DEBIT, # fee is expense, debit entry
            acct=self.acct_service.get_account(SystemAcctNumber.BANK_FEE), # debit to bank fee
            cur_incexp=payment_acct.currency, # payment currency
            amount=payment.payment_fee, # in payment currency
            amount_base=fee_amount_base, # converted to base currency
            description='bank fee charged for payment'
        )
        entries.append(fee)
        
        # bank transfer entry (payment account)
        net_pmt = payment.net_payment
        pmt_amount_base = self.fx_service.convert_to_base(
            amount=net_pmt, # total payment before fee # type: ignore
            src_currency=payment_acct.currency, # type: ignore payment currency
            cur_dt=payment.payment_dt, # convert at payment date
        )
        pmt = Entry(
            entry_type=EntryType.DEBIT, # payment receive is debit entry
            acct=payment_acct, # debit to payment account
            cur_incexp=None,
            amount=net_pmt, # in payment currency # type: ignore
            amount_base=pmt_amount_base, # converted to base currency
            description='total payment received (net of fee)'
        )
        entries.append(pmt)
        
        # add fx gain/loss
        gain = (pmt_amount_base + fee_amount_base) - ar_offset_raw_base # received more than A/R
        fx_gain = Entry(
            entry_type=EntryType.CREDIT, # fx gain is credit
            acct=self.acct_service.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
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
        
    
    def _validate_item(self, item: Item):
        # validate the default_acct_id is income/expense account
        default_item_acct: Account = self.acct_service.get_account(item.default_acct_id)
        # invoice to customer, the acct type must be of income type
        if not default_item_acct.acct_type in (AcctType.INC, ):
            raise NotMatchWithSystemError(
                message=f"Default acct type of sales invoice item must be of Income type, get {default_item_acct.acct_type}"
            )
            
    def _validate_invoice(self, invoice: Invoice) -> Invoice:
        # validate direction
        if not invoice.entity_type == EntityType.CUSTOMER:
            raise OpNotPermittedError('Sales invoice should only be created for customer')
        # validate customer exist
        try:
            self.entity_service.get_customer(invoice.entity_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Customer id {invoice.entity_id} does not exist",
                details=e.details
            )
        
        # validate invoice_items
        for invoice_item in invoice.invoice_items:
            # validate item exist
            try:
                item = self.item_service.get_item(invoice_item.item.item_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Item {invoice_item.item} does not exist",
                    details=e.details
                )
            else:
                # validate item
                try:
                    self._validate_item(invoice_item.item)
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
                item_acct = self.acct_service.get_account(invoice_item.acct_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Account {invoice_item.acct_id} of Invoice Item {invoice_item} does not exist",
                    details=e.details
                )
            else:
                # validate if it is of income type
                if not item_acct.acct_type in (AcctType.INC, ):
                    raise NotMatchWithSystemError(
                        message=f"Item Acct type of sales invoice item must be of Income type, get {item_acct.acct_type}"
                    )
        
        # validate general invoice_items
        for ginvoice_item in invoice.ginvoice_items:
            # validate account id exist
            try:
                gitem_acct = self.acct_service.get_account(ginvoice_item.acct_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Account {ginvoice_item.acct_id} of General Invoice Item {ginvoice_item} does not exist",
                    details=e.details
                )
            else:
                # validate if it is of income/expense type
                if not gitem_acct.acct_type in (AcctType.INC, AcctType.EXP):
                    raise NotMatchWithSystemError(
                        message=f"General Item Acct type of sales invoice item must be of Income/Expense type, get {item_acct.acct_type}"
                    )
        
        return invoice
            
                
    def _validate_payment(self, payment: Payment) -> Payment:
        # validate direction
        if not payment.entity_type == EntityType.CUSTOMER:
            raise OpNotPermittedError('Sales payment should only be created for customer')
        
        # validate payment account id exist
        try:
            payment_acct = self.acct_service.get_account(payment.payment_acct_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Account {payment.payment_acct_id} of Payment {payment} does not exist",
                details=e.details
            )
        
        # validate payment account, must be balance sheet item
        if payment_acct.acct_type not in (AcctType.AST, AcctType.LIB, AcctType.EQU):
            raise OpNotPermittedError(f'Payment account can only be of balance sheet item')
        
        # validate payment items
        for payment_item in payment.payment_items:
            # validate invoice exist or not
            try:
                _invoice, _jrn_id  = self.invoice_dao.get(payment_item.invoice_id)
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
                        f'Same payment and invoice currency ({payment_acct.currency}), payment_amount should equal to payment_amount_raw; '
                        f'payment item amount not expected: {payment_item}'
                    )
        
        return payment
    
    def add_invoice(self, invoice: Invoice):
        
        # see if invoice already exist
        try:
            _invoice, _jrn_id  = self.invoice_dao.get(invoice.invoice_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_invoice(invoice)
            # add journal first
            journal = self.create_journal_from_invoice(invoice)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
            
            # add invoice
            try:
                self.invoice_dao.add(journal_id = journal.journal_id, invoice = invoice)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of invoice does not exist: {invoice}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'Invoice Number already exist, change one please',
                    details=f"payment number: {invoice.invoice_num}"
                )
            
        else:
            raise AlreadyExistError(
                f"Invoice id {invoice.invoice_id} already exist",
                details=f"Invoice: {_invoice}, journal_id: {_jrn_id}"
            )
            
    def add_payment(self, payment: Payment):
        # see if payment already exist
        try:
            _payment, _jrn_id  = self.payment_dao.get(payment.payment_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_payment(payment)
            # add journal first
            journal = self.create_journal_from_payment(payment)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
            
            # add payment
            try:
                self.payment_dao.add(journal_id = journal.journal_id, payment = payment)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of payment does not exist: {payment}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'Payment Number already exist: , change one please',
                    details=f"payment number: {payment.payment_num}"
                )
            
        else:
            raise AlreadyExistError(
                f"Payment id {payment.payment_id} already exist",
                details=f"Payment: {_payment}, journal_id: {_jrn_id}"
            )
            
    def get_invoice_journal(self, invoice_id: str) -> Tuple[Invoice, Journal]:
        try:
            invoice, jrn_id = self.invoice_dao.get(invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_invoice(invoice)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return invoice, journal
    
    def get_payment_journal(self, payment_id: str) -> Tuple[Payment, Journal]:
        try:
            payment, jrn_id = self.payment_dao.get(payment_id)
        except NotExistError as e:
            raise NotExistError(
                f'Payment id {payment_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_payment(payment)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return payment, journal
    
    def delete_invoice(self, invoice_id: str):
        # remove journal first
        # get journal
        try:
            invoice, jrn_id  = self.invoice_dao.get(invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice_id} does not exist',
                details=e.details
            )
            
        # remove invoice first
        try:
            self.invoice_dao.remove(invoice_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Invoice {invoice_id} have dependency cannot be deleted",
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
            
    def delete_payment(self, payment_id: str):
        # remove journal first
        # get journal
        try:
            payment, jrn_id  = self.payment_dao.get(payment_id)
        except NotExistError as e:
            raise NotExistError(
                f'Payment id {payment_id} does not exist',
                details=e.details
            )
            
        # remove payment first
        try:
            self.payment_dao.remove(payment_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Payment {payment_id} have dependency cannot be deleted",
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
            
        
    def update_invoice(self, invoice: Invoice):
        self._validate_invoice(invoice)
        # only delete if validation passed
        # cls.delete_invoice(invoice.invoice_id)
        # cls.add_invoice(invoice)
        
        # get existing journal id
        try:
            _invoice, jrn_id  = self.invoice_dao.get(invoice.invoice_id)
        except NotExistError as e:
            raise NotExistError(
                f'Invoice id {invoice.invoice_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_invoice(invoice)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update invoice
        try:
            self.invoice_dao.update(
                journal_id=journal.journal_id, # use new journal id
                invoice=invoice
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Invoice element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def update_payment(self, payment: Payment):
        self._validate_payment(payment)
        # only delete if validation passed
        # cls.delete_payment(payment.payment_id)
        # cls.add_payment(payment)
        
        # get existing journal id
        try:
            _payment, jrn_id  = self.payment_dao.get(payment.payment_id)
        except NotExistError as e:
            raise NotExistError(
                f'Payment id {payment.payment_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_payment(payment)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update payment
        try:
            self.payment_dao.update(
                journal_id=journal.journal_id, # use new journal id
                payment=payment
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Payment element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def list_invoice(
        self,
        limit: int = 50,
        offset: int = 0,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        customer_ids: list[str] | None = None,
        customer_names: list[str] | None = None,
        is_business: bool | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        subject_keyword: str = '',
        currency: CurType | None = None,
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_invoice_items: int | None = None
    ) -> list[_InvoiceBrief]:
        return self.invoice_dao.list_invoice(
            limit=limit,
            offset=offset,
            entity_type=EntityType.CUSTOMER,
            invoice_ids=invoice_ids,
            invoice_nums=invoice_nums,
            entity_ids=customer_ids,
            entity_names=customer_names,
            is_business=is_business,
            min_dt=min_dt,
            max_dt=max_dt,
            subject_keyword=subject_keyword,
            currency=currency,
            min_amount=min_amount,
            max_amount=max_amount,
            num_invoice_items=num_invoice_items
        )
        
    def list_payment(
        self,
        limit: int = 50,
        offset: int = 0,
        payment_ids: list[str] | None = None,
        payment_nums: list[str] | None = None,
        payment_acct_id: str | None = None,
        payment_acct_name: str | None = None,
        invoice_ids: list[str] | None = None,
        invoice_nums: list[str] | None = None,
        currency: CurType | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31),
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_invoices: int | None = None
    ) -> list[_PaymentBrief]:
        return self.payment_dao.list_payment(
            limit=limit,
            offset=offset,
            entity_type=EntityType.CUSTOMER,
            payment_ids=payment_ids,
            payment_nums=payment_nums,
            payment_acct_id=payment_acct_id,
            payment_acct_name=payment_acct_name,
            invoice_ids=invoice_ids,
            invoice_nums=invoice_nums,
            currency=currency,
            min_dt=min_dt,
            max_dt=max_dt,
            min_amount=min_amount,
            max_amount=max_amount,
            num_invoices=num_invoices
        )
        
    def get_invoice_balance(self, invoice_id: str, bal_dt: date) -> _InvoiceBalance:
        return self.invoice_dao.get_invoice_balance(
            invoice_id=invoice_id,
            bal_dt=bal_dt
        )
        
    def get_invoices_balance_by_entity(self, entity_id: str, bal_dt: date) -> list[_InvoiceBalance]:
        return self.invoice_dao.get_invoices_balance_by_entity(
            entity_id=entity_id,
            bal_dt=bal_dt
        )