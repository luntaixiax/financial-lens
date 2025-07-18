from sqlalchemy.engine import Engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from src.app.model.exceptions import NotExistError
from src.app.dao.orm import SQLModelWithSort
from src.app.dao.connection import get_db_url, get_engine

class initDao:
    def __init__(self, common_engine: Engine):
        self.common_engine = common_engine
        
    def init_common_db(self):
        # common db points to common collection
        if not database_exists(self.common_engine.url):
            create_database(self.common_engine.url)
        SQLModelWithSort.create_table_within_collection(
            collection='common',
            engine=self.common_engine
        )
    
    def init_user_db(self, user_id: str):
        # user db points to user_specific collection
        user_db_url = get_db_url(user_id)
        if not database_exists(user_db_url):
            create_database(user_db_url)
        SQLModelWithSort.create_table_within_collection(
            collection='user_specific',
            engine=get_engine(user_id)
        )
        
    def remove_user_db(self, user_id: str):
        # remove user specific db
        user_db_url = get_db_url(user_id)
        if database_exists(user_db_url):
            drop_database(user_db_url)
        else:
            raise NotExistError(
                f"User specific db {user_id} does not exist",
                details="N/A" # don't pass database info
            )