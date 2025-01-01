from fastapi import APIRouter
from pydantic import BaseModel
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