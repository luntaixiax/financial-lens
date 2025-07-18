from datetime import date
from fastapi import APIRouter, Depends, File, UploadFile
from src.app.model.exceptions import AlreadyExistError
from src.app.model.enums import CurType
from src.app.service.fx import FxService
from src.app.service.misc import GeoService
from src.app.service.files import FileService
from src.app.model.misc import _CountryBrief, _StateBrief, FileWrapper
from src.web.dependency.service import get_fx_service, get_file_service

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

@router.get("/fx/get_rate")
def get_fx_rate(
    src_currency: CurType, 
    tgt_currency: CurType, 
    cur_dt: date,
    fx_service: FxService = Depends(get_fx_service)
) -> float:
    return fx_service.convert(1.0, src_currency, tgt_currency, cur_dt)

@router.get("/fx/convert_to_base")
def convert_to_base(
    amount: float, 
    src_currency: CurType, 
    cur_dt: date,
    fx_service: FxService = Depends(get_fx_service)
) -> float:
    return fx_service.convert_to_base(amount, src_currency, cur_dt)

@router.get("/fx/convert_from_base")
def convert_from_base(
    amount: float, 
    tgt_currency: CurType, 
    cur_dt: date,
    fx_service: FxService = Depends(get_fx_service)
) -> float:
    return fx_service.convert_from_base(amount, tgt_currency, cur_dt)


@router.post("/register_file")
def register_file(
    filename: str,
    file_service: FileService = Depends(get_file_service)
) -> str:
    return file_service.register_file(filename)
    
@router.post("/register_files")
def register_files(
    filenames: list[str],
    file_service: FileService = Depends(get_file_service)
) -> dict[str, str]:
    return file_service.register_files(filenames)

@router.post("/upload_file")
def upload_file(
    files: list[UploadFile] = File(...),
    file_service: FileService = Depends(get_file_service)
) -> list[str]:
    
    file_ids = []
    for file in files:
        try:
            contents = file.file.read().decode(encoding='latin-1')
            f = FileWrapper(
                filename=file.filename or 'noname',
                content=contents
            )
        except Exception as e:
            raise e
        else:
            try:
                file_service.add_file(f)
                file_id = f.file_id
            except AlreadyExistError as e:
                file_id = file_service.get_file_id_by_name(
                    filename = file.filename or 'noname'
                )
        finally:
            file_ids.append(file_id)
            file.file.close()
            
    return file_ids

@router.delete("/delete_file/{file_id}")
def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    file_service.delete_file(file_id)
    
@router.get("/get_file/{file_id}")
def get_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
) -> FileWrapper:
    return file_service.get_file(file_id)