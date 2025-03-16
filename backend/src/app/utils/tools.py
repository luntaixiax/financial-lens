from functools import lru_cache
from typing import Literal
import uuid
import tomli
import yaml
from pathlib import Path
from src.app.model.enums import CurType

def id_generator(prefix: str, length: int = 8, existing_list: list = None) -> str:
    new_id = prefix + str(uuid.uuid4())[:length]
    if existing_list:
        if new_id in existing_list:
            new_id = id_generator(prefix, length, existing_list)
    return new_id

@lru_cache()
def get_settings() -> dict:
    with open(Path.cwd() / 'configs.yaml') as obj:
        return yaml.safe_load(obj)
    
def get_abs_img_path(img_name: str, sector: str) -> str:
    settings = get_settings()
    img_root = settings.get('paths').get('static').get('images')
    return str(Path(img_root) / sector / img_name)

def get_base_cur() -> CurType:
    settings = get_settings()
    return CurType[settings['preferences']['base_cur']]

def get_default_tax_rate() -> float:
    settings = get_settings()
    return settings['preferences']['default_sales_tax_rate']

def get_company() -> dict:
    settings = get_settings()
    return settings['company_settings']

@lru_cache()
def get_secret() -> dict:
    with open(Path.cwd().parent / "secrets.toml", mode="rb") as fp:
        config = tomli.load(fp)
    return config

def get_file_root(type_: Literal['files', 'backup'] = 'files') -> str:
    settings = get_settings().get(type_, {})
    
    if settings.get('fs', 'obj') == 'obj':
        # object file system
        bucket = settings.get('bucket')
        file_root = settings.get('file_root')
        return (Path(bucket) / file_root).as_posix()
    else:
        # file system
        file_root = settings.get('file_root')
        return  (Path(settings.get('root')) / file_root).as_posix()