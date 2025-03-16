from pathlib import Path
from typing import Literal
from s3fs import S3FileSystem
from sqlalchemy import Engine
from sqlmodel import create_engine
from functools import lru_cache
from src.app.utils.tools import get_secret

@lru_cache
def get_engine() -> Engine:
    config = get_secret()['database']

    db_url = f"{config['driver']}://{config['username']}:{config['password']}@{config['ip']}:{config['port']}/{config['db']}"
    engine = create_engine(db_url, pool_size=10)
    return engine

@lru_cache
def get_storage_fs(type_: Literal['files', 'backup'] = 'files') -> S3FileSystem:
    if type_ == 'files':
        config = get_secret()['storage_server']
    else:
        config = get_secret()['backup_server']
        
    if config['provider'] != 's3':
        endpoint_url = f"http://{config['endpoint']}:{config['port']}"
    else:
        endpoint_url = None
    
    s3a = S3FileSystem(
        anon=False,
        key=config['access_key'],
        secret=config['secret_access_key'],
        endpoint_url=endpoint_url,
    )
    return s3a

if __name__ == '__main__':
    from src.app.dao.orm import SQLModelWithSort
    
    SQLModelWithSort.metadata.create_all(get_engine())