import logging
from typing import Dict, List
from datetime import date
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.dao.orm import FxORM
from src.app.dao.connection import get_engine
from src.app.model.enums import CurType
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError


class fxDao:
    
    @classmethod
    def add(cls, currency: CurType, cur_dt: date, rate: float):
        with Session(get_engine()) as s:
            fx = FxORM(
                currency=currency,
                cur_dt=cur_dt,
                rate=rate
            )
            s.add(fx)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {fx} to FX table")
            
    @classmethod
    def adds(cls, currencies: List[CurType], cur_dt: date, rates: List[float]):
        with Session(get_engine()) as s:
            for currency, rate in zip(currencies, rates):
                fx = FxORM(
                    currency=currency,
                    cur_dt=cur_dt,
                    rate=rate
                )
                s.add(fx)
            
            # commit in one load
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {currencies} to FX table @ {cur_dt}")
            
    @classmethod
    def remove(cls, currency: CurType, cur_dt: date):
        with Session(get_engine()) as s:
            sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(details=str(e))
            
        logging.info(f"Removed {p} from FX table")
    
    @classmethod
    def update(cls, currency: CurType, cur_dt: date, rate: float):
        with Session(get_engine()) as s:
            sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
            
            # update
            p.rate = rate
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from FX table")
    
    @classmethod
    def get(cls, currency: CurType, cur_dt: date) -> float:
        with Session(get_engine()) as s:
            sql = select(FxORM.rate).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            try:
                p = s.exec(sql).one() # get the fx
            except NoResultFound as e:
                raise NotExistError(f"FX not exist, currency = {currency}, cur_dt = {cur_dt}")
        return p
    
    @classmethod
    def get_fx_on_date(cls, cur_dt: date) -> List[CurType]:
        with Session(get_engine()) as s:
            sql = select(FxORM.currency).where(FxORM.cur_dt == cur_dt)
            try:
                p = s.exec(sql).all() # get the fx
            except NoResultFound as e:
                raise NotExistError(f"FX (all currency) not exist, cur_dt = {cur_dt}")
            
        return p
    
if __name__ == '__main__':
    fxDao.adds(
        currencies=[CurType.CAD, CurType.USD],
        cur_dt=date(2023, 10, 21),
        rates = [1.305, 1.0]
    )