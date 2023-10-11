import os

from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import declarative_base

from modules import scripts


Base = declarative_base()
metadata: MetaData = Base.metadata

file_prefix = os.getenv("TASK_SCHEDULER_FILE_PREFIX", "")
running_timeout = os.getenv("TASK_SCHEDULER_RUNNING_TIMEOUT", 300)
print(f"file prefix: {file_prefix} running timeout: {running_timeout}")
sqlite_db_fp = os.path.join(scripts.basedir(), f'{file_prefix}task_scheduler.sqlite3')
database_uri = os.getenv("TASK_DATABASE") or f"sqlite:///{sqlite_db_fp}"
is_mysql_db = database_uri.startswith("mysql")


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
