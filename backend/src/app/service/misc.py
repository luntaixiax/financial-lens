from functools import lru_cache
import requests
from src.app.utils.tools import get_secret
from src.app.model.misc import _CountryBrief, _StateBrief


class GeoService:
    
    @classmethod
    def req(cls, path: str) -> dict: # type: ignore
        secret = get_secret()['stateapi']
        headers = {
            'X-CSCAPI-KEY': secret['apikey']
        }
        url = f"{secret['endpoint']}/v1/{path}"
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            return response.json()
    
    @classmethod
    @lru_cache(maxsize=32)
    def list_countries(cls) -> list[_CountryBrief]:
        results = cls.req('countries')
        return [
            _CountryBrief(country=r['name'], iso2=r['iso2'])
            for r in results
        ]
    
    @classmethod
    @lru_cache(maxsize=32)
    def list_states(cls, country_iso2: str) -> list[_StateBrief]:
        results = cls.req(f'countries/{country_iso2}/states')
        return [
            _StateBrief(state=r['name'], iso2=r['iso2'])
            for r in results
        ]
    
    @classmethod
    @lru_cache(maxsize=32)
    def list_cities(cls, country_iso2: str, state_iso2: str) -> list[str]:
        results = cls.req(f'countries/{country_iso2}/states/{state_iso2}/cities')
        return [
            r['name']
            for r in results
        ]