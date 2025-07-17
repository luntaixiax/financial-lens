
from datetime import date
from typing import Tuple
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.exceptions import FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.orm import DividendORM, StockIssueORM, StockRepurchaseORM
from src.app.model.shares import Dividend, StockIssue, StockRepurchase
from src.app.dao.orm import infer_integrity_error
from src.app.dao.connection import UserDaoAccess

class stockIssueDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
        
    def fromStockIssue(self, journal_id: str, stock_issue: StockIssue) -> StockIssueORM:
        return StockIssueORM(
            issue_id=stock_issue.issue_id,
            issue_dt=stock_issue.issue_dt,
            is_reissue=stock_issue.is_reissue,
            num_shares=stock_issue.num_shares,
            issue_price=stock_issue.issue_price,
            reissue_repur_id=stock_issue.reissue_repur_id,
            debit_acct_id=stock_issue.debit_acct_id,
            issue_amt=stock_issue.issue_amt,
            note=stock_issue.note,
            journal_id=journal_id,
        )
        
    def toStockIssue(self, stock_issue_orm: StockIssueORM) -> StockIssue:
        return StockIssue(
            issue_id=stock_issue_orm.issue_id,
            issue_dt=stock_issue_orm.issue_dt,
            is_reissue=stock_issue_orm.is_reissue,
            num_shares=stock_issue_orm.num_shares,
            issue_price=stock_issue_orm.issue_price,
            reissue_repur_id=stock_issue_orm.reissue_repur_id,
            debit_acct_id=stock_issue_orm.debit_acct_id,
            issue_amt=stock_issue_orm.issue_amt,
            note=stock_issue_orm.note
        )
        
    def add(self, journal_id: str, stock_issue: StockIssue):
        stock_issue_orm = self.fromStockIssue(journal_id, stock_issue)
        self.dao_access.user_session.add(stock_issue_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    def remove(self, issue_id: str):
        # remove stock_issue
        sql = delete(StockIssueORM).where(
            StockIssueORM.issue_id == issue_id
        )
        
        # commit at same time
        try:
            self.dao_access.user_session.exec(sql) # type: ignore
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNoDeleteUpdateError(str(e))
            
    def get(self, issue_id: str) -> Tuple[StockIssue, str]:
        # return both issue id and journal id
        # get stock_issue
        sql = select(StockIssueORM).where(
            StockIssueORM.issue_id == issue_id
        )
        try:
            stock_issue_orm = self.dao_access.user_session.exec(sql).one() # get the stock_issue
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        stock_issue = self.toStockIssue(
            stock_issue_orm=stock_issue_orm,
        )
        jrn_id = stock_issue_orm.journal_id
        return stock_issue, jrn_id
    
    def update(self, journal_id: str, stock_issue: StockIssue):
        sql = select(StockIssueORM).where(
            StockIssueORM.issue_id == stock_issue.issue_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        stock_issue_orm = self.fromStockIssue(
            journal_id=journal_id,
            stock_issue=stock_issue
        )
        # must update stock issue orm because journal id changed
        p.issue_dt = stock_issue_orm.issue_dt
        p.is_reissue = stock_issue_orm.is_reissue
        p.num_shares = stock_issue_orm.num_shares
        p.issue_price = stock_issue_orm.issue_price
        p.reissue_repur_id = stock_issue_orm.reissue_repur_id
        p.debit_acct_id = stock_issue_orm.debit_acct_id
        p.issue_amt = stock_issue_orm.issue_amt
        p.note = stock_issue_orm.note
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.dao_access.user_session.add(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.dao_access.user_session.refresh(p) # update p to instantly have new values
                
    def list_issues(self, is_reissue: bool = False) -> list[StockIssue]:
        # get stock_issue
        sql = select(StockIssueORM).where(StockIssueORM.is_reissue == is_reissue)
        try:
            stock_issue_orms = self.dao_access.user_session.exec(sql).all() # get the issues
        except NoResultFound as e:
            return []
        
        stock_issues = [self.toStockIssue(
            stock_issue_orm=stock_issue_orm,
        ) for stock_issue_orm in stock_issue_orms]
            
        return stock_issues
    
    def list_reissue_from_repur(self, repur_id: str) -> list[StockIssue]:
        # get stock_issue
        sql = select(StockIssueORM).where(
            StockIssueORM.is_reissue == True,
            StockIssueORM.reissue_repur_id == repur_id
        )
        try:
            stock_issue_orms = self.dao_access.user_session.exec(sql).all() # get the issues   
        except NoResultFound as e:
            return []
        
        stock_issues = [self.toStockIssue(
            stock_issue_orm=stock_issue_orm,
        ) for stock_issue_orm in stock_issue_orms]
            
        return stock_issues
    
    def get_total_reissue_from_repur(self, repur_id: str, rep_dt: date, exclu_issue_id: str | None = None) -> float:
        # need to exclude self issue id in counting
        # get stock_issue
        sql = select(
            f.sum(StockIssueORM.num_shares).label('total_reissue')
        ).where(
            StockIssueORM.is_reissue == True,
            StockIssueORM.reissue_repur_id == repur_id,
            StockIssueORM.issue_dt <= rep_dt,
            StockIssueORM.issue_id != exclu_issue_id
        )
        total_reissue = self.dao_access.user_session.exec(sql).one() # get the issues
            
        return total_reissue or 0 # type: ignore
    
    
class stockRepurchaseDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
        
    def fromStockRepur(self, journal_id: str, stock_repur: StockRepurchase) -> StockRepurchaseORM:
        return StockRepurchaseORM(
            repur_id=stock_repur.repur_id,
            repur_dt=stock_repur.repur_dt,
            num_shares=stock_repur.num_shares,
            repur_price=stock_repur.repur_price,
            credit_acct_id=stock_repur.credit_acct_id,
            repur_amt=stock_repur.repur_amt,
            note=stock_repur.note,
            journal_id=journal_id
        )
        
    def toStockRepur(self, stock_repur_orm: StockRepurchaseORM) -> StockRepurchase:
        return StockRepurchase(
            repur_id=stock_repur_orm.repur_id,
            repur_dt=stock_repur_orm.repur_dt,
            num_shares=stock_repur_orm.num_shares,
            repur_price=stock_repur_orm.repur_price,
            credit_acct_id=stock_repur_orm.credit_acct_id,
            repur_amt=stock_repur_orm.repur_amt,
            note=stock_repur_orm.note
        )
        
    def add(self, journal_id: str, stock_repur: StockRepurchase):
        stock_repur_orm = self.fromStockRepur(journal_id, stock_repur)
        self.dao_access.user_session.add(stock_repur_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    def remove(self, repur_id: str):
        # remove stock_repur
        sql = delete(StockRepurchaseORM).where(
            StockRepurchaseORM.repur_id == repur_id
        )
        
        # commit at same time
        try:
            self.dao_access.user_session.exec(sql) # type: ignore
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNoDeleteUpdateError(str(e))
            
    def get(self, repur_id: str) -> Tuple[StockRepurchase, str]:
        # return both issue id and journal id
        # get stock_repur
        sql = select(StockRepurchaseORM).where(
            StockRepurchaseORM.repur_id == repur_id
        )
        try:
            stock_repur_orm = self.dao_access.user_session.exec(sql).one() # get the stock_repur
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        stock_repur = self.toStockRepur(
            stock_repur_orm=stock_repur_orm,
        )
        jrn_id = stock_repur_orm.journal_id
        return stock_repur, jrn_id
    
    def update(self, journal_id: str, stock_repur: StockRepurchase):
        sql = select(StockRepurchaseORM).where(
            StockRepurchaseORM.repur_id == stock_repur.repur_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        stock_repur_orm = self.fromStockRepur(
            journal_id=journal_id,
            stock_repur=stock_repur
        )
        # must update stock issue orm because journal id changed
        p.repur_dt = stock_repur_orm.repur_dt
        p.num_shares = stock_repur_orm.num_shares
        p.repur_price = stock_repur_orm.repur_price
        p.credit_acct_id = stock_repur_orm.credit_acct_id
        p.repur_amt = stock_repur_orm.repur_amt
        p.note = stock_repur_orm.note
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.dao_access.user_session.add(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.dao_access.user_session.refresh(p) # update p to instantly have new values
                
    def list_repurs(self) -> list[StockRepurchase]:
        # get stock_repur
        sql = select(StockRepurchaseORM)
        try:
            stock_repur_orms = self.dao_access.user_session.exec(sql).all() # get the repurchases
        except NoResultFound as e:
            return []
        
        stock_repurs = [self.toStockRepur(
            stock_repur_orm=stock_repur_orm,
        ) for stock_repur_orm in stock_repur_orms]
            
        return stock_repurs
    
class dividendDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
        
    def fromDiv(self, journal_id: str, dividend: Dividend) -> DividendORM:
        return DividendORM(
            div_id=dividend.div_id,
            div_dt=dividend.div_dt,
            credit_acct_id=dividend.credit_acct_id,
            div_amt=dividend.div_amt,
            note=dividend.note,
            journal_id=journal_id
        )
        
    def toDiv(self, div_orm: DividendORM) -> Dividend:
        return Dividend(
            div_id=div_orm.div_id,
            div_dt=div_orm.div_dt,
            credit_acct_id=div_orm.credit_acct_id,
            div_amt=div_orm.div_amt,
            note=div_orm.note
        )
        
    def add(self, journal_id: str, dividend: Dividend):
        div_orm = self.fromDiv(journal_id, dividend)
        self.dao_access.user_session.add(div_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
        
    def remove(self, div_id: str):
        # remove dividend
        sql = delete(DividendORM).where(
            DividendORM.div_id == div_id
        )
        
        # commit at same time
        try:
            self.dao_access.user_session.exec(sql) # type: ignore
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNoDeleteUpdateError(str(e))
            
    def get(self, div_id: str) -> Tuple[Dividend, str]:
        # return both issue id and journal id
        # get dividend
        sql = select(DividendORM).where(
            DividendORM.div_id == div_id
        )
        try:
            div_orm = self.dao_access.user_session.exec(sql).one() # get the dividend
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        dividend = self.toDiv(
            div_orm=div_orm,
        )
        jrn_id = div_orm.journal_id
        return dividend, jrn_id
    
    def update(self, journal_id: str, dividend: Dividend):
        sql = select(DividendORM).where(
            DividendORM.div_id == dividend.div_id,
        )
        try:
            p = self.dao_access.user_session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        # update
        div_orm = self.fromDiv(
            journal_id=journal_id,
            dividend=dividend
        )
        # must update stock issue orm because journal id changed
        p.div_dt = div_orm.div_dt
        p.credit_acct_id = div_orm.credit_acct_id
        p.div_amt = div_orm.div_amt
        p.note = div_orm.note
        p.journal_id = journal_id # update to new journal id
        
        try:
            self.dao_access.user_session.add(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNotExistError(
                details=str(e)
            )
        else:
            self.dao_access.user_session.refresh(p) # update p to instantly have new values
                
    def list_divs(self) -> list[Dividend]:
        # get dividend
        sql = select(DividendORM)
        try:
            div_orms = self.dao_access.user_session.exec(sql).all() # get the dividends
        except NoResultFound as e:
            return []
        
        divs = [self.toDiv(
            div_orm=div_orm,
        ) for div_orm in div_orms]
            
        return divs