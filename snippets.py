# uvicorn app.main:app --reload --port 9000


# 1. Install Alembic (if you haven't)
# pip install alembic

# 2. Initialize the directory structure
# alembic init alembic

# 3. Edit alembic.ini to set your database URL(sqlalchemy.url = ...)

# 4.Edit alembic/env.py to set target_metadata for "autogenerate" support

# 5. alembic revision --autogenerate -m "Initial migration" # Create a new migration script


# Install Alembic (once per project)
# pip install alembic

# Initialize Alembic
# Creates alembic/ and alembic.ini.

# Wire Alembic to your models and DB
# In env.py:

# import your models
# set target_metadata = models.Base.metadata
# set DB URL (from DATABASE_URL or your default)
# Stop auto‑creating tables in the app
# Removed models.Base.metadata.create_all() from main.py.

# Create the first migration
# alembic revision --autogenerate -m "initial"
# This compares models vs DB and writes a migration file.

# Fix enum edge case
# Since Postgres enums can already exist, we made the migration create the enum only if it doesn’t exist, and told SQLAlchemy not to recreate it.

# Apply the migration
# alembic upgrade head

# For future changes

# Update models
# Run: alembic revision --autogenerate -m "add xyz"
# Run: alembic upgrade head
