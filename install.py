import launch

if not launch.is_installed("sqlalchemy"):
    launch.run_pip("install sqlalchemy", "requirement for task-scheduler")

if not launch.is_installed("filelock"):
    launch.run_pip("install filelock", "requirement for task-queue")
