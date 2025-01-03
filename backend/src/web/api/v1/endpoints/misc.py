from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel
from src.app.model.enums import CurType
from src.app.service.fx import FxService
from src.app.service.misc import GeoService
from src.app.model.misc import _CountryBrief, _StateBrief

router = APIRouter(prefix="/misc", tags=["misc"])

@router.get("/geo/countries/list")
def list_countries() -> list[_CountryBrief]:
    return GeoService.list_countries()

@router.get("/geo/countries/{country_iso2}/state/list")
def list_states(country_iso2: str) -> list[_StateBrief]:
    return GeoService.list_states(country_iso2)


@router.get("/geo/countries/{country_iso2}/state/{state_iso2}/city/list")
def list_cities(country_iso2: str, state_iso2: str) -> list[str]:
    return GeoService.list_cities(country_iso2, state_iso2)

@router.get("/fx/get_base_cur")
def get_base_currency() -> CurType:
    return FxService.BASE_CUR

@router.get("/fx/get_rate")
def get_fx_rate(src_currency: CurType, tgt_currency: CurType, cur_dt: date) -> float:
    return FxService.convert(1.0, src_currency, tgt_currency, cur_dt)

@router.get("/fx/convert_to_base")
def convert_to_base(amount: float, src_currency: CurType, cur_dt: date) -> float:
    return FxService.convert_to_base(amount, src_currency, cur_dt)

@router.get("/fx/convert_from_base")
def convert_from_base(amount: float, tgt_currency: CurType, cur_dt: date) -> float:
    return FxService.convert_from_base(amount, tgt_currency, cur_dt)