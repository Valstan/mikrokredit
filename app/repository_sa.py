"""
Репозиторий для работы с базой данных через SQLAlchemy.
Используется в десктопной версии приложения.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from .db_sa import get_session
from .models_sa import LoanORM, InstallmentORM


class LoanRepositorySA:
    """Репозиторий для работы с кредитами через SQLAlchemy."""
    
    def get_all_loans(self) -> List[dict]:
        """Получить все кредиты с обогащенной информацией."""
        with get_session() as session:
            loans = session.execute(select(LoanORM)).scalars().all()
            enriched = []
            
            for loan in loans:
                # Получаем информацию о платежах
                unpaid_total = session.execute(
                    select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                        InstallmentORM.loan_id == loan.id, InstallmentORM.paid == 0
                    )
                ).scalar_one()
                
                derived_paid = unpaid_total == 0
                
                # Ближайший неоплаченный платеж
                next_row = None if derived_paid else session.execute(
                    select(InstallmentORM).where(
                        InstallmentORM.loan_id == loan.id, 
                        InstallmentORM.paid == 0
                    ).order_by(
                        InstallmentORM.due_date.asc(), 
                        InstallmentORM.id.asc()
                    ).limit(1)
                ).scalar_one_or_none()
                
                # Последняя дата платежа
                last_date = session.execute(
                    select(func.max(InstallmentORM.due_date)).where(
                        InstallmentORM.loan_id == loan.id
                    )
                ).scalar_one()
                
                # Общая сумма к возврату
                total_due = session.execute(
                    select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                        InstallmentORM.loan_id == loan.id
                    )
                ).scalar_one()
                
                enriched.append({
                    "id": loan.id,
                    "org_name": loan.org_name,
                    "website": loan.website,
                    "loan_date": loan.loan_date,
                    "amount_borrowed": loan.amount_borrowed,
                    "amount_due": float(total_due or 0.0),
                    "due_date": loan.due_date,
                    "risky_org": bool(loan.risky_org),
                    "notes": loan.notes,
                    "payment_methods": loan.payment_methods,
                    "reminded_pre_due": bool(loan.reminded_pre_due),
                    "created_at": loan.created_at,
                    "is_paid": derived_paid,
                    "next_date": next_row.due_date if next_row else None,
                    "next_amount": next_row.amount if next_row else None,
                    "remaining": float(unpaid_total or 0.0),
                    "last_date": last_date,
                })
            
            return enriched
    
    def get_loan_by_id(self, loan_id: int) -> Optional[dict]:
        """Получить кредит по ID."""
        with get_session() as session:
            loan = session.get(LoanORM, loan_id)
            if not loan:
                return None
            
            # Получаем информацию о платежах
            unpaid_total = session.execute(
                select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                    InstallmentORM.loan_id == loan.id, InstallmentORM.paid == 0
                )
            ).scalar_one()
            
            derived_paid = unpaid_total == 0
            
            return {
                "id": loan.id,
                "org_name": loan.org_name,
                "website": loan.website,
                "loan_date": loan.loan_date,
                "amount_borrowed": loan.amount_borrowed,
                "amount_due": loan.amount_due,
                "due_date": loan.due_date,
                "risky_org": bool(loan.risky_org),
                "notes": loan.notes,
                "payment_methods": loan.payment_methods,
                "reminded_pre_due": bool(loan.reminded_pre_due),
                "created_at": loan.created_at,
                "is_paid": derived_paid,
                "remaining": float(unpaid_total or 0.0),
            }
    
    def create_loan(self, loan_data: dict) -> int:
        """Создать новый кредит."""
        with get_session() as session:
            loan = LoanORM(
                org_name=loan_data["org_name"],
                website=loan_data["website"],
                loan_date=loan_data["loan_date"],
                amount_borrowed=loan_data["amount_borrowed"],
                amount_due=0.0,
                due_date=loan_data["due_date"],
                risky_org=int(loan_data.get("risky_org", False)),
                notes=loan_data.get("notes", ""),
                payment_methods=loan_data.get("payment_methods", ""),
                reminded_pre_due=0,
                created_at=date.today().isoformat(),
                is_paid=0,
            )
            session.add(loan)
            session.flush()
            return loan.id
    
    def update_loan(self, loan_id: int, loan_data: dict) -> bool:
        """Обновить кредит."""
        with get_session() as session:
            loan = session.get(LoanORM, loan_id)
            if not loan:
                return False
            
            loan.org_name = loan_data["org_name"]
            loan.website = loan_data["website"]
            loan.loan_date = loan_data["loan_date"]
            loan.amount_borrowed = loan_data["amount_borrowed"]
            loan.due_date = loan_data["due_date"]
            loan.risky_org = int(loan_data.get("risky_org", False))
            loan.notes = loan_data.get("notes", "")
            loan.payment_methods = loan_data.get("payment_methods", "")
            
            return True
    
    def delete_loan(self, loan_id: int) -> bool:
        """Удалить кредит."""
        with get_session() as session:
            loan = session.get(LoanORM, loan_id)
            if not loan:
                return False
            
            session.delete(loan)
            return True


class InstallmentRepositorySA:
    """Репозиторий для работы с платежами через SQLAlchemy."""
    
    def get_installments_by_loan_id(self, loan_id: int) -> List[dict]:
        """Получить все платежи по ID кредита."""
        with get_session() as session:
            installments = session.execute(
                select(InstallmentORM).where(
                    InstallmentORM.loan_id == loan_id
                ).order_by(
                    InstallmentORM.due_date.asc(),
                    InstallmentORM.id.asc()
                )
            ).scalars().all()
            
            return [
                {
                    "id": inst.id,
                    "loan_id": inst.loan_id,
                    "due_date": inst.due_date,
                    "amount": inst.amount,
                    "paid": bool(inst.paid),
                    "paid_date": inst.paid_date,
                    "created_at": inst.created_at,
                }
                for inst in installments
            ]
    
    def create_installment(self, installment_data: dict) -> int:
        """Создать новый платеж."""
        with get_session() as session:
            installment = InstallmentORM(
                loan_id=installment_data["loan_id"],
                due_date=installment_data["due_date"],
                amount=installment_data["amount"],
                paid=0,
                paid_date=None,
                created_at=date.today().isoformat(),
            )
            session.add(installment)
            
            # Пересчитываем поля кредита
            self._recalculate_loan_fields(session, installment_data["loan_id"])
            
            session.flush()
            return installment.id
    
    def update_installment(self, installment_id: int, installment_data: dict) -> bool:
        """Обновить платеж."""
        with get_session() as session:
            installment = session.get(InstallmentORM, installment_id)
            if not installment:
                return False
            
            installment.due_date = installment_data["due_date"]
            installment.amount = installment_data["amount"]
            
            # Пересчитываем поля кредита
            self._recalculate_loan_fields(session, installment.loan_id)
            
            return True
    
    def toggle_installment_paid(self, installment_id: int, paid: bool) -> bool:
        """Переключить статус оплаты платежа."""
        with get_session() as session:
            installment = session.get(InstallmentORM, installment_id)
            if not installment:
                return False
            
            installment.paid = 1 if paid else 0
            installment.paid_date = date.today().isoformat() if paid else None
            
            # Пересчитываем поля кредита
            self._recalculate_loan_fields(session, installment.loan_id)
            
            return True
    
    def delete_installment(self, installment_id: int) -> bool:
        """Удалить платеж."""
        with get_session() as session:
            installment = session.get(InstallmentORM, installment_id)
            if not installment:
                return False
            
            loan_id = installment.loan_id
            session.delete(installment)
            
            # Пересчитываем поля кредита
            self._recalculate_loan_fields(session, loan_id)
            
            return True
    
    def _recalculate_loan_fields(self, session: Session, loan_id: int) -> None:
        """Пересчитать поля кредита на основе платежей."""
        # Общая сумма к возврату
        total = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                InstallmentORM.loan_id == loan_id
            )
        ).scalar_one()
        
        # Неоплаченная сумма
        unpaid = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                InstallmentORM.loan_id == loan_id, 
                InstallmentORM.paid == 0
            )
        ).scalar_one()
        
        # Обновляем кредит
        loan = session.get(LoanORM, loan_id)
        if loan:
            loan.amount_due = float(total or 0.0)
            loan.is_paid = 1 if (unpaid or 0.0) == 0.0 else 0


# Создаем экземпляры репозиториев
loan_repo = LoanRepositorySA()
installment_repo = InstallmentRepositorySA()
