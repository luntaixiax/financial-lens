from pathlib import Path
import tomli
from sqlmodel import create_engine

with open(Path.cwd().parent / "secrets.toml", mode="rb") as fp:
    config = tomli.load(fp)['mysql']

mysql_url = f"mysql+mysqlconnector://{config['username']}:{config['password']}@{config['ip']}:{config['port']}/{config['db']}"
engine = create_engine(mysql_url, echo=True)

if __name__ == '__main__':
    from src.dao.orm import SQLModel
    
    SQLModel.metadata.create_all(engine)