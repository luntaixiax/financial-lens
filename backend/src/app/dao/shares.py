
from datetime import date
import logging
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.exceptions import FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.orm import DividendORM, StockIssueORM, StockRepurchaseORM
from src.app.model.shares import Dividend, StockIssue, StockRepurchase
from src.app.dao.orm import infer_integrity_error
from src.app.dao.connection import get_engine

class stockIssueDao:
    
    @classmethod
    def fromStockIssue(cls, journal_id: str, stock_issue: StockIssue) -> StockIssueORM:
        return StockIssueORM(
            issue_id=stock_issue.issue_id,
            issue_dt=stock_issue.issue_dt,
            is_reissue=stock_issue.is_reissue,
            num_shares=stock_issue.num_shares,
            issue_price=stock_issue.issue_price,
            cost_price=stock_issue.cost_price,
            debit_acct_id=stock_issue.debit_acct_id,
            issue_amt=stock_issue.issue_amt,
            journal_id=journal_id
        )
        
    @classmethod
    def toStockIssue(cls, stock_issue_orm: StockIssueORM) -> StockIssue:
        return StockIssue(
            issue_id=stock_issue_orm.issue_id,
            issue_dt=stock_issue_orm.issue_dt,
            is_reissue=stock_issue_orm.is_reissue,
            num_shares=stock_issue_orm.num_shares,
            issue_price=stock_issue_orm.issue_price,
            cost_price=stock_issue_orm.cost_price,
            debit_acct_id=stock_issue_orm.debit_acct_id,
            issue_amt=stock_issue_orm.issue_amt,
        )
        
    @classmethod
    def add(cls, journal_id: str, stock_issue: StockIssue):
        with Session(get_engine()) as s:
            stock_issue_orm = cls.fromStockIssue(journal_id, stock_issue)
        s.add(stock_issue_orm)
        try:
            s.commit()
        except IntegrityError as e:
            s.rollback()
            raise infer_integrity_error(e, during_creation=True)
        logging.info(f"Added {stock_issue} to stock_issue table")
        
    @classmethod
    def remove(cls, issue_id: str):
        # remove stock_issue
        with Session(get_engine()) as s:
            sql = delete(StockIssueORM).where(
                StockIssueORM.issue_id == issue_id
            )
            s.exec(sql)
            
            # commit at same time
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(str(e))
            logging.info(f"deleted stock issue for {issue_id}")
            
    @classmethod
    def get(cls, issue_id: str) -> Tuple[StockIssue, str]:
        # return both issue id and journal id
        with Session(get_engine()) as s:

            # get stock_issue
            sql = select(StockIssueORM).where(
                StockIssueORM.issue_id == issue_id
            )
            try:
                stock_issue_orm = s.exec(sql).one() # get the stock_issue
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            stock_issue = cls.toStockIssue(
                stock_issue_orm=stock_issue_orm,
            )
            jrn_id = stock_issue_orm.journal_id
        return stock_issue, jrn_id
    
    @classmethod
    def update(cls, journal_id: str, stock_issue: StockIssue):
        with Session(get_engine()) as s:
            sql = select(StockIssueORM).where(
                StockIssueORM.issue_id == stock_issue.issue_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            stock_issue_orm = cls.fromStockIssue(
                journal_id=journal_id,
                stock_issue=stock_issue
            )
            # must update stock issue orm because journal id changed
            p.issue_dt = stock_issue_orm.issue_dt
            p.is_reissue = stock_issue_orm.is_reissue
            p.num_shares = stock_issue_orm.num_shares
            p.issue_price = stock_issue_orm.issue_price
            p.cost_price = stock_issue_orm.cost_price
            p.debit_acct_id = stock_issue_orm.debit_acct_id
            p.issue_amt = stock_issue_orm.stock_issue_orm
            p.journal_id = journal_id # update to new journal id
            
            try:
                s.add(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                s.refresh(p) # update p to instantly have new values
                
    @classmethod
    def list_issues(cls) -> list[StockIssue]:
        with Session(get_engine()) as s:

            # get stock_issue
            sql = select(StockIssueORM)
            try:
                stock_issue_orms = s.exec(sql).all() # get the issues
            except NoResultFound as e:
                return []
            
            stock_issues = [cls.toStockIssue(
                stock_issue_orm=stock_issue_orm,
            ) for stock_issue_orm in stock_issue_orms]
            
        return stock_issues
    
    
class stockRepurchaseDao:
    
    @classmethod
    def fromStockRepur(cls, journal_id: str, stock_repur: StockRepurchase) -> StockRepurchaseORM:
        return StockRepurchaseORM(
            repur_id=stock_repur.repur_id,
            repurchase_dt=stock_repur.repurchase_dt,
            num_shares=stock_repur.num_shares,
            repur_price=stock_repur.repur_price,
            credit_acct_id=stock_repur.credit_acct_id,
            repur_amt=stock_repur.repur_amt,
            journal_id=journal_id
        )
        
    @classmethod
    def toStockRepur(cls, stock_repur_orm: StockRepurchaseORM) -> StockRepurchase:
        return StockRepurchase(
            repur_id=stock_repur_orm.repur_id,
            repurchase_dt=stock_repur_orm.repurchase_dt,
            num_shares=stock_repur_orm.num_shares,
            repur_price=stock_repur_orm.repur_price,
            credit_acct_id=stock_repur_orm.credit_acct_id,
            repur_amt=stock_repur_orm.repur_amt,
        )
        
    @classmethod
    def add(cls, journal_id: str, stock_repur: StockRepurchase):
        with Session(get_engine()) as s:
            stock_repur_orm = cls.fromStockRepur(journal_id, stock_repur)
        s.add(stock_repur_orm)
        try:
            s.commit()
        except IntegrityError as e:
            s.rollback()
            raise infer_integrity_error(e, during_creation=True)
        logging.info(f"Added {stock_repur} to stock_repur table")
        
    @classmethod
    def remove(cls, repur_id: str):
        # remove stock_repur
        with Session(get_engine()) as s:
            sql = delete(StockRepurchaseORM).where(
                StockRepurchaseORM.repur_id == repur_id
            )
            s.exec(sql)
            
            # commit at same time
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(str(e))
            logging.info(f"deleted stock repurchase for {repur_id}")
            
    @classmethod
    def get(cls, repur_id: str) -> Tuple[StockRepurchase, str]:
        # return both issue id and journal id
        with Session(get_engine()) as s:

            # get stock_repur
            sql = select(StockRepurchaseORM).where(
                StockRepurchaseORM.repur_id == repur_id
            )
            try:
                stock_repur_orm = s.exec(sql).one() # get the stock_repur
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            stock_repur = cls.toStockRepur(
                stock_repur_orm=stock_repur_orm,
            )
            jrn_id = stock_repur_orm.journal_id
        return stock_repur, jrn_id
    
    @classmethod
    def update(cls, journal_id: str, stock_repur: StockRepurchase):
        with Session(get_engine()) as s:
            sql = select(StockRepurchaseORM).where(
                StockRepurchaseORM.repur_id == stock_repur.repur_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            stock_repur_orm = cls.fromStockRepur(
                journal_id=journal_id,
                stock_repur=stock_repur
            )
            # must update stock issue orm because journal id changed
            p.repurchase_dt = stock_repur_orm.repurchase_dt
            p.num_shares = stock_repur_orm.num_shares
            p.repur_price = stock_repur_orm.repur_price
            p.credit_acct_id = stock_repur_orm.credit_acct_id
            p.repur_amt = stock_repur_orm.stock_repur_orm
            p.journal_id = journal_id # update to new journal id
            
            try:
                s.add(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                s.refresh(p) # update p to instantly have new values
                
    @classmethod
    def list_issues(cls) -> list[StockRepurchase]:
        with Session(get_engine()) as s:

            # get stock_repur
            sql = select(StockRepurchaseORM)
            try:
                stock_repur_orms = s.exec(sql).all() # get the issues
            except NoResultFound as e:
                return []
            
            stock_repurs = [cls.toStockRepur(
                stock_repur_orm=stock_repur_orm,
            ) for stock_repur_orm in stock_repur_orms]
            
        return stock_repurs
    
class dividendDao:
    
    @classmethod
    def fromDiv(cls, journal_id: str, dividend: Dividend) -> DividendORM:
        return DividendORM(
            div_id=dividend.div_id,
            div_dt=dividend.div_dt,
            credit_acct_id=dividend.credit_acct_id,
            div_amt=dividend.div_amt,
            journal_id=journal_id
        )
        
    @classmethod
    def toDiv(cls, div_orm: DividendORM) -> Dividend:
        return Dividend(
            div_id=div_orm.div_id,
            div_dt=div_orm.div_dt,
            credit_acct_id=div_orm.credit_acct_id,
            div_amt=div_orm.div_amt,
        )
        
    @classmethod
    def add(cls, journal_id: str, dividend: Dividend):
        with Session(get_engine()) as s:
            div_orm = cls.fromDiv(journal_id, dividend)
        s.add(div_orm)
        try:
            s.commit()
        except IntegrityError as e:
            s.rollback()
            raise infer_integrity_error(e, during_creation=True)
        logging.info(f"Added {dividend} to dividend table")
        
    @classmethod
    def remove(cls, div_id: str):
        # remove dividend
        with Session(get_engine()) as s:
            sql = delete(DividendORM).where(
                DividendORM.div_id == div_id
            )
            s.exec(sql)
            
            # commit at same time
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(str(e))
            logging.info(f"deleted dividend for {div_id}")
            
    @classmethod
    def get(cls, div_id: str) -> Tuple[Dividend, str]:
        # return both issue id and journal id
        with Session(get_engine()) as s:

            # get dividend
            sql = select(DividendORM).where(
                DividendORM.div_id == div_id
            )
            try:
                div_orm = s.exec(sql).one() # get the dividend
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            dividend = cls.toDiv(
                div_orm=div_orm,
            )
            jrn_id = div_orm.journal_id
        return dividend, jrn_id
    
    @classmethod
    def update(cls, journal_id: str, dividend: Dividend):
        with Session(get_engine()) as s:
            sql = select(DividendORM).where(
                DividendORM.div_id == dividend.div_id,
            )
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            div_orm = cls.fromDiv(
                journal_id=journal_id,
                dividend=dividend
            )
            # must update stock issue orm because journal id changed
            p.div_dt = div_orm.div_dt
            p.credit_acct_id = div_orm.credit_acct_id
            p.div_amt = div_orm.div_orm
            p.journal_id = journal_id # update to new journal id
            
            try:
                s.add(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNotExistError(
                    details=str(e)
                )
            else:
                s.refresh(p) # update p to instantly have new values
                
    @classmethod
    def list_issues(cls) -> list[Dividend]:
        with Session(get_engine()) as s:

            # get dividend
            sql = select(DividendORM)
            try:
                div_orms = s.exec(sql).all() # get the issues
            except NoResultFound as e:
                return []
            
            divs = [cls.toDiv(
                div_orm=div_orm,
            ) for div_orm in div_orms]
            
        return divs