from functools import lru_cache
from datetime import datetime, timezone, timedelta
import math
from typing import Any, Hashable, Literal
from collections import OrderedDict
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

class LocalCacheKVStore:
    
    def __init__(self, capacity: int, ttl: int = 60 * 60 * 1):
        self._capacity = capacity
        self._cache = {} # space -> key -> value
        self._ttl = ttl

    def put(self, space: str, key: Hashable, value: Any) -> None:
        expire_time = datetime.now(timezone.utc) + timedelta(seconds=self._ttl)
        
        if space in self._cache:
            if key in self._cache[space]:
                self._cache[space].pop(key)
            elif len(self._cache[space]) >= self._capacity:
                self._cache[space].popitem(last=False) # Remove the least recently used (first item)
            # set value
            self._cache[space][key] = {
                'value': value,
                'expire_time': expire_time
            }
        else:
            # set value
            self._cache[space] = OrderedDict({key: {
                'value': value,
                'expire_time': expire_time
            }})
    
    def get(self, space: str, key: Hashable) -> Any:
        if space in self._cache:
            if key in self._cache[space]:
                if self._cache[space][key]['expire_time'] < datetime.now(timezone.utc):
                    self._cache[space].pop(key)
                    raise TimeoutError(f"Key {key} expired in space {space}")
                else:
                    return self._cache[space][key]['value']
            else:
                raise KeyError(f"Key {key} not found in space {space}")
        else:
            raise KeyError(f"Space {space} not found")
    
    def remove(self, space: str, key: Hashable) -> None:
        if space in self._cache:
            if key in self._cache[space]:
                self._cache[space].pop(key)
            else:
                raise KeyError(f"Key {key} not found in space {space}")
        else:
            raise KeyError(f"Space {space} not found")
        
    def invalidate(self, space: str, key: Hashable) -> None:
        try:
            self.remove(space, key)
        except KeyError:
            pass
        
    def clear(self, space: str):
        if space in self._cache:
            self._cache.pop(space)
    
    def clear_all(self):
        self._cache = {}
            