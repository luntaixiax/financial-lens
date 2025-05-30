from functools import lru_cache
from typing import Literal
import uuid
import hvac
import os
import tomli
import yaml
from pathlib import Path
from src.app.model.enums import CurType

ENV = os.environ.get("ENV", "prod")
VAULT_MOUNT_POINT = "finlens"
VAULT_MOUNT_PATH = {
    'database' : f"{ENV}/database",
    'storage_server' : f"{ENV}/storage_server",
    'backup_server' : f"{ENV}/backup_server",
    'stateapi' : f"{ENV}/stateapi",
}

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


def get_base_cur() -> CurType:
    settings = get_settings()
    return CurType[settings['preferences']['base_cur']]

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
    
    return {
        'database' : database,
        'storage_server' : storage_server,
        'backup_server' : backup_server,
        'stateapi' : stateapi,
    }

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
    
def get_config_root(type_: Literal['files', 'backup'] = 'files') -> str:
    settings = get_settings().get(type_, {})
    
    if settings.get('fs', 'obj') == 'obj':
        # object file system
        bucket = settings.get('bucket')
        file_root = 'config'
        return (Path(bucket) / file_root).as_posix()
    else:
        # file system
        file_root = 'config'
        return  (Path(settings.get('root')) / file_root).as_posix()