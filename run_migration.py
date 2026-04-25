#!/usr/bin/env python3
"""Script to run alembic migrations"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def run_migration():
    # Create alembic config
    alembic_cfg = Config("alembic.ini")

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()