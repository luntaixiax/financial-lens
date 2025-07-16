from pathlib import Path
from typing import Generator, Literal
from s3fs import S3FileSystem
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine
from functools import lru_cache
from src.app.utils.tools import get_secret

def get_db_url(db: str) -> str:
    config = get_secret()['database']
    db_url = f"{config['driver']}://{config['username']}:{config['password']}@{config['hostname']}:{config['port']}/{db}"
    return db_url

@lru_cache
def get_engine(db: str = 'common') -> Engine:
    config = get_secret()['database']

    db_url = get_db_url(db)
    engine = create_engine(db_url, pool_size=10)
    return engine

@lru_cache
def engine_factory(db: str):
    
    def func() -> Generator[Engine, None, None]:
        yield get_engine(db)
    
    return func

@lru_cache
def session_factory(db: str):
    
    def get_session() -> Generator[Session, None, None]:
        engine = get_engine(db)
        with Session(engine) as s:
            yield s
    
    return get_session

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

def yield_file_fs() -> S3FileSystem:
    return get_storage_fs('files')
    
def yield_backup_fs() -> S3FileSystem:
    return get_storage_fs('backup')