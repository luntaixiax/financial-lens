from datetime import date
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from src.app.model.exceptions import AlreadyExistError
from src.app.model.enums import CurType
from src.app.service.fx import FxService
from src.app.service.misc import GeoService, SettingService
from src.app.service.files import FileService
from src.app.model.misc import _CountryBrief, _StateBrief, FileWrapper

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

@router.get("/settings/get_default_tax_rate")
def get_default_tax_rate() -> float:
    return SettingService.get_default_tax_rate()

@router.post("/upload_file")
def upload_file(files: list[UploadFile] = File(...)) -> list[str]:
    
    file_ids = []
    for file in files:
        try:
            contents = file.file.read().decode(encoding='latin-1')
            f = FileWrapper(
                filename=file.filename,
                content=contents
            )
        except Exception as e:
            raise e
        else:
            try:
                FileService.add_file(f)
                file_id = f.file_id
            except AlreadyExistError as e:
                file_id = FileService.get_file_id_by_name(filename = file.filename)
        finally:
            file_ids.append(file_id)
            file.file.close()
            
    return file_ids

@router.delete("/delete_file/{file_id}")
def delete_file(file_id: str):
    
    FileService.delete_file(file_id)
    
@router.get("/get_file/{file_id}")
def get_file(file_id: str) -> FileWrapper:
    
    return FileService.get_file(file_id)