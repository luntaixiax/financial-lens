from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.expense import ExpenseItem, Expense, Merchant
from src.app.dao.orm import ExpenseItemORM, ExpenseORM, infer_integrity_error
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
        
    