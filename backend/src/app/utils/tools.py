from functools import lru_cache
import math
from typing import Literal
import uuid
import re
import hvac
import os
import tomli
from pathlib import Path
from passlib.context import CryptContext


ENV = os.environ.get("ENV", "prod")
VAULT_MOUNT_POINT = "finlens"
VAULT_MOUNT_PATH = {
    'database' : f"{ENV}/database",
    'storage_server' : f"{ENV}/storage_server",
    'backup_server' : f"{ENV}/backup_server",
    'stateapi' : f"{ENV}/stateapi",
    'static_server': f"{ENV}/static_server",
    'auth': f"{ENV}/auth",
}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def id_generator(prefix: str, length: int = 8, existing_list: list[str] | None = None, 
                 only_alpha_numeric: bool = False) -> str:
    new_id = prefix + str(uuid.uuid4())[:length]
    if existing_list:
        if new_id in existing_list:
            new_id = id_generator(prefix, length, existing_list, only_alpha_numeric)
    if only_alpha_numeric:
        new_id = re.sub(r'[^a-zA-Z0-9]', '', new_id)
    return new_id


# def get_settings(user: User) -> dict:
#     from sqlmodel import Session
#     from src.app.service.misc import SettingService
#     from src.app.service.files import FileService
#     from src.app.dao.files import configDao, fileDao
#     from src.app.dao.connection import UserDaoAccess, get_engine, get_storage_fs
    
#     common_engine = get_engine('common')
#     user_engine=get_engine(user.user_id)
    
#     with Session(common_engine) as common_session, Session(user_engine) as user_session:
#         dao_access = UserDaoAccess(
#             common_engine=common_engine,
#             common_session=common_session,
#             user_engine=user_engine,
#             user_session=user_session,
#             file_fs=get_storage_fs('files'),
#             backup_fs=get_storage_fs('backup'),
#             user=user
#         )
#         file_dao=fileDao(dao_access=dao_access)
#         file_service = FileService(file_dao=file_dao)
#         config_dao = configDao(dao_access=dao_access)
        
#         setting_service = SettingService(
#             file_service=file_service,
#             config_dao=config_dao
#         )
    
#         settings = {
#             'preferences': {
#                 'base_cur': setting_service.get_base_currency(),
#                 'default_sales_tax_rate': setting_service.get_default_tax_rate(),
#                 'par_share_price': setting_service.get_par_share_price()
#             }
#         }
#     return settings

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


def get_vault_resp(mount_point: str, path: str) -> dict:
    with open((Path(__file__).resolve().parent.parent.parent.parent.parent / "secrets.toml").resolve(), mode="rb") as fp:
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
    auth = get_vault_resp(
        mount_point = VAULT_MOUNT_POINT,
        path = VAULT_MOUNT_PATH['auth'],
    )
    
    return {
        'database' : database,
        'storage_server' : storage_server,
        'backup_server' : backup_server,
        'stateapi' : stateapi,
        'static_server': static_server,
        'auth': auth
    }

def get_files_bucket() -> str:
    path_config = get_secret()['storage_server']['path']
    return path_config['bucket']

def get_backup_bucket() -> str:
    path_config = get_secret()['backup_server']['path']
    return path_config['bucket']