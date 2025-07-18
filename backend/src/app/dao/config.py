from pathlib import Path
from typing import Any
import json
from src.app.utils.tools import LocalCacheKVStore
from src.app.dao.connection import UserDaoAccess
from src.app.utils.tools import get_files_bucket

class configDao:
    # json config file, can be replaced by nosql db
    CONFIG_FILENAME = 'config.json'
    LOCAL_CACHE = LocalCacheKVStore(capacity=100, ttl=60 * 60 * 8)
    
    def __init__(self, dao_access: UserDaoAccess):  
        self.dao_access = dao_access
    
    def getConfigPath(self) -> str:
        return (Path(get_files_bucket()) / self.dao_access.user.user_id / 'config' / self.CONFIG_FILENAME).as_posix()
    
    def get_config(self) -> dict[str, Any]:
        filepath = self.getConfigPath()
        fs = self.dao_access.file_fs
        try:
            with fs.open(filepath, 'r') as obj:
                config = json.load(obj)
        except FileNotFoundError as e:
            return {}
        
        # TODO: add error handling when config is not exist
        return config
    
    def get_config_value(self, key: str) -> Any:
        try:
            v = self.LOCAL_CACHE.get(
                space=self.dao_access.user.user_id,
                key=key
            )
        except (TimeoutError, KeyError) as e:
            v = self.get_config().get(key)
            self.LOCAL_CACHE.put(
                space=self.dao_access.user.user_id,
                key=key,
                value=v
            )
        return v
    
    def set_config_value(self, key: str, value: Any):
        config = self.get_config()
        config[key] = value
        
        # invalidate cache
        self.LOCAL_CACHE.invalidate(
            space=self.dao_access.user.user_id,
            key=key,
        )
        
        # write config back
        filepath = self.getConfigPath()
        fs = self.dao_access.file_fs
        with fs.open(filepath, 'w') as obj:
            json.dump(config, obj, indent=4)