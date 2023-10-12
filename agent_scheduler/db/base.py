import os

from sqlalchemy import create_engine, text
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from modules import scripts


Base = declarative_base()
metadata: MetaData = Base.metadata

file_prefix = os.getenv("TASK_SCHEDULER_FILE_PREFIX", "")
running_timeout = os.getenv("TASK_SCHEDULER_RUNNING_TIMEOUT", 300)
sqlite_db_fp = os.path.join(scripts.basedir(), f'{file_prefix}task_scheduler.sqlite3')
database_uri = os.getenv("TASK_DATABASE") or f"sqlite:///{sqlite_db_fp}"
is_mysql_db = database_uri.startswith("mysql")
lock_timeout = os.getenv("TASK_SCHEDULER_LOCK_TIMEOUT", 5)
lock_name = f"{file_prefix}_queue_lock" if is_mysql_db else os.path.join(scripts.basedir(), f"{file_prefix}task_queue.lock")
print(f"file prefix: {file_prefix} running timeout: {running_timeout} is mysql: {is_mysql_db}")


class BaseTableManager:
    def __init__(self, engine = None):
        # Get the db connection object, making the file and tables if needed.
        try:
            self.engine = engine if engine else create_engine(database_uri)
        except Exception as e:
            print(f"Exception connecting to database: {e}")
            raise e

    def get_engine(self):
        return self.engine

    # Commit and close the database connection.
    def quit(self):
        self.engine.dispose()


class MySQLLock(BaseTableManager):
    _session_factory = None
    _scoped_session = None

    @classmethod
    def initialize_session_factory(cls, engine_url):
        engine = create_engine(engine_url)
        cls._session_factory = sessionmaker(bind=engine)
        cls._scoped_session = scoped_session(cls._session_factory)

    def __init__(self, lock_name="task_lock", timeout=lock_timeout):
        super().__init__()
        if MySQLLock._scoped_session is None:
            raise ValueError("Please initialize the session factory first using `initialize_session_factory`.")


        self.lock_name = f"{file_prefix}_{lock_name}"
        self.timeout = timeout
        self.session = None

    def __enter__(self):
        self.session = MySQLLock._scoped_session()
        # Acquire the lock
        self.session.execute(text(f"SELECT GET_LOCK('{self.lock_name}', {self.timeout});"))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # 释放锁
        self.session.execute(text(f"SELECT RELEASE_LOCK('{self.lock_name}');"))
        # Commit changes and close session
        self.session.commit()
        self.session.close()


if is_mysql_db:
    # Initialization
    MySQLLock.initialize_session_factory(database_uri)