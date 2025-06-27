from typing import Any, Tuple
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status, Body
from fastapi.responses import Response
from src.app.model.enums import CurType
from src.app.model.entity import Contact
from src.app.model.misc import FileWrapper
from src.app.service.misc import SettingService


router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/is_setup")
def is_setup() -> bool:
    return SettingService.is_setup()

@router.post("/confirm_setup")
def confirm_setup():
    SettingService.confirm_setup()
    
@router.post("/init_coa")
def init_coa():
    from src.app.dao.connection import get_engine
    from src.app.service.acct import AcctService
    from src.app.service.misc import SettingService
    from src.app.model.exceptions import AlreadyExistError
    
    if not SettingService.is_setup():
        # create basic account structure *standard
        AcctService.init()
        SettingService.confirm_setup()
        
    else:
        raise AlreadyExistError(
            message='Already setup, cannot re-setup'
        )

@router.get("/get_base_currency")
def get_base_currency() -> CurType:
    return SettingService.get_base_currency()

@router.post("/set_base_currency")
def set_base_currency(base_currency: CurType):
    SettingService.set_base_currency(base_currency)

@router.get("/get_default_tax_rate")
def get_default_tax_rate() -> float:
    return SettingService.get_default_tax_rate()

@router.post("/set_default_tax_rate")
def set_default_tax_rate(default_tax_rate: float):
    SettingService.set_default_tax_rate(default_tax_rate)
    
@router.get("/get_par_share_price")
def get_par_share_price() -> float:
    return SettingService.get_par_share_price()

@router.post("/set_par_share_price")
def set_par_share_price(par_share_price: float):
    SettingService.set_par_share_price(par_share_price)

@router.post("/set_logo")
def set_logo(logo: UploadFile = File(...)):
    try:
        content = logo.file.read().decode(encoding='latin-1')
    except Exception as e:
        raise e
    else:
        SettingService.set_logo(content)
    finally:
        logo.file.close()
        
@router.get("/get_logo")
def get_logo() -> FileWrapper:
    return SettingService.get_logo()

@router.get("/get_config")
def get_config() -> dict[str, Any]:
    return SettingService.get_config()

@router.get("/get_config_value")
def get_config_value(key: str) -> Any:
    return SettingService.get_config_value(key)

@router.post("/set_config_value")
def set_config_value(key: str, value: Any = Body(embed=False)):
    SettingService.set_config_value(key, value)

@router.get("/get_company")
def get_company() -> Tuple[str, Contact]:
    return SettingService.get_company()

@router.post("/set_company")
def set_company(name: str, contact: Contact):
    SettingService.set_company(name, contact)
