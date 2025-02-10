from pathlib import Path
from s3fs import S3FileSystem
from sqlalchemy import Engine
from sqlmodel import create_engine
from functools import lru_cache
from src.app.utils.tools import get_secret

@lru_cache
def get_engine() -> Engine:
    config = get_secret()['mysql']

    mysql_url = f"mysql+mysqlconnector://{config['username']}:{config['password']}@{config['ip']}:{config['port']}/{config['db']}"
    engine = create_engine(mysql_url, pool_size=10)
    return engine

@lru_cache
def get_fs() -> S3FileSystem:
    config = get_secret()['s3']
    
    s3a = S3FileSystem(
        anon=False,
        key=config['access_key'],
        secret=config['secret_access_key'],
        endpoint_url=f"http://{config['endpoint']}:{config['port']}",
    )
    return s3a

if __name__ == '__main__':
    from src.app.dao.orm import SQLModel
    
    SQLModel.metadata.create_all(get_engine())