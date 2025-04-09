#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import oracledb
import pymysql
import pathlib

# Check the dynamic_apps module
# Create if it doesn't exist
def ensure_dynamic_apps_module():
    # Path to where dynamic_apps should be (e.g., DjangoApp/dynamic_apps)
    project_root = pathlib.Path(__file__).parent
    dynamic_apps_path = project_root / "BUDjangoProxyApp" / "dynamic_apps"
    init_file = dynamic_apps_path / "__init__.py"

    # Create dynamic_apps directory if it doesn't exist
    dynamic_apps_path.mkdir(exist_ok=True)

    # Create __init__.py if it doesn't exist
    if not init_file.exists():
        init_file.touch()  # Creates an empty __init__.py

def main():
    # Initilazing the oracle and mysql main to initialize them once
    # "settings.py" is getting called multiple times due to dynamic DB addition
    oracledb.init_oracle_client()
    pymysql.install_as_MySQLdb()
    ensure_dynamic_apps_module()  # Ensure module exists before settings import

    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BUDjangoProxy.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
