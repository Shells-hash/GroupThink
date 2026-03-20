"""
Drop and recreate all database tables. DEVELOPMENT ONLY.
Run from project root: python scripts/reset_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backend.models  # noqa — register all models
from backend.database.engine import engine
from backend.database.base import Base

print("Dropping all tables…")
Base.metadata.drop_all(bind=engine)
print("Recreating all tables…")
Base.metadata.create_all(bind=engine)
print("Done.")
