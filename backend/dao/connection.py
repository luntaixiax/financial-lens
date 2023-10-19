import os
import sys
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(ROOT)
import tomli
from sqlmodel import create_engine
from orm import SQLModel

with open(os.path.join(ROOT, "secrets.toml"), mode="rb") as fp:
    config = tomli.load(fp)['mysql']

mysql_url = f"mysql+mysqlconnector://{config['username']}:{config['password']}@{config['ip']}:{config['port']}/{config['db']}"
engine = create_engine(mysql_url, echo=True)

if __name__ == '__main__':
    SQLModel.metadata.create_all(engine)