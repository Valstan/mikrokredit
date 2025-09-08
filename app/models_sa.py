from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, Float, Boolean, ForeignKey
from typing import List, Optional


class Base(DeclarativeBase):
    pass


class LoanORM(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    website: Mapped[str] = mapped_column(String, nullable=False)
    loan_date: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM-DD
    amount_borrowed: Mapped[float] = mapped_column(Float, nullable=False)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    risky_org: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_methods: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reminded_pre_due: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    org_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    installments: Mapped[List["InstallmentORM"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan"
    )


class InstallmentORM(Base):
    __tablename__ = "installments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    paid_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    loan: Mapped[LoanORM] = relationship(back_populates="installments")
