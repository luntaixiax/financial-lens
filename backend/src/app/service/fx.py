
from datetime import date
from currency_converter import CurrencyConverter, ECB_URL
from src.app.model.exceptions import NotExistError
from src.app.utils.tools import get_base_cur
from src.app.dao.fx import fxDao
from src.app.model.enums import CurType


class FxService:
    GLOBAL_BASE_CUR = CurType.EUR
    FALL_BACK_CUR = {
        CurType.MOP : CurType.HKD
    }
    FALL_BACK_FX = {
        CurType.TWD: 33.5,
        CurType.CUP: 25.41
    }
    
    @classmethod
    def pull(cls, cur_dt: date, overwrite: bool = False):
        # fresh new run -- pull all at one time
        existing_fxs = fxDao.get_fx_on_date(cur_dt=cur_dt)
        if len(existing_fxs) == 0:
            rates = cls._pull(curs = CurType, cur_dt = cur_dt)
            fxDao.adds(
                currencies=[cur for cur in CurType],
                cur_dt=cur_dt,
                rates=rates
            )
            return
        
        if overwrite:
            rates = cls._pull(curs = CurType, cur_dt = cur_dt)
            for cur, rate in zip(CurType, rates):
                if cur in existing_fxs:
                    fxDao.update(
                        currency=cur,
                        cur_dt=cur_dt,
                        rate=rate
                    )
                else:
                    fxDao.add(
                        currency=cur,
                        cur_dt=cur_dt,
                        rate=rate
                    )
        else:
            # have at least some existing values
            missing_fxs = [cur for cur in CurType if cur not in existing_fxs]
            rates = cls._pull(curs = missing_fxs, cur_dt = cur_dt)
            for cur, rate in zip(missing_fxs, rates):
                fxDao.add(
                    currency=cur,
                    cur_dt=cur_dt,
                    rate=rate
                )   
            
    @classmethod
    def _pull(cls, curs: list[CurType], cur_dt: date) -> list[float]:
        # pull fx rates at given date
        c = CurrencyConverter(
            currency_file = ECB_URL,
            fallback_on_missing_rate = True,
            fallback_on_missing_rate_method = 'last_known',
            fallback_on_wrong_date = True, 
            ref_currency = cls.GLOBAL_BASE_CUR.name
        )
        # for 100 base currency, how much local currency is it
        rates = []
        for cur in curs:
            if cur.name not in c.currencies:
                cur_fallback = cls.FALL_BACK_CUR.get(cur)
                if cur_fallback is None:
                    rate = cls.FALL_BACK_FX.get(cur)
                    rates.append(rate)
                    continue
            else:
                cur_fallback = cur
            rate = c.convert(
                amount = 100, 
                currency = cls.GLOBAL_BASE_CUR.name, 
                new_currency = cur_fallback.name, 
                date = cur_dt
            )
            rate = round(rate, 4)
            rates.append(rate)
            
        return rates
        
    @classmethod
    def _get(cls, currency: CurType, cur_dt: date) -> float:
        try:
            rate = fxDao.get(currency=currency, cur_dt=cur_dt)
        except NotExistError as e:
            cls.pull(cur_dt=cur_dt, overwrite=False)
            return fxDao.get(currency=currency, cur_dt=cur_dt)
        else:
            return rate
        
    @classmethod
    def get(cls, currency: CurType, cur_dt: date) -> float:
        # convert using user defined base currency
        base_cur = get_base_cur()
        if base_cur == currency:
            return 1.0
        base_fx = cls._get(base_cur, cur_dt=cur_dt)
        target_fx = cls._get(currency, cur_dt=cur_dt)
        return base_fx / target_fx
    
    @classmethod
    def convert_to_base(cls, amount: float, src_currency: CurType, cur_dt: date) -> float:
        # convert from src_currency to base currency
        return cls.get(src_currency, cur_dt) * amount
    
    @classmethod
    def convert_from_base(cls, amount: float, tgt_currency: CurType, cur_dt: date) -> float:
        # convert from base currency to target currency
        return amount / cls.get(tgt_currency, cur_dt)
    
    @classmethod
    def convert(cls, amount: float, src_currency: CurType, tgt_currency: CurType, cur_dt: date) -> float:
        # convert from src_currency to base currency
        return amount * cls._get(tgt_currency, cur_dt=cur_dt) / cls._get(src_currency, cur_dt=cur_dt)