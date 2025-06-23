from functools import lru_cache
import math
from typing import Literal
import uuid
import hvac
import os
import tomli
from pathlib import Path
from src.app.model.enums import CurType

ENV = os.environ.get("ENV", "prod")
VAULT_MOUNT_POINT = "finlens"
VAULT_MOUNT_PATH = {
    'database' : f"{ENV}/database",
    'storage_server' : f"{ENV}/storage_server",
    'backup_server' : f"{ENV}/backup_server",
    'stateapi' : f"{ENV}/stateapi",
    'static_server': f"{ENV}/static_server",
}

def id_generator(prefix: str, length: int = 8, existing_list: list = None) -> str:
    new_id = prefix + str(uuid.uuid4())[:length]
    if existing_list:
        if new_id in existing_list:
            new_id = id_generator(prefix, length, existing_list)
    return new_id


def get_settings() -> dict:
    from src.app.service.misc import SettingService
    
    return {
        'preferences': {
            'base_cur': SettingService.get_base_currency(),
            'default_sales_tax_rate': SettingService.get_default_tax_rate()
        }
    }

@lru_cache()
def get_amount_precision() -> int:
    return 2 # dollar amount precision will be maxed at this decimal place

def finround(x: float) -> float:
    # banker rounding: <= 4 round down, >= 6 round up. =5 half up half down
    return round(x, get_amount_precision())

def taxround(x: float) -> float:
    # tax rounding: <= 4 round down and >= 5 round up
    precision = get_amount_precision()
    expoN = x * 10 ** precision
    if round(abs(expoN) - abs(math.floor(expoN)), 9) < 0.5: # must round here to prevent error
        return math.floor(expoN) / 10 ** precision
    return math.ceil(expoN) / 10 ** precision

@lru_cache()
def get_base_cur() -> CurType:
    settings = get_settings()
    return settings['preferences']['base_cur']

def get_default_tax_rate() -> float:
    settings = get_settings()
    return settings['preferences']['default_sales_tax_rate']


def get_vault_resp(mount_point: str, path: str) -> dict:
    with open(Path.cwd().parent / "secrets.toml", mode="rb") as fp:
        config = tomli.load(fp)
        
    vault_config = config['vault']
    
    client = hvac.Client(
        url = f"{vault_config['endpoint']}:{vault_config['port']}",
        token = vault_config['token']
    )
    if client.is_authenticated():
        response = client.secrets.kv.read_secret_version(
            mount_point=mount_point,
            path=path,
            raise_on_deleted_version=True
        )['data']['data']
        return response
    else:
        raise PermissionError("Vault Permission Error")

@lru_cache()
def get_secret() -> dict:
    database = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['database'],
    )
    storage_server = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['storage_server'],
    )
    backup_server = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['backup_server'],
    )
    stateapi = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['stateapi'],
    )
    static_server = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['static_server']
    )
    
    return {
        'database' : database,
        'storage_server' : storage_server,
        'backup_server' : backup_server,
        'stateapi' : stateapi,
        'static_server': static_server
    }

def get_file_root(type_: Literal['files', 'backup'] = 'files') -> str:
    if type_ == 'files':
        path_config = get_secret()['storage_server']['path']
    else:
        path_config = get_secret()['backup_server']['path']
    
    return (Path(path_config['bucket']) / path_config['file_root']).as_posix()
    
def get_config_root(type_: Literal['files', 'backup'] = 'files') -> str:
    if type_ == 'files':
        path_config = get_secret()['storage_server']['path']
    else:
        path_config = get_secret()['backup_server']['path']
        
    return (Path(path_config['bucket']) / 'config').as_posix()