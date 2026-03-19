from app import models
from sqlalchemy import inspect

print("Budget columns:")
mapper = inspect(models.Budget)
for column in mapper.attrs:
    print(f"  - {column.key}")
