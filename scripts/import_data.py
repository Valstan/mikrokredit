#!/usr/bin/env python3
"""
Скрипт для импорта данных в базу данных микрокредита.
Импортирует данные из JSON файла, созданного скриптом export_data.py.
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session():
    """Создает сессию для работы с базой данных."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def import_data_from_json(json_file: str, clear_existing: bool = False) -> None:
    """
    Импортирует данные из JSON файла в базу данных.
    
    Args:
        json_file: Путь к JSON файлу с данными
        clear_existing: Удалять ли существующие данные перед импортом
    """
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"Файл {json_file} не найден")
    
    print(f"Чтение данных из файла: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'loans' not in data or 'installments' not in data:
        raise ValueError("Неверный формат файла. Ожидается JSON с полями 'loans' и 'installments'")
    
    print(f"Подключение к базе данных...")
    print(f"URL: {DATABASE_URL}")
    
    session = create_session()
    
    try:
        if clear_existing:
            print("Очистка существующих данных...")
            session.query(InstallmentORM).delete()
            session.query(LoanORM).delete()
            session.commit()
        
        # Импорт кредитов
        print(f"Импорт {len(data['loans'])} кредитов...")
        loan_id_mapping = {}  # Старые ID -> Новые ID
        
        for loan_data in data['loans']:
            old_id = loan_data['id']
            del loan_data['id']  # Удаляем старый ID, чтобы создать новый
            
            loan = LoanORM(
                website=loan_data['website'],
                loan_date=loan_data['loan_date'],
                amount_borrowed=loan_data['amount_borrowed'],
                amount_due=loan_data['amount_due'],
                due_date=loan_data['due_date'],
                risky_org=int(loan_data['risky_org']),
                notes=loan_data['notes'],
                payment_methods=loan_data['payment_methods'],
                reminded_pre_due=int(loan_data['reminded_pre_due']),
                created_at=loan_data['created_at'],
                is_paid=int(loan_data['is_paid']),
                org_name=loan_data['org_name']
            )
            
            session.add(loan)
            session.flush()  # Получаем новый ID
            loan_id_mapping[old_id] = loan.id
        
        session.commit()
        print(f"[OK] Импортировано кредитов: {len(data['loans'])}")
        
        # Импорт рассрочек
        print(f"Импорт {len(data['installments'])} рассрочек...")
        imported_installments = 0
        
        for installment_data in data['installments']:
            old_loan_id = installment_data['loan_id']
            
            # Проверяем, есть ли соответствующий кредит
            if old_loan_id not in loan_id_mapping:
                print(f"[WARNING] Пропускаем рассрочку {installment_data['id']} - кредит {old_loan_id} не найден")
                continue
            
            new_loan_id = loan_id_mapping[old_loan_id]
            del installment_data['id']  # Удаляем старый ID
            
            installment = InstallmentORM(
                loan_id=new_loan_id,
                due_date=installment_data['due_date'],
                amount=installment_data['amount'],
                paid=int(installment_data['paid']),
                paid_date=installment_data['paid_date'],
                created_at=installment_data['created_at']
            )
            
            session.add(installment)
            imported_installments += 1
        
        session.commit()
        print(f"[OK] Импортировано рассрочек: {imported_installments}")
        
        print(f"Итоговая статистика:")
        print(f"   - Кредитов импортировано: {len(data['loans'])}")
        print(f"   - Рассрочек импортировано: {imported_installments}")
        
        # Показываем информацию о экспорте, если есть
        if 'export_info' in data:
            export_info = data['export_info']
            print(f"Информация об оригинальном экспорте:")
            print(f"   - Дата экспорта: {export_info.get('export_date', 'неизвестно')}")
            print(f"   - База данных: {export_info.get('database_url', 'неизвестно')}")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Ошибка при импорте данных: {e}")
        raise
    finally:
        session.close()


def main():
    """Основная функция скрипта."""
    print("Скрипт импорта данных микрокредита")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python import_data.py <json_file> [--clear]")
        print("")
        print("Параметры:")
        print("  json_file  - Путь к JSON файлу с данными")
        print("  --clear    - Удалить существующие данные перед импортом")
        print("")
        print("Пример:")
        print("  python import_data.py mikrokredit_export_20240101_120000.json")
        print("  python import_data.py mikrokredit_export_20240101_120000.json --clear")
        return
    
    json_file = sys.argv[1]
    clear_existing = "--clear" in sys.argv
    
    if clear_existing:
        print("[WARNING] ВНИМАНИЕ: Существующие данные будут удалены!")
        response = input("Продолжить? (y/N): ")
        if response.lower() not in ['y', 'yes', 'да']:
            print("Импорт отменен.")
            return
    
    try:
        import_data_from_json(json_file, clear_existing)
        print("[OK] Импорт завершен успешно!")
    except Exception as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
