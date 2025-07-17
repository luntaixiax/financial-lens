import tempfile
from pathlib import Path
import sqlalchemy
from sqlalchemy import MetaData, JSON, column, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqlmodel import Session, select, delete
from src.app.dao.connection import get_db_url, get_engine, UserDaoAccess
from src.app.model.exceptions import NotExistError
from src.app.dao.orm import get_class_by_tablename, SQLModelWithSort
from src.app.utils.tools import get_files_bucket, get_backup_bucket

def drop_tables(engine: Engine):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # respect foreign key constraints so sort the tables
    with Session(engine) as s:
        src_metadata = MetaData()
        src_metadata.reflect(bind=engine)
    
        for tbl in reversed(metadata.sorted_tables):
            table_cls = get_class_by_tablename(tbl.name)
            table_cls.__table__.drop(bind=engine) # type: ignore
            
def migrate_database(src_engine: Engine, tgt_engine: Engine):

    src_metadata = MetaData()
    src_metadata.reflect(bind=src_engine)
    
    # create table schema in target engine
    SQLModelWithSort.create_table_within_collection(
        collection='user_specific',
        engine=tgt_engine
    )
    
    # open connection to backup database
    with Session(tgt_engine) as s:
        
        tgt_metadata = MetaData()
        tgt_metadata.reflect(bind=tgt_engine)

        for table in tgt_metadata.sorted_tables:
            stmt = table.insert()
            # read objects from file system
            with Session(src_engine) as e:            
                src_table = src_metadata.tables[table.name]
                
                # select all rows
                rows = e.exec(src_table.select()) # type: ignore
                
                # need to sort the results to insert, otherwise some FK may be violated
                table_cls = get_class_by_tablename(table.name)
                rows = table_cls.sort_for_backup(rows) # type: ignore
                
                for index, row in enumerate(rows):
                    s.exec(stmt.values(row)) # type: ignore
                    s.commit()
                    
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


class backupDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
    
    def get_backup_folder_path(self, backup_id: str) -> str:
        return (Path(get_backup_bucket()) / self.dao_access.user.user_id / 'backup' / backup_id).as_posix()
    
    @classmethod
    def get_backup_db_fname(cls) -> str:
        return 'backup-data.db'
    
    def list_backup_ids(self) -> list[str]:
        bk_fs = self.dao_access.backup_fs
        file_root = Path(get_backup_bucket()) / self.dao_access.user.user_id / 'backup'
        try:
            files = bk_fs.ls(file_root, detail=True)
        except FileNotFoundError:
            return []
        
        ids = []
        for file in files:
            if file['type'] == 'directory':
                # S3FS use `Key` and MemoryFS use `name`
                ids.append(file.get('Key', file.get('name')).split('/')[-1])
        return ids
    
    def backup_files(self, backup_id: str):
        # backup all files, e.g., receipts
        # create backup folder
        bk_root = Path(self.get_backup_folder_path(backup_id)) / 'bk_files'
        bk_fs = self.dao_access.backup_fs
        bk_fs.mkdirs(bk_root, exist_ok=True)
        
        rpath = (Path(get_files_bucket()) / self.dao_access.user.user_id / 'files').as_posix()
        fs = self.dao_access.file_fs
        fs.mkdirs(rpath, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            # download files from fs to local temp dir first
            fs.get(
                rpath=rpath,
                lpath=(Path(tmpdirname) / 'bk_files').as_posix(),
                recursive=True
            )
            
            # upload files to backup folder
            bk_fs.put(
                lpath=(Path(tmpdirname) / 'bk_files').as_posix(),
                rpath=bk_root.as_posix(),
                recursive=True
            )
    
    def backup_database(self, backup_id: str):
        # read all data from src database and save to a sqlite database as backup
        
        # create backup folder
        bk_fs = self.dao_access.backup_fs
        bk_fs.mkdirs(self.get_backup_folder_path(backup_id), exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            
            # create sqlite3 database
            @event.listens_for(Engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                if isinstance(dbapi_connection, SQLite3Connection):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON;")
                    cursor.close()
            
            # setup sqlite database with all tables
            cur_path = Path(tmpdirname) / self.get_backup_db_fname()
            tgt_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
                            
            migrate_database(
                src_engine = self.dao_access.user_engine,
                tgt_engine = tgt_engine
            )
            
            # upload backup file to backup server
            bk_fs.put_file(
                lpath=cur_path,
                rpath=Path(self.get_backup_folder_path(backup_id)) / self.get_backup_db_fname()
            )
            
    def restore_files(self, backup_id: str):
        # read all files (e.g., receipts) from backup storage and save/overwrite current fs
        bk_root = Path(self.get_backup_folder_path(backup_id)) / 'bk_files'
        bk_fs = self.dao_access.backup_fs
        
        rpath = (Path(get_files_bucket()) / self.dao_access.user.user_id / 'files').as_posix()
        fs = self.dao_access.file_fs
        fs.mkdirs(rpath, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            
            # download from backup storage to local first
            bk_fs.get(
                rpath=bk_root.as_posix(),
                lpath=(Path(tmpdirname) / 'bk_files').as_posix(),
                recursive=True
            )
            
            # upload to current storage
            fs.put(
                lpath=(Path(tmpdirname) / 'bk_files').as_posix(),
                rpath=rpath,
                recursive=True
            )
            
            
    def restore_database(self, backup_id: str):
        # read all data from backup sqlite database (source) and overwrite the target database
        
        bk_fs = self.dao_access.backup_fs
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            cur_path = Path(tmpdirname) / self.get_backup_db_fname()
            # download the file to local first
            bk_fs.get_file(
                rpath=Path(self.get_backup_folder_path(backup_id)) / self.get_backup_db_fname(),
                lpath=cur_path
            )
            
            src_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
            tgt_engine = self.dao_access.user_engine
            
            # drop all existing tables
            drop_tables(tgt_engine)
            
            # copy data from source to target
            migrate_database(
                src_engine = src_engine,
                tgt_engine = tgt_engine
            )