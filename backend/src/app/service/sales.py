from src.app.model.const import SystemAcctNumber
from src.app.service.acct import AcctService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, EntryType
from src.app.model.invoice import Invoice
from src.app.model.journal import Journal, Entry


class SalesService:
    
    @classmethod
    def create_journal_from_invoice(cls, invoice: Invoice) -> Journal:
        
        entries = []
        # create sales invoice entries
        for invoice_item in invoice.invoice_items:
            # get the invoice item account for journal entry line item
            item_acct_id = invoice_item.acct_id # the account id for this entry
            item_acct: Account = AcctService.get_account(item_acct_id)
            
            # validate the item account must be of income type
            if not item_acct.acct_type == AcctType.INC:
                raise TypeError(f"Acct type of invoice item must be of Income type, get {item_acct.acct_type}")
            
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