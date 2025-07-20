import tempfile
from pathlib import Path
from fsspec import AbstractFileSystem
import sqlalchemy
from sqlalchemy import MetaData, JSON, column, event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy_utils import database_exists, create_database, drop_database
from sqlmodel import Session
from src.app.dao.user import userDao
from src.app.dao.connection import CommonDaoAccess, UserDaoAccess, get_engine
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
            
def migrate_database(src_engine: Engine, tgt_engine: Engine, collection: str):
    
    if not database_exists(src_engine.url):
        # return if source database not exist
        return
    
    # if target database not exist, create it
    if database_exists(tgt_engine.url):
        # drop all existing tables
        drop_database(tgt_engine.url)
    
    create_database(tgt_engine.url)


    src_metadata = MetaData()
    src_metadata.reflect(bind=src_engine)
    
    # create table schema in target engine
    SQLModelWithSort.create_table_within_collection(
        collection=collection,
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

def general_restore_db(bk_fs: AbstractFileSystem, bk_db_fname: str, bpath: str, tgt_engine: Engine, collection: str):
        
    with tempfile.TemporaryDirectory() as tmpdirname:
        cur_path = (Path(tmpdirname) / bk_db_fname).as_posix()
        # download the file to local first
        bk_fs.get_file(
            rpath=(Path(bpath) / bk_db_fname).as_posix(),
            lpath=cur_path
        )
        
        src_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path}')
        # copy data from source to target
        migrate_database(
            src_engine = src_engine,
            tgt_engine = tgt_engine,
            collection=collection
        )
            
