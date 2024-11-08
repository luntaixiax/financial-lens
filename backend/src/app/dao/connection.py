from pathlib import Path
import tomli
from sqlmodel import create_engine
from functools import lru_cache

@lru_cache
def get_engine():
    with open(Path.cwd().parent / "secrets.toml", mode="rb") as fp:
        config = tomli.load(fp)['mysql']

    mysql_url = f"mysql+mysqlconnector://{config['username']}:{config['password']}@{config['ip']}:{config['port']}/{config['db']}"
    engine = create_engine(mysql_url, echo=True)
    return engine

if __name__ == '__main__':
    from src.app.dao.orm import SQLModel
    
    SQLModel.metadata.create_all(get_engine())