from __future__ import annotations
import os
import sys
import sqlite3
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models_sa import Base, LoanORM, InstallmentORM

# PostgreSQL connection string from Render
POSTGRES_URL = "postgresql://mikrokredit_user:6xoKkR0wfL1Zc0YcmqcE4GSjBSXlQ8Rv@dpg-d308623e5dus73dfrrsg-a.oregon-postgres.render.com/mikrokredit"

# Local SQLite database path
SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mikrokredit.db")


def migrate_from_postgres_to_sqlite() -> None:
    """Migrate data from PostgreSQL (Render) to local SQLite database"""
    
    print("Starting migration from PostgreSQL to SQLite...")
    
    # Create PostgreSQL engine
    try:
        postgres_engine = create_engine(POSTGRES_URL, echo=False)
        print("Connected to PostgreSQL database")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return
    
    # Create SQLite database and tables
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB}", echo=False)
    Base.metadata.create_all(bind=sqlite_engine)
    print(f"Created SQLite database at: {SQLITE_DB}")
    
    # Migrate data
    with Session(postgres_engine) as postgres_session, Session(sqlite_engine) as sqlite_session:
        # Migrate loans
        print("Migrating loans...")
        loans = postgres_session.query(LoanORM).all()
        print(f"Found {len(loans)} loans to migrate")
        
        for loan in loans:
            sqlite_loan = LoanORM(
                id=loan.id,
                website=loan.website,
                loan_date=loan.loan_date,
                amount_borrowed=loan.amount_borrowed,
                amount_due=loan.amount_due,
                due_date=loan.due_date,
                risky_org=loan.risky_org,
                notes=loan.notes,
                payment_methods=loan.payment_methods,
                reminded_pre_due=loan.reminded_pre_due,
                created_at=loan.created_at,
                is_paid=loan.is_paid,
                org_name=loan.org_name,
            )
            sqlite_session.merge(sqlite_loan)
        
        sqlite_session.flush()
        print("Loans migrated successfully")
        
        # Migrate installments
        print("Migrating installments...")
        installments = postgres_session.query(InstallmentORM).all()
        print(f"Found {len(installments)} installments to migrate")
        
        for installment in installments:
            sqlite_installment = InstallmentORM(
                id=installment.id,
                loan_id=installment.loan_id,
                due_date=installment.due_date,
                amount=installment.amount,
                paid=installment.paid,
                paid_date=installment.paid_date,
                created_at=installment.created_at,
            )
            sqlite_session.merge(sqlite_installment)
        
        sqlite_session.commit()
        print("Installments migrated successfully")
    
    print("Migration completed successfully!")
    print(f"Data migrated to: {SQLITE_DB}")


if __name__ == "__main__":
    migrate_from_postgres_to_sqlite()