def general_backup_db(bk_fs: AbstractFileSystem, bk_db_fname: str, bpath: str, src_engine: Engine, collection: str):
    bk_fs.mkdirs(bpath, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        
        # create sqlite3 database
        @event.listens_for(Engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.close()
        
        # setup sqlite database with all tables
        cur_path = (Path(tmpdirname) / bk_db_fname).as_posix()
        tgt_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path}')
                        
        migrate_database(
            src_engine = src_engine,
            tgt_engine = tgt_engine,
            collection=collection
        )
        
        # upload backup file to backup server
        bk_fs.put_file(
            lpath=cur_path,
            rpath=(Path(bpath) / bk_db_fname).as_posix()
        )

def general_backup_files(spath: str, file_fs: AbstractFileSystem, bpath: str, bk_fs: AbstractFileSystem):
    """Backup files from storage server to backup server
    Args:
        spath: folder root path on storage server that contains the files to backup
        file_fs: file system on storage server
        bpath: folderroot path on backup server that will paste the files (actual file will go under bpath/bk_files)
        bk_fs: file system on backup server
    """
    # root on backup server
    bk_root = Path(bpath) / 'bk_files'
    bk_fs.mkdirs(bk_root, exist_ok=True)
    
    # root on storage server
    #file_fs.mkdirs(spath, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        # download files from file storage to local temp dir first
        if file_fs.exists(spath):
            file_fs.get(
                rpath=spath,
                lpath=Path(tmpdirname) / 'bk_files',
                recursive=True
            )
            
            # upload files to backup server
            bk_fs.put(
                lpath=Path(tmpdirname) / 'bk_files',
                rpath=bk_root.as_posix(),
                recursive=True
            )
        
def general_restore_files(spath: str, file_fs: AbstractFileSystem, bpath: str, bk_fs: AbstractFileSystem):
    """Restore files from backup server to storage server
    Args:
        spath: folder root path on storage server that contains the files to backup
        file_fs: file system on storage server
        bpath: folderroot path on backup server that will paste the files (actual file will go under bpath/bk_files)
        bk_fs: file system on backup server
    """
    bk_root = Path(bpath) / 'bk_files'
    file_fs.mkdirs(spath, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        if bk_fs.exists(bk_root):
            # download from backup storage to local first
            bk_fs.get(
                rpath=bk_root.as_posix(),
                lpath=Path(tmpdirname) / 'bk_files', # for local FS, need to be Path to work properly, but for some db, may need posix string
                recursive=True
            )
            
            # upload to current storage
            file_fs.put(
                lpath=Path(tmpdirname) / 'bk_files',
                rpath=spath,
                recursive=True
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
        
        general_backup_files(
            spath=(Path(get_files_bucket()) / self.dao_access.user.user_id / 'files').as_posix(),
            file_fs=self.dao_access.file_fs,
            bpath=(Path(self.get_backup_folder_path(backup_id))).as_posix(),
            bk_fs=self.dao_access.backup_fs
        )
    
    def backup_database(self, backup_id: str):
        # read all data from src database and save to a sqlite database as backup
        general_backup_db(
            bk_fs=self.dao_access.backup_fs,
            bpath=self.get_backup_folder_path(backup_id),
            bk_db_fname=self.get_backup_db_fname(),
            src_engine=self.dao_access.user_engine,
            collection='user_specific',
        )
            
    def restore_files(self, backup_id: str):
        general_restore_files(
            spath=(Path(get_files_bucket()) / self.dao_access.user.user_id / 'files').as_posix(),
            file_fs=self.dao_access.file_fs,
            bpath=(Path(self.get_backup_folder_path(backup_id))).as_posix(),
            bk_fs=self.dao_access.backup_fs
        )
            
            
    def restore_database(self, backup_id: str):
        # read all data from backup sqlite database (source) and overwrite the target database
        general_restore_db(
            bk_fs=self.dao_access.backup_fs,
            bpath=self.get_backup_folder_path(backup_id),
            bk_db_fname=self.get_backup_db_fname(),
            tgt_engine=self.dao_access.user_engine,
            collection='user_specific',
        )        

            
class adminBackupDao:
    # only backup admin database, not user specific database
    
    def __init__(self, dao_access: CommonDaoAccess):
        self.dao_access = dao_access
        
    def get_backup_folder_path(self, backup_id: str) -> str:
        return (Path(get_backup_bucket()) / '_common' / 'backup' / backup_id).as_posix()
    
    @classmethod
    def get_backup_db_fname(cls) -> str:
        return 'backup-common.db'
        
    def list_backup_ids(self) -> list[str]:
        bk_fs = self.dao_access.backup_fs
        file_root = Path(get_backup_bucket()) / '_common' / 'backup'
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
        user_dao = userDao(self.dao_access.common_session)
        for user in user_dao.list_user():

            general_backup_files(
                spath=(Path(get_files_bucket()) / user.user_id / 'files').as_posix(),
                file_fs=self.dao_access.file_fs,
                bpath=(Path(self.get_backup_folder_path(backup_id)) / user.user_id).as_posix(),
                bk_fs=self.dao_access.backup_fs
            )
    
    def backup_database(self, backup_id: str):
        # read all data from src database and save to a sqlite database as backup
        general_backup_db(
            bk_fs=self.dao_access.backup_fs,
            bpath=self.get_backup_folder_path(backup_id),
            bk_db_fname=self.get_backup_db_fname(),
            src_engine=self.dao_access.common_engine,
            collection='common',
        )
        
        # back up all user specific databases
        user_dao = userDao(self.dao_access.common_session)
        for user in user_dao.list_user():
            
            user_engine = get_engine(user.user_id)
            
            general_backup_db(
                bk_fs=self.dao_access.backup_fs,
                bpath=(Path(self.get_backup_folder_path(backup_id)) / user.user_id).as_posix(),
                bk_db_fname='user-specific.db',
                src_engine=user_engine,
                collection='user_specific',
            )
        
            
    def restore_files(self, backup_id: str):
        
        user_dao = userDao(self.dao_access.common_session)
        for user in user_dao.list_user():
            general_restore_files(
                spath=(Path(get_files_bucket()) / user.user_id / 'files').as_posix(),
                file_fs=self.dao_access.file_fs,
                bpath=(Path(self.get_backup_folder_path(backup_id)) / user.user_id).as_posix(),
                bk_fs=self.dao_access.backup_fs
            )
            
            
    def restore_database(self, backup_id: str):
        # read all data from backup sqlite database (source) and overwrite the target database
        general_restore_db(
            bk_fs=self.dao_access.backup_fs,
            bpath=self.get_backup_folder_path(backup_id),
            bk_db_fname=self.get_backup_db_fname(),
            tgt_engine=self.dao_access.common_engine,
            collection='common',
        )
        
        # back up all user specific databases
        user_dao = userDao(self.dao_access.common_session)
        for user in user_dao.list_user():
            
            user_engine = get_engine(user.user_id)
            
            general_restore_db(
                bk_fs=self.dao_access.backup_fs,
                bpath=(Path(self.get_backup_folder_path(backup_id)) / user.user_id).as_posix(),
                bk_db_fname='user-specific.db',
                tgt_engine=user_engine,
                collection='user_specific',
            )