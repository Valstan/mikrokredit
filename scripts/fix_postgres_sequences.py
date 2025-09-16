#!/usr/bin/env python3
"""
Скрипт для исправления последовательностей в PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine, text

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL

def fix_sequences():
    """Исправляет последовательности в PostgreSQL"""
    print(f"Подключение к базе данных: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Проверяем, есть ли таблицы
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('loans', 'installments')
        """))
        tables = [row[0] for row in result]
        print(f"Найденные таблицы: {tables}")
        
        if 'loans' in tables:
            # Получаем максимальный ID из таблицы loans
            result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM loans"))
            max_id = result.scalar()
            print(f"Максимальный ID в таблице loans: {max_id}")
            
            # Исправляем последовательность для loans
            conn.execute(text(f"SELECT setval('loans_id_seq', {max_id + 1}, false)"))
            print("Последовательность loans_id_seq исправлена")
        
        if 'installments' in tables:
            # Получаем максимальный ID из таблицы installments
            result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM installments"))
            max_id = result.scalar()
            print(f"Максимальный ID в таблице installments: {max_id}")
            
            # Исправляем последовательность для installments
            conn.execute(text(f"SELECT setval('installments_id_seq', {max_id + 1}, false)"))
            print("Последовательность installments_id_seq исправлена")
        
        conn.commit()
        print("Последовательности исправлены успешно!")

if __name__ == "__main__":
    fix_sequences()
