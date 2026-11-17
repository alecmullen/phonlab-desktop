from sqlalchemy.orm import DeclarativeBase

# Set in a table's `info` for a table that is created when it is first needed, not
# with the rest of the database
ON_DEMAND = "on_demand"


class BaseEntity(DeclarativeBase):
    pass
