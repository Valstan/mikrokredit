#!/usr/bin/env python3
"""
Скрипт для экспорта данных из базы данных микрокредита.
Экспортирует все данные из таблиц loans и installments в JSON файл.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Добавляем путь к модулям приложения
sys.path.append(str(Path(__file__).parent.parent))

from app.config import DATABASE_URL
from app.models_sa import Base, LoanORM, InstallmentORM
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def create_session():
    """Создает сессию для работы с базой данных."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def export_data_to_json(output_file: str = None) -> str:
    """
    Экспортирует все данные из базы в JSON файл.
    
    Args:
        output_file: Путь к выходному файлу. Если не указан, создается автоматически.
    
    Returns:
        str: Путь к созданному файлу
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mikrokredit_export_{timestamp}.json"
    
    print(f"Подключение к базе данных...")
    print(f"URL: {DATABASE_URL}")
    
    session = create_session()
    
    try:
        print("Экспорт данных из таблицы loans...")
        loans = session.query(LoanORM).all()
        
        loans_data = []
        for loan in loans:
            loan_dict = {
                'id': loan.id,
                'website': loan.website,
                'loan_date': loan.loan_date,
                'amount_borrowed': float(loan.amount_borrowed),
                'amount_due': float(loan.amount_due),
                'due_date': loan.due_date,
                'risky_org': bool(loan.risky_org),
                'notes': loan.notes,
                'payment_methods': loan.payment_methods,
                'reminded_pre_due': bool(loan.reminded_pre_due),
                'created_at': loan.created_at,
                'is_paid': bool(loan.is_paid),
                'org_name': loan.org_name
            }
            loans_data.append(loan_dict)
        
        print(f"Найдено кредитов: {len(loans_data)}")
        
        print("Экспорт данных из таблицы installments...")
        installments = session.query(InstallmentORM).all()
        
        installments_data = []
        for installment in installments:
            installment_dict = {
                'id': installment.id,
                'loan_id': installment.loan_id,
                'due_date': installment.due_date,
                'amount': float(installment.amount),
                'paid': bool(installment.paid),
                'paid_date': installment.paid_date,
                'created_at': installment.created_at
            }
            installments_data.append(installment_dict)
        
        print(f"Найдено рассрочек: {len(installments_data)}")
        
        # Создаем структуру данных для экспорта
        export_data = {
            'export_info': {
                'export_date': datetime.now().isoformat(),
                'database_url': DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown',  # Скрываем учетные данные
                'total_loans': len(loans_data),
                'total_installments': len(installments_data)
            },
            'loans': loans_data,
            'installments': installments_data
        }
        
        # Записываем данные в JSON файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Данные успешно экспортированы в файл: {output_file}")
        print(f"Статистика:")
        print(f"   - Кредитов: {len(loans_data)}")
        print(f"   - Рассрочек: {len(installments_data)}")
        
        return output_file
        
    except Exception as e:
        print(f"[ERROR] Ошибка при экспорте данных: {e}")
        raise
    finally:
        session.close()


def export_data_to_sql(output_file: str = None) -> str:
    """
    Экспортирует данные в SQL файл для импорта в другую базу данных.
    
    Args:
        output_file: Путь к выходному файлу. Если не указан, создается автоматически.
    
    Returns:
        str: Путь к созданному файлу
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mikrokredit_export_{timestamp}.sql"
    
    print(f"Подключение к базе данных...")
    print(f"URL: {DATABASE_URL}")
    
    session = create_session()
    
    try:
        print("Экспорт данных в SQL формат...")
        
        # Получаем данные
        loans = session.query(LoanORM).all()
        installments = session.query(InstallmentORM).all()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- Экспорт данных микрокредита\n")
            f.write(f"-- Дата экспорта: {datetime.now().isoformat()}\n")
            f.write(f"-- Всего кредитов: {len(loans)}\n")
            f.write(f"-- Всего рассрочек: {len(installments)}\n\n")
            
            # Отключаем проверки внешних ключей
            f.write("-- Отключаем проверки внешних ключей\n")
            f.write("SET session_replication_role = replica;\n\n")
            
            # Очищаем таблицы
            f.write("-- Очищаем существующие данные\n")
            f.write("DELETE FROM installments;\n")
            f.write("DELETE FROM loans;\n\n")
            
            # Сбрасываем последовательности
            f.write("-- Сбрасываем последовательности\n")
            f.write("ALTER SEQUENCE loans_id_seq RESTART WITH 1;\n")
            f.write("ALTER SEQUENCE installments_id_seq RESTART WITH 1;\n\n")
            
            # Вставляем данные кредитов
            f.write("-- Вставка данных кредитов\n")
            for loan in loans:
                f.write(f"INSERT INTO loans (id, website, loan_date, amount_borrowed, amount_due, due_date, risky_org, notes, payment_methods, reminded_pre_due, created_at, is_paid, org_name) VALUES (\n")
                f.write(f"  {loan.id},\n")
                f.write(f"  {repr(loan.website)},\n")
                f.write(f"  {repr(loan.loan_date)},\n")
                f.write(f"  {loan.amount_borrowed},\n")
                f.write(f"  {loan.amount_due},\n")
                f.write(f"  {repr(loan.due_date)},\n")
                f.write(f"  {int(loan.risky_org)},\n")
                f.write(f"  {repr(loan.notes)},\n")
                f.write(f"  {repr(loan.payment_methods)},\n")
                f.write(f"  {int(loan.reminded_pre_due)},\n")
                f.write(f"  {repr(loan.created_at)},\n")
                f.write(f"  {int(loan.is_paid)},\n")
                f.write(f"  {repr(loan.org_name)}\n")
                f.write(f");\n\n")
            
            # Вставляем данные рассрочек
            f.write("-- Вставка данных рассрочек\n")
            for installment in installments:
                f.write(f"INSERT INTO installments (id, loan_id, due_date, amount, paid, paid_date, created_at) VALUES (\n")
                f.write(f"  {installment.id},\n")
                f.write(f"  {installment.loan_id},\n")
                f.write(f"  {repr(installment.due_date)},\n")
                f.write(f"  {installment.amount},\n")
                f.write(f"  {int(installment.paid)},\n")
                f.write(f"  {repr(installment.paid_date)},\n")
                f.write(f"  {repr(installment.created_at)}\n")
                f.write(f");\n\n")
            
            # Включаем проверки внешних ключей
            f.write("-- Включаем проверки внешних ключей\n")
            f.write("SET session_replication_role = DEFAULT;\n")
        
        print(f"[OK] Данные успешно экспортированы в SQL файл: {output_file}")
        print(f"Статистика:")
        print(f"   - Кредитов: {len(loans)}")
        print(f"   - Рассрочек: {len(installments)}")
        
        return output_file
        
    except Exception as e:
        print(f"[ERROR] Ошибка при экспорте данных: {e}")
        raise
    finally:
        session.close()


def main():
    """Основная функция скрипта."""
    print("Скрипт экспорта данных микрокредита")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--sql":
            # Экспорт в SQL формат
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
            export_data_to_sql(output_file)
        elif sys.argv[1] == "--help":
            print("Использование:")
            print("  python export_data.py           # Экспорт в JSON")
            print("  python export_data.py --sql     # Экспорт в SQL")
            print("  python export_data.py --help    # Показать эту справку")
        else:
            # Экспорт в JSON с указанным именем файла
            export_data_to_json(sys.argv[1])
    else:
        # Экспорт в JSON по умолчанию
        export_data_to_json()


if __name__ == "__main__":
    main()
