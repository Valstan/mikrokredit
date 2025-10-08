from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import date, timedelta

from .db import get_connection
from .models import Loan, Installment


def _row_to_loan(row) -> Loan:
    return Loan(
        id=row["id"],
        website=row["website"],
        loan_date=row["loan_date"],
        amount_borrowed=float(row["amount_borrowed"]),
        amount_due=float(row["amount_due"]),
        due_date=row["due_date"],
        risky_org=bool(row["risky_org"]),
        notes=row["notes"] or "",
        payment_methods=row["payment_methods"] or "",
        reminded_pre_due=bool(row["reminded_pre_due"]),
        created_at=row["created_at"],
        is_paid=bool(row["is_paid"]) if "is_paid" in row.keys() else False,
        org_name=row["org_name"] or "",
    )


def add_loan(loan: Loan) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO loans(
                website, loan_date, amount_borrowed, amount_due, due_date,
                risky_org, notes, payment_methods, reminded_pre_due, created_at, is_paid, org_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loan.website,
                loan.loan_date,
                loan.amount_borrowed,
                loan.amount_due,
                loan.due_date,
                1 if loan.risky_org else 0,
                loan.notes,
                loan.payment_methods,
                1 if loan.reminded_pre_due else 0,
                loan.created_at or date.today().isoformat(),
                1 if loan.is_paid else 0,
                loan.org_name,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_loan(loan: Loan) -> None:
    if loan.id is None:
        raise ValueError("Loan ID is required for update")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE loans
            SET website = ?, loan_date = ?, amount_borrowed = ?, amount_due = ?, due_date = ?,
                risky_org = ?, notes = ?, payment_methods = ?, reminded_pre_due = ?, is_paid = ?, org_name = ?
            WHERE id = ?
            """,
            (
                loan.website,
                loan.loan_date,
                loan.amount_borrowed,
                loan.amount_due,
                loan.due_date,
                1 if loan.risky_org else 0,
                loan.notes,
                loan.payment_methods,
                1 if loan.reminded_pre_due else 0,
                1 if loan.is_paid else 0,
                loan.org_name,
                loan.id,
            ),
        )
        conn.commit()


def delete_loan(loan_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
        conn.commit()


def get_all_loans() -> List[Loan]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM loans ORDER BY due_date ASC, id DESC").fetchall()
        return [_row_to_loan(r) for r in rows]


def get_due_soon_loans(days_before: int = 7) -> List[Loan]:
    today = date.today()
    target = today + timedelta(days=days_before)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM loans
            WHERE date(due_date) BETWEEN date(?) AND date(?)
              AND reminded_pre_due = 0
            ORDER BY due_date ASC
            """,
            (today.isoformat(), target.isoformat()),
        ).fetchall()
        return [_row_to_loan(r) for r in rows]


def mark_loan_reminded(loan_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE loans SET reminded_pre_due = 1 WHERE id = ?", (loan_id,))
        conn.commit()


# Installments

def _row_to_installment(row) -> Installment:
    return Installment(
        id=row["id"],
        loan_id=row["loan_id"],
        due_date=row["due_date"],
        amount=float(row["amount"]),
        paid=bool(row["paid"]),
        paid_date=row["paid_date"],
        created_at=row["created_at"],
    )


def list_installments(loan_id: int) -> List[Installment]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM installments WHERE loan_id = ? ORDER BY due_date ASC, id ASC",
            (loan_id,),
        ).fetchall()
        return [_row_to_installment(r) for r in rows]


def add_installment(inst: Installment) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO installments(loan_id, due_date, amount, paid, paid_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inst.loan_id,
                inst.due_date,
                inst.amount,
                1 if inst.paid else 0,
                inst.paid_date,
                inst.created_at or date.today().isoformat(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_installment(inst: Installment) -> None:
    if inst.id is None:
        raise ValueError("Installment ID is required for update")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE installments
            SET due_date = ?, amount = ?, paid = ?, paid_date = ?
            WHERE id = ?
            """,
            (
                inst.due_date,
                inst.amount,
                1 if inst.paid else 0,
                inst.paid_date,
                inst.id,
            ),
        )
        conn.commit()


def delete_installment(installment_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM installments WHERE id = ?", (installment_id,))
        conn.commit()


def mark_installment_paid(installment_id: int, paid: bool, paid_date: Optional[str] = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE installments SET paid = ?, paid_date = ? WHERE id = ?",
            (1 if paid else 0, paid_date, installment_id),
        )
        conn.commit()


def get_next_unpaid_installment(loan_id: int) -> Optional[Installment]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM installments
            WHERE loan_id = ? AND paid = 0
            ORDER BY due_date ASC, id ASC
            LIMIT 1
            """,
            (loan_id,),
        ).fetchone()
        return _row_to_installment(row) if row else None


def get_next_payment_for_loan(loan: Loan) -> Optional[Tuple[str, float]]:
    if loan.is_paid:
        return None
    nxt = get_next_unpaid_installment(loan.id) if loan.id is not None else None
    if nxt is not None:
        return nxt.due_date, nxt.amount
    # Fallback to whole loan due
    return loan.due_date, loan.amount_due


def update_loan_paid_status_if_complete(loan_id: int) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(1) FROM installments WHERE loan_id = ? AND paid = 0",
            (loan_id,),
        ).fetchone()
        has_unpaid = row[0] > 0 if row else False
        if not has_unpaid:
            conn.execute("UPDATE loans SET is_paid = 1 WHERE id = ?", (loan_id,))
            conn.commit()


def get_installments_total(loan_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM installments WHERE loan_id = ?",
            (loan_id,),
        ).fetchone()
        return float(row[0] or 0.0)


def get_installments_unpaid_total(loan_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM installments WHERE loan_id = ? AND paid = 0",
            (loan_id,),
        ).fetchone()
        return float(row[0] or 0.0)


def get_last_installment_date(loan_id: int) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(due_date) FROM installments WHERE loan_id = ?",
            (loan_id,),
        ).fetchone()
        return row[0] if row and row[0] else None


def recalc_loan_amount_due(loan_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE loans
            SET amount_due = (SELECT COALESCE(SUM(amount), 0) FROM installments WHERE loan_id = ?)
            WHERE id = ?
            """,
            (loan_id, loan_id),
        )
        conn.commit()
