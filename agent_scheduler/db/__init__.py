from pathlib import Path
from sqlalchemy import create_engine, inspect, text, String, Text
from sqlalchemy_utils import create_database, database_exists

from .base import Base, metadata, database_uri, is_mysql_db
from .app_state import AppStateKey, AppState, AppStateManager
from .task import TaskStatus, Task, TaskManager

version = "1"

state_manager = AppStateManager()
task_manager = TaskManager()
TEXT_COLUME = "LONGTEXT" if is_mysql_db else "TEXT"
BLOB_COLUME = "LONGBLOB" if is_mysql_db else "BLOB"


def init():
    engine = create_engine(database_uri)
    if not database_exists(engine.url):
        create_database(engine.url)

    metadata.create_all(engine)

    state_manager.set_value(AppStateKey.Version, version)
    # check if app state exists
    if state_manager.get_value(AppStateKey.QueueState) is None:
        # create app state
        state_manager.set_value(AppStateKey.QueueState, "running")

    inspector = inspect(engine)
    with engine.connect() as conn:
        task_columns = inspector.get_columns("task")
        # add result column
        if not any(col["name"] == "result" for col in task_columns):
            conn.execute(text("ALTER TABLE task ADD COLUMN result TEXT"))

        # add api_task_id column
        if not any(col["name"] == "api_task_id" for col in task_columns):
            conn.execute(text("ALTER TABLE task ADD COLUMN api_task_id VARCHAR(64)"))

        # add api_task_callback column
        if not any(col["name"] == "api_task_callback" for col in task_columns):
            conn.execute(text("ALTER TABLE task ADD COLUMN api_task_callback VARCHAR(255)"))

        # add name column
        if not any(col["name"] == "name" for col in task_columns):
            conn.execute(text("ALTER TABLE task ADD COLUMN name VARCHAR(255)"))

        # add bookmarked column
        if not any(col["name"] == "bookmarked" for col in task_columns):
            conn.execute(text("ALTER TABLE task ADD COLUMN bookmarked BOOLEAN DEFAULT FALSE"))

        params_column = next(col for col in task_columns if col["name"] == "params")
        if version > "1" and not isinstance(params_column["type"], Text):
            transaction = conn.begin()
            conn.execute(
                text(
                    f"""
                    CREATE TABLE task_temp (
                        id VARCHAR(64) NOT NULL,
                        type VARCHAR(20) NOT NULL,
                        params {TEXT_COLUME} NOT NULL,
                        script_params {BLOB_COLUME} NOT NULL,
                        priority INTEGER NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        created_at DATETIME DEFAULT ("CURRENT_TIMESTAMP") NOT NULL,
                        updated_at DATETIME DEFAULT ("CURRENT_TIMESTAMP") NOT NULL,
                        result TEXT,
                        PRIMARY KEY (id)
                    )"""
                )
            )
            conn.execute(text("INSERT INTO task_temp SELECT * FROM task"))
            conn.execute(text("DROP TABLE task"))
            conn.execute(text("ALTER TABLE task_temp RENAME TO task"))
            transaction.commit()

        conn.close()


__all__ = [
    "init",
    "Base",
    "metadata",
    "database_uri",
    "AppStateKey",
    "AppState",
    "TaskStatus",
    "Task",
    "task_manager",
    "state_manager",
]
