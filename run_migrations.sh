#!/bin/bash
# Run Alembic migrations inside Docker

docker-compose exec api python -m alembic upgrade head
