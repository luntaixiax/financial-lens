import logging
from typing import Dict, List
from datetime import date
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.dao.orm import FxORM
from src.app.model.enums import CurType
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError


class fxDao:
    
    def __init__(self, session: Session):
        self.session = session
        
    def add(self, currency: CurType, cur_dt: date, rate: float):
        fx = FxORM(
            currency=currency,
            cur_dt=cur_dt,
            rate=rate
        )
        self.session.add(fx)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistError(details=str(e))
            

    def adds(self, currencies: List[CurType], cur_dt: date, rates: List[float]):
        for currency, rate in zip(currencies, rates):
            fx = FxORM(
                currency=currency,
                cur_dt=cur_dt,
                rate=rate
            )
            self.session.add(fx)
        
        # commit in one load
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistError(details=str(e))
            
    def remove(self, currency: CurType, cur_dt: date):
        sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
        
        try:
            self.session.delete(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
            
    
    def update(self, currency: CurType, cur_dt: date, rate: float):
        sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
        
        # update
        p.rate = rate
        
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p) # update p to instantly have new values
        

    def get(self, currency: CurType, cur_dt: date) -> float:
        sql = select(FxORM.rate).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
        try:
            p = self.session.exec(sql).one() # get the fx
        except NoResultFound as e:
            raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
        return p
    
    def get_fx_on_date(self, cur_dt: date) -> List[CurType]:

        sql = select(FxORM.currency).where(FxORM.cur_dt == cur_dt)
        try:
            p = self.session.exec(sql).all() # get the fx
        except NoResultFound as e:
            raise NotExistError(f"FX (all currency) not exist, cur_dt = {cur_dt}")
            
        return p