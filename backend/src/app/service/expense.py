from datetime import date
import math
from time import sleep
from typing import Tuple
from src.app.utils.tools import get_base_cur
from src.app.dao.expense import expenseDao
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.const import SystemAcctNumber
from src.app.model.invoice import GeneralInvoiceItem
from src.app.service.acct import AcctService
from src.app.service.journal import JournalService
from src.app.service.fx import FxService
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntryType, JournalSrc
from src.app.model.expense import _ExpenseBrief, _ExpenseSummaryBrief, ExpenseItem, Expense, ExpInfo, Merchant
from src.app.model.journal import Journal, Entry

class ExpenseService:
    
    @classmethod
    def create_sample(cls):
        expense1 = Expense(
            expense_id='exp-sample1',
            expense_dt=date(2024, 1, 1),
            currency=get_base_cur(),
            expense_items=[
                ExpenseItem(
                    expense_item_id='sample-exp-item1',
                    expense_acct_id='acct-meal',
                    amount_pre_tax=98,
                    tax_rate=0.13,
                    description='4 course meals'
                ),
                ExpenseItem(
                    expense_item_id='sample-exp-item2',
                    expense_acct_id='acct-tip',
                    amount_pre_tax=13,
                    tax_rate=0,
                    description='tip for server'
                )
            ],
            payment_acct_id='acct-credit',
            payment_amount=123.74,
            exp_info=ExpInfo(
                merchant=Merchant(
                    merchant='Good Taste Sushi',
                    platform='Uber Eats',
                    ref_no='ub12345'
                ),
                external_pmt_acct='BNS Amex'
            ),
            note='Meal for client gathering',
            receipts=[
                'invoice.png',
                'receipt.pdf'
            ]
        )
        expense2 = Expense(
            expense_id='exp-sample2',
            expense_dt=date(2024, 1, 1),
            currency=CurType.EUR,
            expense_items=[
                ExpenseItem(
                    expense_item_id='sample-exp-item3',
                    expense_acct_id='acct-rental',
                    amount_pre_tax=980,
                    tax_rate=0.13,
                    description=None
                )
            ],
            payment_acct_id='acct-shareloan',
            payment_amount=1250, # paid EUR1250
            exp_info=ExpInfo(
                merchant=Merchant(
                    merchant='Shareholder',
                    platform=None,
                    ref_no='RENT-20240101'
                ),
                external_pmt_acct='Scotia Check'
            ),
            note='Rent for 2024-01-01',
            receipts=None
        )
        cls.add_expense(expense1)
        cls.add_expense(expense2)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_expense('exp-sample1')
        cls.delete_expense('exp-sample2')
        
    @classmethod
    def _validate_expense(cls, expense: Expense) -> Expense:
        try:
            payment_acct: Account = AcctService.get_account(
                expense.payment_acct_id
            )
        except NotExistError as e:
            raise FKNotExistError(
                f"Payment Account Id {expense.payment_acct_id} does not exist",
                details=e.details
            )
        
        # validate expense items
        for expense_item in expense.expense_items:
            # see if expense account id exist
            # validate account id exist
            try:
                AcctService.get_account(expense_item.expense_acct_id)
            except NotExistError as e:
                raise FKNotExistError(
                    f"Expense Account {expense_item.expense_acct_id} of Expense Item {expense_item} does not exist",
                    details=e.details
                )
        
        if expense.currency == payment_acct.currency:
            if not math.isclose(expense.total, expense.payment_amount, rel_tol=1e-6):
                raise NotMatchWithSystemError(
                    f"Expense currency equals Payment currency ({expense.currency})",
                    details=f"Expense amount: {expense.total}, while payment amount = {expense.payment_amount}"
                )
                
        return expense
    
    @classmethod
    def create_general_invoice_items_from_expense(cls, expense_id: str, invoice_currency: CurType) -> list[GeneralInvoiceItem]:
        expense, _ = cls.get_expense_journal(expense_id)
        
        ginv_items = []
        for expense_item in expense.expense_items:
            ginv_item = GeneralInvoiceItem(
                incur_dt=expense.expense_dt,
                acct_id=expense_item.expense_acct_id,
                currency=expense.currency,
                amount_pre_tax_raw=expense_item.amount_pre_tax,
                amount_pre_tax=FxService.convert(
                    amount=expense_item.amount_pre_tax,
                    src_currency=expense.currency, # convert from expense currency
                    tgt_currency=invoice_currency, # convert to invoice currency
                    cur_dt=expense.expense_dt, # convert fx at expense date
                ),
                tax_rate=expense_item.tax_rate,
                description=expense_item.description
            )
            ginv_items.append(ginv_item)
        return ginv_items
            
    
    @classmethod
    def create_journal_from_expense(cls, expense: Expense) -> Journal:
        cls._validate_expense(expense)
        
        # create journal entries
        entries = []
        expense_entry_base_amount = 0
        for expense_item in expense.expense_items:
            
            exp_acct: Account = AcctService.get_account(
                expense_item.expense_acct_id
            )
            
            # validate the exp account must be of expense type
            if not exp_acct.acct_type == AcctType.EXP:
                raise NotMatchWithSystemError(
                    message=f"Acct type of expense item must be of Expense type, get {exp_acct.acct_type}"
                )
            
            # assemble the entry item
            amount_base=FxService.convert_to_base(
                amount=expense_item.amount_pre_tax,
                src_currency=expense.currency, # expense currency
                cur_dt=expense.expense_dt, # convert fx at expense date
            )
            entry = Entry(
                entry_type=EntryType.DEBIT, # expense is debit entry
                acct=exp_acct,
                cur_incexp=expense.currency, # currency is expense currency
                amount=expense_item.amount_pre_tax, # amount in raw currency
                # amount in base currency
                amount_base=amount_base,
                description=expense_item.description
            )
            entries.append(entry)
            expense_entry_base_amount += amount_base
            
        # add tax (use base currency)
        tax_amount_base_cur = FxService.convert_to_base(
            amount=expense.tax_amount, # total tax across all expenses
            src_currency=expense.currency, # expense currency
            cur_dt=expense.expense_dt, # convert fx at expense date
        )
        tax = Entry(
            entry_type=EntryType.DEBIT, # tax is debit entry
            # tax account is input tax -- predefined
            acct=AcctService.get_account(SystemAcctNumber.INPUT_TAX),
            amount=tax_amount_base_cur, # amount in raw currency
            # amount in base currency
            amount_base=tax_amount_base_cur,
            description=f'input tax in base currency'
        )
        entries.append(tax)
        
        # add payment account (use account currency)
        payment_acct: Account = AcctService.get_account(
            expense.payment_acct_id
        )
        payment_amount_base=FxService.convert_to_base(
            amount=expense.payment_amount, # payment amount in payment currency
            src_currency=payment_acct.currency, # payment currency
            cur_dt=expense.expense_dt, # convert fx at expense date
        )
        payment = Entry(
            entry_type=EntryType.CREDIT, # payment is credit entry
            acct=payment_acct,
            amount=expense.payment_amount, # should equal to total expense amount
            amount_base=payment_amount_base,
            description='payment for the expense'
        )
        entries.append(payment)
        if not expense.currency == payment_acct.currency:
            # record amount credit in payment currency, and record any discrepancy as FX gain
            total_exp_base = expense_entry_base_amount + tax_amount_base_cur
            gain = total_exp_base - payment_amount_base # paid less than owed
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
            jrn_date=expense.expense_dt,
            entries=entries,
            jrn_src=JournalSrc.EXPENSE,
            note=expense.note
        )
        journal.reduce_entries()
        return journal
    
    @classmethod
    def add_expense(cls, expense: Expense):
        
        # see if expense already exist
        try:
            _expense, _jrn_id  = expenseDao.get(expense.expense_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_expense(expense)
            # add journal first
            journal = cls.create_journal_from_expense(expense)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
            
            # add expense
            try:
                expenseDao.add(journal_id = journal.journal_id, expense = expense)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of expense does not exist: {expense}',
                    details=e.details
                )
            
        else:
            raise AlreadyExistError(
                f"Expense id {expense.expense_id} already exist",
                details=f"Expense: {_expense}, journal_id: {_jrn_id}"
            )
            
    @classmethod
    def add_expenses(cls, expenses: list[Expense]):
        errs = []
        err_exps = []
        dup_exps = []
        for i, expense in enumerate(expenses):
            try:
                cls.add_expense(expense)
            except (FKNotExistError, NotMatchWithSystemError, FKNoDeleteUpdateError, OpNotPermittedError) as e:
                errs.append(e)
                err_exps.append(expense)
            except AlreadyExistError as e:
                dup_exps.append(expense)
                
            # not to pressure db # TODO optimize
            # if i % 10:
            #     sleep(1)
        
        if len(err_exps) > 0:
            raise OpNotPermittedError(
                message="Several expenses not added due to error",
                details="\n".join(f"Error ({er}), Expense {exp}" for er, exp in zip(errs, err_exps))
            )
            
            
    @classmethod
    def delete_expense(cls, expense_id: str):
        # remove journal first
        # get journal
        try:
            expense, jrn_id  = expenseDao.get(expense_id)
        except NotExistError as e:
            raise NotExistError(
                f'Expense id {expense_id} does not exist',
                details=e.details
            )
            
        # remove expense first
        try:
            expenseDao.remove(expense_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Expense {expense_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def update_expense(cls, expense: Expense):
        cls._validate_expense(expense)
        # only delete if validation passed
        # cls.delete_expense(expense.expense_id)
        # cls.add_expense(expense)
        
        # get existing journal id
        try:
            _expense, jrn_id  = expenseDao.get(expense.expense_id)
        except NotExistError as e:
            raise NotExistError(
                f'Expense id {_expense.expense_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_expense(expense)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update expense
        try:
            expenseDao.update(
                journal_id=journal.journal_id, # use new journal id
                expense=expense
            ) # TODO
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
    def get_expense_journal(cls, expense_id: str) -> Tuple[Expense, Journal]:
        try:
            expense, jrn_id = expenseDao.get(expense_id)
        except NotExistError as e:
            raise NotExistError(
                f'Expense id {expense_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_expense(expense)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return expense, journal
        
    @classmethod
    def list_expense(
        cls,
        limit: int = 50,
        offset: int = 0,
        expense_ids: list[str] | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        currency: CurType | None = None,
        payment_acct_id: str | None = None,
        payment_acct_name: str | None = None,
        expense_acct_ids: list[str] | None = None,
        expense_acct_names: list[str] | None = None,
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        has_receipt: bool | None = None
    ) -> Tuple[list[_ExpenseBrief], int]:
        return expenseDao.list_expense(
            limit=limit,
            offset=offset,
            expense_ids=expense_ids,
            min_dt=min_dt,
            max_dt=max_dt,
            payment_acct_id=payment_acct_id,
            payment_acct_name=payment_acct_name,
            expense_acct_ids=expense_acct_ids,
            expense_acct_names=expense_acct_names,
            currency=currency,
            min_amount=min_amount,
            max_amount=max_amount,
            has_receipt=has_receipt
        )
        
    @classmethod
    def summary_expense(cls, start_dt: date, end_dt: date) -> list[_ExpenseSummaryBrief]:
        return expenseDao.summary_expense(
            start_dt=start_dt,
            end_dt=end_dt
        )