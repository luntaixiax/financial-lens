from datetime import date
import logging
from typing import Tuple
from sqlalchemy import JSON
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import CurType, EntryType
from src.app.model.expense import _ExpenseBrief, ExpenseItem, Expense, Merchant
from src.app.dao.orm import EntryORM, ExpenseItemORM, ExpenseORM, infer_integrity_error
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, NotExistError, FKNoDeleteUpdateError


class expenseDao:
    @classmethod
    def fromExpenseItem(cls, expense_id: str, expense_item: ExpenseItem) -> ExpenseItemORM:
        return ExpenseItemORM(
            expense_item_id=expense_item.expense_item_id,
            expense_id=expense_id,
            expense_acct_id=expense_item.expense_acct_id,
            amount_pre_tax=expense_item.amount_pre_tax,
            tax_rate=expense_item.tax_rate,
            description=expense_item.description,
        )
        
    @classmethod
    def toExpenseItem(cls, expense_item_orm: ExpenseItemORM) -> ExpenseItem:
        return ExpenseItem(
            expense_item_id=expense_item_orm.expense_item_id,
            expense_acct_id=expense_item_orm.expense_acct_id,
            amount_pre_tax=expense_item_orm.amount_pre_tax,
            tax_rate=expense_item_orm.tax_rate,
            description=expense_item_orm.description,
        )
        
    @classmethod
    def fromExpense(cls, journal_id: str, expense: Expense) -> ExpenseORM:
        return ExpenseORM(
            expense_id=expense.expense_id,
            expense_dt=expense.expense_dt,
            currency=expense.currency,
            payment_acct_id=expense.payment_acct_id,
            payment_amount=expense.payment_amount,
            merchant=expense.merchant.model_dump(),
            receipts=expense.receipts,
            note=expense.note,
            journal_id=journal_id # TODO
        )
        
    @classmethod
    def toExpense(cls, expense_orm: ExpenseORM, expense_item_orms: list[ExpenseItemORM]) -> Expense:
        return Expense(
            expense_id=expense_orm.expense_id,
            expense_dt=expense_orm.expense_dt,
            currency=expense_orm.currency,
            expense_items=[
                cls.toExpenseItem(expense_item_orm) 
                for expense_item_orm in expense_item_orms
            ],
            payment_acct_id=expense_orm.payment_acct_id,
            payment_amount=expense_orm.payment_amount,
            merchant=Merchant.model_validate(expense_orm.merchant),
            receipts=expense_orm.receipts,
            note=expense_orm.note,
        )
        
    @classmethod
    def add(cls, journal_id: str, expense: Expense):
        with Session(get_engine()) as s:
            # add expense first
            expense_orm = cls.fromExpense(journal_id, expense)
            
            s.add(expense_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            logging.info(f"Added {expense_orm} to expense table")
            
            # add expense items
            for expense_item in expense.expense_items:
                expense_item_orm = cls.fromExpenseItem(
                    expense_id=expense.expense_id,
                    expense_item=expense_item
                )
                s.add(expense_item_orm)
                logging.info(f"Added {expense_item_orm} to expense Item table")
            
            # commit all items
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
        
    @classmethod
    def remove(cls, expense_id: str):
        # only remove expense, not journal, journal will be removed in journalDao
        with Session(get_engine()) as s:
            # remove expense items first
            sql = delete(ExpenseItemORM).where(
                ExpenseItemORM.expense_id == expense_id
            )
            s.exec(sql)
            # remove expense
            sql = delete(ExpenseORM).where(
                ExpenseORM.expense_id == expense_id
            )
            s.exec(sql)
            
            # commit at same time
            s.commit()
            logging.info(f"deleted expense and items for {expense_id}")
        
    @classmethod
    def get(cls, expense_id: str) -> Tuple[Expense, str]:
        # return both expense id and journal id
        with Session(get_engine()) as s:
           # get expense items
            sql = select(ExpenseItemORM).where(
                ExpenseItemORM.expense_id == expense_id
            )
            try:
                expense_item_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))

            # get expense
            sql = select(ExpenseORM).where(
                ExpenseORM.expense_id == expense_id
            )
            try:
                expense_orm = s.exec(sql).one() # get the expense
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            expense = cls.toExpense(
                expense_orm=expense_orm,
                expense_item_orms=expense_item_orms
            )
            jrn_id = expense_orm.journal_id
        return expense, jrn_id
    
    @classmethod
    def list(
        cls,
        limit: int = 50,
        offset: int = 0,
        expense_ids: list[str] | None = None,
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        currency: CurType | None = None,
        payment_acct_id: str | None = None,
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        has_receipt: bool | None = None
    ) -> list[_ExpenseBrief]:
        with Session(get_engine()) as s:
            
            expense_summary = (
                select(
                    ExpenseItemORM.expense_id,
                    f.sum(
                        ExpenseItemORM.amount_pre_tax * (1 + ExpenseItemORM.tax_rate)
                    ).label('total_raw_amount')
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
                ExpenseORM.expense_dt.between(min_dt, max_dt), 
                journal_summary.c.amount_base
                .between(min_amount, max_amount)
            ]
            # add currency filter
            if currency is not None:
                exp_filters.append(ExpenseORM.currency == currency)
            if expense_ids is not None:
                exp_filters.append(ExpenseORM.expense_id.in_(expense_ids))
            if payment_acct_id is not None:
                exp_filters.append(ExpenseORM.payment_acct_id == payment_acct_id)
            if has_receipt is not None:
                exp_filters.append(
                    case(
                        (ExpenseORM.receipts.is_(JSON.NULL), False),
                        else_=True
                    ) == has_receipt
                )
            expense_joined = (
                select(
                    ExpenseORM.expense_id,
                    ExpenseORM.expense_dt,
                    ExpenseORM.merchant, # TODO, extract merchant
                    ExpenseORM.currency,
                    expense_summary.c.total_raw_amount,
                    journal_summary.c.amount_base.label('total_base_amount'),
                    case(
                        (ExpenseORM.receipts.is_(None), False),
                        else_=True
                    ).label('has_receipt')
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
                .order_by(ExpenseORM.expense_dt.desc())
                .offset(offset)
                .limit(limit)
            )
            
            expenses = s.exec(expense_joined).all()
            
        return [
            _ExpenseBrief(
                expense_id=expense.expense_id,
                expense_dt=expense.expense_dt,
                merchant=Merchant.model_validate(expense.merchant).merchant,
                currency=expense.currency,
                total_raw_amount=expense.total_raw_amount,
                total_base_amount=expense.total_base_amount,
                has_receipt=expense.has_receipt
            ) 
            for expense in expenses
        ]