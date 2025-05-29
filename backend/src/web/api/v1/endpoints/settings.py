from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import Response
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