from typing import Any, Tuple
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status, Body
from fastapi.responses import Response
from src.app.model.entity import Contact
from src.app.model.misc import FileWrapper
from src.app.service.misc import SettingService


router = APIRouter(prefix="/settings", tags=["settings"])

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
