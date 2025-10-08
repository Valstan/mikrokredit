from dataclasses import dataclass
from typing import Optional


@dataclass
class Loan:
    id: Optional[int]
    website: str
    loan_date: str  # YYYY-MM-DD
    amount_borrowed: float
    amount_due: float
    due_date: str  # YYYY-MM-DD
    risky_org: bool
    notes: str
    payment_methods: str
    reminded_pre_due: bool = False
    created_at: str = ""
    is_paid: bool = False
    org_name: str = ""


@dataclass
class Installment:
    id: Optional[int]
    loan_id: int
    due_date: str  # YYYY-MM-DD
    amount: float
    paid: bool
    paid_date: Optional[str]
    created_at: str = ""
