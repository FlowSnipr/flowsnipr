from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import Integer, String

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
