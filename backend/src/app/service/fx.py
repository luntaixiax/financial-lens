from datetime import date
from currency_converter import CurrencyConverter, ECB_URL
from src.app.service.settings import ConfigService
from src.app.model.exceptions import NotExistError
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
    
    def __init__(self, fx_dao: fxDao, setting_service: ConfigService):
        self.fx_dao = fx_dao
        self.setting_service = setting_service
            
    def pull(self, cur_dt: date, overwrite: bool = False):
        # fresh new run -- pull all at one time
        existing_fxs = self.fx_dao.get_fx_on_date(cur_dt=cur_dt)
        if len(existing_fxs) == 0:
            rates = self._pull(curs = CurType, cur_dt = cur_dt) # type: ignore
            self.fx_dao.adds(
                currencies=[cur for cur in CurType],
                cur_dt=cur_dt,
                rates=rates
            )
            return
        
        if overwrite:
            rates = self._pull(curs = CurType, cur_dt = cur_dt) # type: ignore
            for cur, rate in zip(CurType, rates):
                if cur in existing_fxs:
                    self.fx_dao.update(
                        currency=cur,
                        cur_dt=cur_dt,
                        rate=rate
                    )
                else:
                    self.fx_dao.add(
                        currency=cur,
                        cur_dt=cur_dt,
                        rate=rate
                    )
        else:
            # have at least some existing values
            missing_fxs = [cur for cur in CurType if cur not in existing_fxs]
            rates = self._pull(curs = missing_fxs, cur_dt = cur_dt)
            for cur, rate in zip(missing_fxs, rates):
                self.fx_dao.add(
                    currency=cur,
                    cur_dt=cur_dt,
                    rate=rate
                )   
            
    def _pull(self, curs: list[CurType], cur_dt: date) -> list[float]:
        # pull fx rates at given date
        c = CurrencyConverter(
            currency_file = ECB_URL,
            fallback_on_missing_rate = True,
            fallback_on_missing_rate_method = 'last_known',
            fallback_on_wrong_date = True, 
            ref_currency = self.GLOBAL_BASE_CUR.name
        )
        # for 100 base currency, how much local currency is it
        rates = []
        for cur in curs:
            if cur.name not in c.currencies: # type: ignore
                cur_fallback = self.FALL_BACK_CUR.get(cur)
                if cur_fallback is None:
                    rate = self.FALL_BACK_FX.get(cur)
                    rates.append(rate)
                    continue
            else:
                cur_fallback = cur
            rate = c.convert(
                amount = 100, 
                currency = self.GLOBAL_BASE_CUR.name, 
                new_currency = cur_fallback.name, 
                date = cur_dt
            )
            rate = round(rate, 4)
            rates.append(rate)
            
        return rates
        
    def _get(self, currency: CurType, cur_dt: date) -> float:
        try:
            rate = self.fx_dao.get(currency=currency, cur_dt=cur_dt)
        except NotExistError as e:
            self.pull(cur_dt=cur_dt, overwrite=False)
            return self.fx_dao.get(currency=currency, cur_dt=cur_dt)
        else:
            return rate
        
    def get(self, currency: CurType, cur_dt: date) -> float:
        # convert using user defined base currency
        base_cur = self.setting_service.get_base_currency()
        if base_cur == currency:
            return 1.0
        base_fx = self._get(base_cur, cur_dt=cur_dt)
        target_fx = self._get(currency, cur_dt=cur_dt)
        return base_fx / target_fx
    
    def convert_to_base(self, amount: float, src_currency: CurType, cur_dt: date) -> float:
        # convert from src_currency to base currency
        return self.get(src_currency, cur_dt) * amount
    
    def convert_from_base(self, amount: float, tgt_currency: CurType, cur_dt: date) -> float:
        # convert from base currency to target currency
        return amount / self.get(tgt_currency, cur_dt)
    
    def convert(self, amount: float, src_currency: CurType, tgt_currency: CurType, cur_dt: date) -> float:
        # convert from src_currency to base currency
        return amount * self._get(tgt_currency, cur_dt=cur_dt) / self._get(src_currency, cur_dt=cur_dt)