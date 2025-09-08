from __future__ import annotations
import os
import sqlite3
from datetime import date
from sqlalchemy.orm import Session
from app.db_sa import engine
from app.models_sa import Base, LoanORM, InstallmentORM

SQLITE_DB = os.environ.get("MIKROKREDIT_DB", "mikrokredit.db")


def migrate() -> None:
    # Create tables in target DB
    Base.metadata.create_all(bind=engine)

    # Read from SQLite directly
    if not os.path.exists(SQLITE_DB):
        print(f"SQLite DB not found: {SQLITE_DB}")
        return
    src = sqlite3.connect(SQLITE_DB)
    src.row_factory = sqlite3.Row

    with Session(engine) as session:
        loans = src.execute("SELECT * FROM loans").fetchall()
        for r in loans:
            loan = LoanORM(
                id=r["id"],
                website=r["website"],
                loan_date=r["loan_date"],
                amount_borrowed=float(r["amount_borrowed"]),
                amount_due=float(r["amount_due"]),
                due_date=r["due_date"],
                risky_org=int(r["risky_org"]) if r["risky_org"] is not None else 0,
                notes=r["notes"],
                payment_methods=r["payment_methods"],
                reminded_pre_due=int(r["reminded_pre_due"]) if r["reminded_pre_due"] is not None else 0,
                created_at=r["created_at"] or date.today().isoformat(),
                is_paid=int(r["is_paid"]) if "is_paid" in r.keys() else 0,
                org_name=r["org_name"] if "org_name" in r.keys() else None,
            )
            session.merge(loan)
        session.flush()

        insts = src.execute("SELECT * FROM installments").fetchall()
        for r in insts:
            inst = InstallmentORM(
                id=r["id"],
                loan_id=r["loan_id"],
                due_date=r["due_date"],
                amount=float(r["amount"]),
                paid=int(r["paid"]) if r["paid"] is not None else 0,
                paid_date=r["paid_date"],
                created_at=r["created_at"] or date.today().isoformat(),
            )
            session.merge(inst)
        session.commit()

    src.close()
    print("Migration completed.")


if __name__ == "__main__":
    migrate()
