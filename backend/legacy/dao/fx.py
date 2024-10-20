import logging
from typing import Dict, List
from datetime import date
from dacite import from_dict, Config
from sqlmodel import Session, select
from legacy.dao.orm import FxORM
from legacy.dao.connection import engine
from legacy.model.enums import CurType

class fxDao:
    
    @classmethod
    def add(cls, currency: CurType, cur_dt: date, rate: float):
        with Session(engine) as s:
            fx = FxORM(
                currency=currency,
                cur_dt=cur_dt,
                rate=rate
            )
            s.add(fx)
            s.commit()
            logging.info(f"Added {fx} to FX table")
            
    @classmethod
    def adds(cls, currencies: List[CurType], cur_dt: date, rates: List[float]):
        with Session(engine) as s:
            for currency, rate in zip(currencies, rates):
                fx = FxORM(
                    currency=currency,
                    cur_dt=cur_dt,
                    rate=rate
                )
                s.add(fx)
            s.commit()
            logging.info(f"Added {currencies} to FX table @ {cur_dt}")
            
    @classmethod
    def remove(cls, currency: CurType, cur_dt: date):
        with Session(engine) as s:
            sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            p = s.exec(sql).one() # get the fx
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from FX table")
    
    @classmethod
    def update(cls, currency: CurType, cur_dt: date, rate: float):
        with Session(engine) as s:
            sql = select(FxORM).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            p = s.exec(sql).one() # get the fx
            
            # update
            p.rate = rate
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from FX table")
    
    @classmethod
    def get(cls, currency: CurType, cur_dt: date) -> float:
        with Session(engine) as s:
            sql = select(FxORM.rate).where(FxORM.currency == currency, FxORM.cur_dt == cur_dt)
            p = s.exec(sql).one() # get the fx
        return p
    
    @classmethod
    def get_fx_on_date(cls, cur_dt: date) -> List[CurType]:
        with Session(engine) as s:
            sql = select(FxORM.currency).where(FxORM.cur_dt == cur_dt)
            p = s.exec(sql).all() # get the fx
        return p
    
if __name__ == '__main__':
    fxDao.adds(
        currencies=[CurType.CAD, CurType.USD],
        cur_dt=date(2023, 10, 21),
        rates = [1.305, 1.0]
    )