#!/usr/bin/env python3
"""
Миграция для добавления новых полей в таблицу loans
"""
import sys
import os

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.secrets import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def main():
    import psycopg2
    
    print("🔧 Миграция: добавление новых полей в loans")
    
    # Подключение к БД
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    try:
        cur = conn.cursor()
        
        # Проверяем существуют ли уже поля
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'loans' 
            AND column_name IN ('loan_type', 'category', 'interest_rate')
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        
        if len(existing_columns) == 3:
            print("✓ Все поля уже существуют, миграция не требуется")
            return
        
        print(f"Найдено существующих полей: {len(existing_columns)}")
        
        # Добавляем loan_type
        if 'loan_type' not in existing_columns:
            print("  Добавляем loan_type...")
            cur.execute("""
                ALTER TABLE loans 
                ADD COLUMN IF NOT EXISTS loan_type VARCHAR(50) DEFAULT 'single'
            """)
            
            # Устанавливаем значение на основе installments
            cur.execute("""
                UPDATE loans 
                SET loan_type = CASE 
                    WHEN (SELECT COUNT(*) FROM installments WHERE loan_id = loans.id) > 0 
                    THEN 'installment' 
                    ELSE 'single' 
                END
            """)
        
        # Добавляем category
        if 'category' not in existing_columns:
            print("  Добавляем category...")
            cur.execute("""
                ALTER TABLE loans 
                ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'microloan'
            """)
        
        # Добавляем interest_rate
        if 'interest_rate' not in existing_columns:
            print("  Добавляем interest_rate...")
            cur.execute("""
                ALTER TABLE loans 
                ADD COLUMN IF NOT EXISTS interest_rate FLOAT DEFAULT 0.0
            """)
            
            # Рассчитываем процент переплаты для существующих займов
            cur.execute("""
                UPDATE loans 
                SET interest_rate = CASE 
                    WHEN amount_borrowed > 0 
                    THEN ROUND(((amount_due - amount_borrowed) / amount_borrowed * 100)::numeric, 2)
                    ELSE 0 
                END
                WHERE interest_rate = 0 OR interest_rate IS NULL
            """)
        
        conn.commit()
        print("✅ Миграция выполнена успешно!")
        
        # Статистика
        cur.execute("SELECT COUNT(*) FROM loans")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM loans WHERE loan_type = 'installment'")
        installment_count = cur.fetchone()[0]
        
        print(f"\n📊 Статистика:")
        print(f"  Всего займов: {total}")
        print(f"  С рассрочкой: {installment_count}")
        print(f"  Разовых: {total - installment_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

