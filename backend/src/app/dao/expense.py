from datetime import date
import logging
from typing import Tuple
from sqlalchemy import JSON, column
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import CurType, EntryType
from src.app.model.expense import _ExpenseBrief, _ExpenseSummaryBrief, ExpenseItem, Expense, ExpInfo
from src.app.dao.orm import AcctORM, EntryORM, ExpenseItemORM, ExpenseORM, infer_integrity_error
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, FKNoDeleteUpdateError


class expenseDao:
    
    def __init__(self, session: Session):
        self.session = session
    
    def fromExpenseItem(self, expense_id: str, expense_item: ExpenseItem) -> ExpenseItemORM:
        return ExpenseItemORM(
            expense_item_id=expense_item.expense_item_id,
            expense_id=expense_id,
            expense_acct_id=expense_item.expense_acct_id,
            amount_pre_tax=expense_item.amount_pre_tax,
            tax_rate=expense_item.tax_rate,
            description=expense_item.description,
        )
        
    
    def toExpenseItem(self, expense_item_orm: ExpenseItemORM) -> ExpenseItem:
        return ExpenseItem(
            expense_item_id=expense_item_orm.expense_item_id,
            expense_acct_id=expense_item_orm.expense_acct_id,
            amount_pre_tax=expense_item_orm.amount_pre_tax,
            tax_rate=expense_item_orm.tax_rate,
            description=expense_item_orm.description,
        )
        
    
    def fromExpense(self, journal_id: str, expense: Expense) -> ExpenseORM:
        return ExpenseORM(
            expense_id=expense.expense_id,
            expense_dt=expense.expense_dt,
            currency=expense.currency,
            payment_acct_id=expense.payment_acct_id,
            payment_amount=expense.payment_amount,
            exp_info=expense.exp_info.model_dump(),
            receipts=expense.receipts,
            note=expense.note,
            journal_id=journal_id # TODO
        )
        
    
    def toExpense(self, expense_orm: ExpenseORM, expense_item_orms: list[ExpenseItemORM]) -> Expense:
        # receipts should be list or None
        if expense_orm.receipts == 'null':
            expense_orm.receipts = None
        
        return Expense(
            expense_id=expense_orm.expense_id,
            expense_dt=expense_orm.expense_dt,
            currency=expense_orm.currency,
            expense_items=[
                self.toExpenseItem(expense_item_orm) 
                for expense_item_orm in expense_item_orms
            ],
            payment_acct_id=expense_orm.payment_acct_id,
            payment_amount=expense_orm.payment_amount,
            exp_info=ExpInfo.model_validate(expense_orm.exp_info),
            receipts=expense_orm.receipts,
            note=expense_orm.note,
        )
        
    
    def add(self, journal_id: str, expense: Expense):
        # add expense first
        expense_orm = self.fromExpense(journal_id, expense)
        
        self.session.add(expense_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
        # add expense items
        for expense_item in expense.expense_items:
            expense_item_orm = self.fromExpenseItem(
                expense_id=expense.expense_id,
                expense_item=expense_item
            )
            self.session.add(expense_item_orm)
        
        # commit all items
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    
    def remove(self, expense_id: str):
        # only remove expense, not journal, journal will be removed in journalDao
        try:
            # remove expense items first
            sql = delete(ExpenseItemORM).where(
                ExpenseItemORM.expense_id == expense_id
            )
            self.session.exec(sql) # type: ignore
            # remove expense
            sql = delete(ExpenseORM).where(
                ExpenseORM.expense_id == expense_id
            )
            self.session.exec(sql) # type: ignore
            
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
        
    
    def get(self, expense_id: str) -> Tuple[Expense, str]:
        # return both expense id and journal id
        # get expense items
        sql = select(ExpenseItemORM).where(
            ExpenseItemORM.expense_id == expense_id
        )
        try:
            expense_item_orms = self.session.exec(sql).all()
        except NoResultFound as e:
            raise NotExistError(details=str(e))

        # get expense
        sql = select(ExpenseORM).where(
            ExpenseORM.expense_id == expense_id
        )
        try:
            expense_orm = self.session.exec(sql).one() # get the expense
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        expense = self.toExpense(
            expense_orm=expense_orm,
            expense_item_orms=expense_item_orms
        )
        jrn_id = expense_orm.journal_id
        
        return expense, jrn_id
    
    
    def update(self, journal_id: str, expense: Expense):
        # journal_id is the new journal created first before calling this API
        # update expense first
        sql = select(ExpenseORM).where(
            ExpenseORM.expense_id == expense.expense_id,
        )
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        expense_orm = self.fromExpense(
            journal_id=journal_id,
            expense=expense
        )
        # must update expense orm because journal id changed
        p.expense_dt = expense_orm.expense_dt
        p.currency = expense_orm.currency
        p.payment_acct_id = expense_orm.payment_acct_id
        p.payment_amount = expense_orm.payment_amount
        p.exp_info = expense_orm.exp_info
        p.note = expense_orm.note
        p.receipts = expense_orm.receipts
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.session.add(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.session.refresh(p) # update p to instantly have new values
            
        # remove existing expense items
        sql = delete(ExpenseItemORM).where(
            ExpenseItemORM.expense_id == expense.expense_id
        )
        self.session.exec(sql) # type: ignore
        
        # add new expense items
        # add individual expense items
        for expense_item in expense.expense_items:
            expense_item_orm = self.fromExpenseItem(
                expense_id=expense.expense_id,
                expense_item=expense_item
            )
            self.session.add(expense_item_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback() # will rollback both item removal and new item add
            raise FKNotExistError(
                details=str(e)
            )
        
    
    
    def list_expense(
        self,
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
        # return list of filtered expense, and count without applying limit and offset         
        acct_case_when = []
        if expense_acct_ids is not None:
            acct_case_when.append(
                f.max(
                    case(
                        (AcctORM.acct_id.in_(expense_acct_ids), 1), # type: ignore
                        else_=0
                    )
                ).label('contains_acct_id'),
            )
        if expense_acct_names is not None:
            acct_case_when.append(
                f.max(
                    case(
                        (AcctORM.acct_name.in_(expense_acct_names), 1), # type: ignore
                        else_=0
                    )
                ).label('contains_acct_name')
            )
        
        expense_summary = (
            select(
                ExpenseItemORM.expense_id,
                f.group_concat(AcctORM.acct_name).label('expense_acct_name_strs'),
                f.sum(
                    ExpenseItemORM.amount_pre_tax * (1 + ExpenseItemORM.tax_rate)
                ).label('total_raw_amount'),
                *acct_case_when
            )
            .join(
                AcctORM,
                onclause=ExpenseItemORM.expense_acct_id == AcctORM.acct_id, 
                isouter=True # outer join
            )
            .group_by(
                ExpenseItemORM.expense_id
            )
            .subquery()
        )
        journal_summary = (
            select(
                EntryORM.journal_id,
                f.sum(EntryORM.amount_base).label('amount_base')
            )
            .where(
                EntryORM.entry_type == EntryType.DEBIT
            )
            .group_by(
                EntryORM.journal_id
            )
            .subquery()
        )
        
        exp_filters = [
            ExpenseORM.expense_dt.between(min_dt, max_dt), # type: ignore
            journal_summary.c.amount_base
            .between(min_amount, max_amount)
        ]
        # add currency filter
        if currency is not None:
            exp_filters.append(ExpenseORM.currency == currency)
        if expense_ids is not None:
            exp_filters.append(ExpenseORM.expense_id.in_(expense_ids)) # type: ignore
        if payment_acct_id is not None:
            exp_filters.append(ExpenseORM.payment_acct_id == payment_acct_id)
        if payment_acct_name is not None:
            exp_filters.append(AcctORM.acct_name == payment_acct_name)
        if has_receipt is not None:
            exp_filters.append(
                case(
                    (ExpenseORM.receipts.is_(JSON.NULL), False), # type: ignore
                    else_=True
                ) == has_receipt
            )
        if expense_acct_ids is not None:
            exp_filters.append(expense_summary.c.contains_acct_id == 1)
        if expense_acct_names is not None:
            exp_filters.append(expense_summary.c.contains_acct_name == 1)
            
        expense_joined = (
            select(
                ExpenseORM.expense_id,
                ExpenseORM.expense_dt,
                ExpenseORM.exp_info, # TODO, extract exp_info
                ExpenseORM.currency,
                AcctORM.acct_name.label('payment_acct_name'), # type: ignore
                expense_summary.c.expense_acct_name_strs,
                expense_summary.c.total_raw_amount,
                journal_summary.c.amount_base.label('total_base_amount'), # type: ignore
                case(
                    (ExpenseORM.receipts.is_(None), False), # type: ignore
                    else_=True
                ).label('has_receipt')
            )
            .join(
                AcctORM,
                onclause=ExpenseORM.payment_acct_id == AcctORM.acct_id, 
                isouter=True # outer join
            )
            .join(
                expense_summary,
                onclause=ExpenseORM.expense_id  == expense_summary.c.expense_id, 
                isouter=False
            )
            .join(
                journal_summary,
                onclause=ExpenseORM.journal_id  == journal_summary.c.journal_id, 
                isouter=False
            )
            .where(
                *exp_filters
            )
            .order_by(ExpenseORM.expense_dt.desc(), ExpenseORM.expense_id) # type: ignore
            .offset(offset)
            .limit(limit)
        )
        
        count_sql = (
            select(
                f.count(ExpenseORM.expense_id)
            )
            .join(
                AcctORM,
                onclause=ExpenseORM.payment_acct_id == AcctORM.acct_id, 
                isouter=True # outer join
            )
            .join(
                expense_summary,
                onclause=ExpenseORM.expense_id  == expense_summary.c.expense_id, 
                isouter=False
            )
            .join(
                journal_summary,
                onclause=ExpenseORM.journal_id  == journal_summary.c.journal_id, 
                isouter=False
            )
            .where(*exp_filters)
        )
        
        try:
            expenses = self.session.exec(expense_joined).all()
            num_records = self.session.exec(count_sql).one()
        except NoResultFound as e:
            return [], 0
            
        return [
            _ExpenseBrief(
                expense_id=expense.expense_id,
                expense_dt=expense.expense_dt,
                merchant=ExpInfo.model_validate(expense.exp_info).merchant.merchant,
                currency=expense.currency,
                payment_acct_name=expense.payment_acct_name,
                expense_acct_name_strs=expense.expense_acct_name_strs,
                total_raw_amount=expense.total_raw_amount,
                total_base_amount=expense.total_base_amount,
                has_receipt=expense.has_receipt
            ) 
            for expense in expenses
        ], num_records
        
        
    
    def summary_expense(self, start_dt: date, end_dt: date) -> list[_ExpenseSummaryBrief]:
        journal_summary = (
            select(
                EntryORM.journal_id,
                f.sum(EntryORM.amount_base).label('amount_base')
            )
            .where(
                EntryORM.entry_type == EntryType.DEBIT
            )
            .group_by(
                EntryORM.journal_id
            )
            .subquery()
        )
        
        expense_item_summary = (
            select(
                ExpenseItemORM.expense_acct_id,
                ExpenseItemORM.expense_id,
                ExpenseORM.expense_dt,
                # (ExpenseItemORM.amount_pre_tax * (1 + ExpenseItemORM.tax_rate)).label('raw_amount_after_tax'),
                # f.sum(
                #     ExpenseItemORM.amount_pre_tax * (1 + ExpenseItemORM.tax_rate)
                # ).over(partition_by=[ExpenseItemORM.expense_id]).label('exp_raw_amount_after_tax'),
                # journal_summary.c.amount_base,
                (
                    journal_summary.c.amount_base 
                    * ExpenseItemORM.amount_pre_tax 
                    * (1 + ExpenseItemORM.tax_rate) 
                    / f.sum(
                        ExpenseItemORM.amount_pre_tax * (1 + ExpenseItemORM.tax_rate)
                    ).over(
                        partition_by=[ExpenseItemORM.expense_id]
                    )
                ).label('base_amount_after_tax')
            )
            .join(
                ExpenseORM,
                onclause=ExpenseORM.expense_id == ExpenseItemORM.expense_id, 
                isouter=False # inner join
            )
            .join(
                journal_summary,
                onclause=ExpenseORM.journal_id == journal_summary.c.journal_id, 
                isouter=True # outer join
            )
            .where(
                ExpenseORM.expense_dt.between(start_dt, end_dt) # type: ignore
            )
            .subquery()
        )
        
        expense_summary = (
            select(
                AcctORM.acct_name,
                f.sum(
                    expense_item_summary.c.base_amount_after_tax
                ).label('total_base_amount')
            )
            .join(
                AcctORM,
                onclause=expense_item_summary.c.expense_acct_id == AcctORM.acct_id, 
                isouter=False # inner join
            )
            .group_by(
                AcctORM.acct_name
            )
            .order_by(column('total_base_amount').desc())
        )
        
        try:
            expenses = self.session.exec(expense_summary).all()
        except NoResultFound as e:
            return []
            
        return [
            _ExpenseSummaryBrief(
                expense_type=expense.acct_name,
                total_base_amount=expense.total_base_amount,
            ) 
            for expense in expenses
        ]