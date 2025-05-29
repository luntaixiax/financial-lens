from functools import lru_cache
import requests
from src.app.model.exceptions import NotExistError
from src.app.service.files import FileService
from src.app.utils.tools import get_default_tax_rate, get_secret
from src.app.model.misc import _CountryBrief, _StateBrief, FileWrapper


class GeoService:
    
    @classmethod
    def req(cls, path: str) -> dict:
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

class SettingService:
    LOGO_FILE_ID = 'settings-logo'
    
    @classmethod
    def get_default_tax_rate(cls) -> float:
        return get_default_tax_rate()
    
    @classmethod
    def set_logo(cls, content: str):
        logo = FileWrapper(
            file_id=cls.LOGO_FILE_ID,
            filename='SETTINGS_LOGO.PNG', 
            content=content
        )
        try:
            FileService.get_file(cls.LOGO_FILE_ID)
        except NotExistError:
            FileService.add_file(logo)
        else:
            # if exist, remove current one and replace with new one
            FileService.delete_file(cls.LOGO_FILE_ID)
            FileService.add_file(logo)
        
    @classmethod
    def get_logo(cls) -> FileWrapper:
        try:
            logo = FileService.get_file(cls.LOGO_FILE_ID)
        except NotExistError as e:
            raise NotExistError(message="Logo not set yet! " + e.message, details=e.details)
        return logo