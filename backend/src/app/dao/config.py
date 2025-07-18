from functools import lru_cache
from pathlib import Path
from typing import Any
import json
from src.app.dao.connection import UserDaoAccess
from src.app.utils.tools import get_files_bucket

class configDao:
    # json config file, can be replaced by nosql db
    CONFIG_FILENAME = 'config.json'
    
    def __init__(self, dao_access: UserDaoAccess):  
        self.dao_access = dao_access
    
    def getConfigPath(self) -> str:
        return (Path(get_files_bucket()) / self.dao_access.user.user_id / 'config' / self.CONFIG_FILENAME).as_posix()
    
    @lru_cache
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
        return self.get_config().get(key)
    
    def set_config_value(self, key: str, value: Any):
        config = self.get_config()
        config[key] = value
        
        # write config back
        filepath = self.getConfigPath()
        fs = self.dao_access.file_fs
        with fs.open(filepath, 'w') as obj:
            json.dump(config, obj, indent=4)
        
        # clear cache
        self.get_config.cache_clear()