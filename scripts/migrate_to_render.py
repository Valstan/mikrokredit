#!/usr/bin/env python3
"""
Скрипт для миграции данных из локальной SQLite базы в PostgreSQL на Render.
Запускать локально с установленной переменной DATABASE_URL.
"""

from __future__ import annotations
import os
import sys
import sqlite3
from datetime import date
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_sa import engine
from app.models_sa import Base, LoanORM, InstallmentORM

SQLITE_DB = os.environ.get("MIKROKREDIT_DB", "mikrokredit.db")


def migrate_to_render() -> None:
    """Мигрирует данные из SQLite в PostgreSQL на Render."""
    
    # Проверяем, что DATABASE_URL установлен
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ОШИБКА: Переменная DATABASE_URL не установлена!")
        print("Установите DATABASE_URL с URL вашей PostgreSQL базы на Render.")
        return
    
    if not database_url.startswith("postgresql://"):
        print("ОШИБКА: DATABASE_URL должен указывать на PostgreSQL базу!")
        return
    
    print(f"Миграция в PostgreSQL: {database_url}")
    
    # Создаем таблицы в целевой БД
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    
    # Читаем из SQLite
    if not os.path.exists(SQLITE_DB):
        print(f"ОШИБКА: SQLite база не найдена: {SQLITE_DB}")
        return
    
    print(f"Чтение данных из SQLite: {SQLITE_DB}")
    src = sqlite3.connect(SQLITE_DB)
    src.row_factory = sqlite3.Row
    
    try:
        with Session(engine) as session:
            # Мигрируем кредиты
            loans = src.execute("SELECT * FROM loans").fetchall()
            print(f"Найдено кредитов: {len(loans)}")
            
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
            print("Кредиты мигрированы")
            
            # Мигрируем платежи
            insts = src.execute("SELECT * FROM installments").fetchall()
            print(f"Найдено платежей: {len(insts)}")
            
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
            print("Платежи мигрированы")
            
        print("✅ Миграция завершена успешно!")
        print(f"✅ Мигрировано: {len(loans)} кредитов, {len(insts)} платежей")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        src.close()


if __name__ == "__main__":
    migrate_to_render()
