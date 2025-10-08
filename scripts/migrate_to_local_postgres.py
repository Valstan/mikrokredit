from __future__ import annotations
import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models_sa import Base, LoanORM, InstallmentORM

# PostgreSQL connection strings
RENDER_POSTGRES_URL = "postgresql://mikrokredit_user:6xoKkR0wfL1Zc0YcmqcE4GSjBSXlQ8Rv@dpg-d308623e5dus73dfrrsg-a.oregon-postgres.render.com/mikrokredit"
LOCAL_POSTGRES_URL = "postgresql://mikrokredit_user:mikrokredit_pass_2024@localhost:5434/mikrokredit_db"


def migrate_from_render_to_local_postgres() -> None:
    """Migrate data from Render PostgreSQL to local PostgreSQL database"""
    
    print("Starting migration from Render PostgreSQL to local PostgreSQL...")
    
    # Create engines
    try:
        render_engine = create_engine(RENDER_POSTGRES_URL, echo=False)
        print("Connected to Render PostgreSQL database")
    except Exception as e:
        print(f"Error connecting to Render PostgreSQL: {e}")
        return
    
    try:
        local_engine = create_engine(LOCAL_POSTGRES_URL, echo=False)
        print("Connected to local PostgreSQL database")
    except Exception as e:
        print(f"Error connecting to local PostgreSQL: {e}")
        return
    
    # Create tables in local database
    Base.metadata.create_all(bind=local_engine)
    print("Created tables in local PostgreSQL database")
    
    # Migrate data
    with Session(render_engine) as render_session, Session(local_engine) as local_session:
        # Migrate loans
        print("Migrating loans...")
        loans = render_session.query(LoanORM).all()
        print(f"Found {len(loans)} loans to migrate")
        
        for loan in loans:
            local_loan = LoanORM(
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
            local_session.merge(local_loan)
        
        local_session.flush()
        print("Loans migrated successfully")
        
        # Migrate installments
        print("Migrating installments...")
        installments = render_session.query(InstallmentORM).all()
        print(f"Found {len(installments)} installments to migrate")
        
        for installment in installments:
            local_installment = InstallmentORM(
                id=installment.id,
                loan_id=installment.loan_id,
                due_date=installment.due_date,
                amount=installment.amount,
                paid=installment.paid,
                paid_date=installment.paid_date,
                created_at=installment.created_at,
            )
            local_session.merge(local_installment)
        
        local_session.commit()
        print("Installments migrated successfully")
    
    print("Migration completed successfully!")
    print(f"Data migrated to local PostgreSQL at: {LOCAL_POSTGRES_URL}")


if __name__ == "__main__":
    migrate_from_render_to_local_postgres()
