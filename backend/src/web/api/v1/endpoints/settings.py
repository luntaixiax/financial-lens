from typing import Any, Tuple
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status, Body
from fastapi.responses import Response
from src.app.service.acct import AcctService
from src.app.model.exceptions import AlreadyExistError
from src.app.model.enums import CurType
from src.app.model.entity import Contact
from src.app.model.misc import FileWrapper
from src.app.service.settings import ConfigService
from src.app.service.settings import BackupService
from src.web.dependency.service import get_setting_service, get_acct_service, get_backup_service

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/is_setup")
def is_setup(
    setting_service: ConfigService = Depends(get_setting_service)
) -> bool:
    return setting_service.is_setup()

@router.post("/confirm_setup")
def confirm_setup(
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.confirm_setup()
    
@router.post("/init_coa")
def init_coa(
    setting_service: ConfigService = Depends(get_setting_service),
    acct_service: AcctService = Depends(get_acct_service)
):
    
    if not setting_service.is_setup():
        # create basic account structure *standard
        acct_service.init()
        setting_service.confirm_setup()
        
    else:
        raise AlreadyExistError(
            message='Already setup, cannot re-setup'
        )

@router.get("/get_base_currency")
def get_base_currency(
    setting_service: ConfigService = Depends(get_setting_service)
) -> CurType:
    return setting_service.get_base_currency()

@router.post("/set_base_currency")
def set_base_currency(
    base_currency: CurType,
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.set_base_currency(base_currency)

@router.get("/get_default_tax_rate")
def get_default_tax_rate(
    setting_service: ConfigService = Depends(get_setting_service)
) -> float:
    return setting_service.get_default_tax_rate()

@router.post("/set_default_tax_rate")
def set_default_tax_rate(
    default_tax_rate: float,
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.set_default_tax_rate(default_tax_rate)
    
@router.get("/get_par_share_price")
def get_par_share_price(
    setting_service: ConfigService = Depends(get_setting_service)
) -> float:
    return setting_service.get_par_share_price()

@router.post("/set_par_share_price")
def set_par_share_price(
    par_share_price: float,
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.set_par_share_price(par_share_price)

@router.post("/set_logo")
def set_logo(
    logo: UploadFile = File(...),
    setting_service: ConfigService = Depends(get_setting_service)
):
    try:
        content = logo.file.read().decode(encoding='latin-1')
    except Exception as e:
        raise e
    else:
        setting_service.set_logo(content)
    finally:
        logo.file.close()
        
@router.get("/get_logo")
def get_logo(
    setting_service: ConfigService = Depends(get_setting_service)
) -> FileWrapper:
    return setting_service.get_logo()

@router.get("/get_config")
def get_config(
    setting_service: ConfigService = Depends(get_setting_service)
) -> dict[str, Any]:
    return setting_service.get_config()

@router.get("/get_config_value")
def get_config_value(
    key: str,
    setting_service: ConfigService = Depends(get_setting_service)
) -> Any:
    return setting_service.get_config_value(key)

@router.post("/set_config_value")
def set_config_value(
    key: str,
    value: Any = Body(embed=False),
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.set_config_value(key, value)

@router.get("/get_company")
def get_company(
    setting_service: ConfigService = Depends(get_setting_service)
) -> Tuple[str, Contact]:
    return setting_service.get_company()

@router.post("/set_company")
def set_company(
    name: str, 
    contact: Contact,
    setting_service: ConfigService = Depends(get_setting_service)
):
    setting_service.set_company(name, contact)


@router.get("/list_backup_ids")
def list_backup_ids(
    backup_service: BackupService = Depends(get_backup_service)
) -> list[str]:
    return backup_service.list_backup_ids()

@router.post("/backup")
def backup(
    backup_id: str | None = None,
    backup_service: BackupService = Depends(get_backup_service)
) -> str:
    return backup_service.backup(backup_id)

@router.post("/restore")
def restore(
    backup_id: str,
    backup_service: BackupService = Depends(get_backup_service)
):
    backup_service.restore(backup_id)