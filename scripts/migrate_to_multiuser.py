#!/usr/bin/env python3
"""
Скрипт миграции к многопользовательской системе

Этот скрипт:
1. Создает таблицы для многопользовательской системы
2. Создает admin пользователя на основе текущего AUTH_PASSWORD
3. Привязывает все существующие записи к admin пользователю
4. Создает дефолтные категории для admin
"""

import sys
import os
from datetime import datetime
from getpass import getpass

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from app.db_sa import engine, get_session
from app.models_sa import Base, UserORM, LoanORM, TaskORM, TaskCategoryORM


def create_tables():
    """Создание всех таблиц"""
    print("📦 Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")


def check_existing_admin():
    """Проверка существования admin пользователя"""
    with get_session() as session:
        admin = session.query(UserORM).filter_by(email='admin@mikrokredit.local').first()
        return admin


def create_admin_user(email: str, password: str, full_name: str):
    """Создание admin пользователя"""
    import bcrypt
    
    print(f"\n👤 Создание admin пользователя: {email}")
    
    # Хешируем пароль
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    now = datetime.now().isoformat()
    
    with get_session() as session:
        admin = UserORM(
            email=email,
            username='admin',
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
            is_admin=True,
            email_verified=True,
            email_verified_at=now,
            email_notifications=True,
            telegram_notifications=True,
            created_at=now,
            updated_at=now,
        )
        session.add(admin)
        session.flush()
        admin_id = admin.id
        
    print(f"✅ Admin пользователь создан с ID: {admin_id}")
    return admin_id


def migrate_loans(admin_id: int):
    """Привязка займов к admin пользователю"""
    with get_session() as session:
        # Проверяем есть ли уже user_id колонка
        result = session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='loans' AND column_name='user_id'"
        ))
        has_user_id = result.fetchone() is not None
        
        if not has_user_id:
            print("\n💰 Добавление user_id в таблицу loans...")
            # Добавляем колонку с временным nullable
            session.execute(text(
                f"ALTER TABLE loans ADD COLUMN user_id INTEGER"
            ))
            session.commit()
        
        # Обновляем все записи
        session.execute(text(
            f"UPDATE loans SET user_id = {admin_id} WHERE user_id IS NULL"
        ))
        session.commit()
        
        # Добавляем constraint если нужно
        if not has_user_id:
            session.execute(text(
                "ALTER TABLE loans ALTER COLUMN user_id SET NOT NULL"
            ))
            session.execute(text(
                f"ALTER TABLE loans ADD CONSTRAINT fk_loans_user_id "
                f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
            ))
            session.execute(text(
                "CREATE INDEX ix_loans_user_id ON loans(user_id)"
            ))
            session.commit()
        
        count = session.execute(text("SELECT COUNT(*) FROM loans")).scalar()
        print(f"✅ Привязано {count} займов к admin пользователю")


def migrate_task_categories(admin_id: int):
    """Привязка категорий задач к admin пользователю"""
    with get_session() as session:
        # Проверяем есть ли уже user_id колонка
        result = session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='task_categories' AND column_name='user_id'"
        ))
        has_user_id = result.fetchone() is not None
        
        if not has_user_id:
            print("\n📁 Добавление user_id в таблицу task_categories...")
            session.execute(text(
                f"ALTER TABLE task_categories ADD COLUMN user_id INTEGER"
            ))
            session.commit()
        
        # Обновляем все записи
        session.execute(text(
            f"UPDATE task_categories SET user_id = {admin_id} WHERE user_id IS NULL"
        ))
        session.commit()
        
        # Добавляем constraint если нужно
        if not has_user_id:
            session.execute(text(
                "ALTER TABLE task_categories ALTER COLUMN user_id SET NOT NULL"
            ))
            session.execute(text(
                f"ALTER TABLE task_categories ADD CONSTRAINT fk_task_categories_user_id "
                f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
            ))
            session.execute(text(
                "CREATE INDEX ix_task_categories_user_id ON task_categories(user_id)"
            ))
            session.commit()
        
        count = session.execute(text("SELECT COUNT(*) FROM task_categories")).scalar()
        print(f"✅ Привязано {count} категорий к admin пользователю")


def migrate_tasks(admin_id: int):
    """Привязка задач к admin пользователю"""
    with get_session() as session:
        # Проверяем есть ли уже user_id колонка
        result = session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='tasks' AND column_name='user_id'"
        ))
        has_user_id = result.fetchone() is not None
        
        if not has_user_id:
            print("\n✅ Добавление user_id в таблицу tasks...")
            session.execute(text(
                f"ALTER TABLE tasks ADD COLUMN user_id INTEGER"
            ))
            session.commit()
        
        # Обновляем все записи
        session.execute(text(
            f"UPDATE tasks SET user_id = {admin_id} WHERE user_id IS NULL"
        ))
        session.commit()
        
        # Добавляем constraint если нужно
        if not has_user_id:
            session.execute(text(
                "ALTER TABLE tasks ALTER COLUMN user_id SET NOT NULL"
            ))
            session.execute(text(
                f"ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user_id "
                f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
            ))
            session.execute(text(
                "CREATE INDEX ix_tasks_user_id ON tasks(user_id)"
            ))
            session.commit()
        
        count = session.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        print(f"✅ Привязано {count} задач к admin пользователю")


def main():
    print("=" * 60)
    print("🚀 МИГРАЦИЯ К МНОГОПОЛЬЗОВАТЕЛЬСКОЙ СИСТЕМЕ")
    print("=" * 60)
    
    # Проверяем существует ли уже admin
    existing_admin = check_existing_admin()
    if existing_admin:
        print(f"\n⚠️  Admin пользователь уже существует: {existing_admin.email}")
        response = input("Продолжить миграцию данных? (y/n): ")
        if response.lower() != 'y':
            print("❌ Миграция отменена")
            return
        admin_id = existing_admin.id
    else:
        # Создаем таблицы
        create_tables()
        
        # Запрашиваем данные для admin
        print("\n" + "=" * 60)
        print("Создание администратора системы")
        print("=" * 60)
        
        email = input("Email администратора [admin@mikrokredit.local]: ").strip() or "admin@mikrokredit.local"
        full_name = input("Полное имя [Administrator]: ").strip() or "Administrator"
        
        # Пароль
        print("\n💡 Используйте текущий пароль от AUTH_PASSWORD для совместимости")
        password = getpass("Пароль администратора: ")
        password_confirm = getpass("Подтвердите пароль: ")
        
        if password != password_confirm:
            print("❌ Пароли не совпадают!")
            return
        
        if len(password) < 8:
            print("❌ Пароль должен быть не менее 8 символов!")
            return
        
        # Создаем admin
        admin_id = create_admin_user(email, password, full_name)
    
    # Мигрируем данные
    try:
        migrate_loans(admin_id)
        migrate_task_categories(admin_id)
        migrate_tasks(admin_id)
        
        print("\n" + "=" * 60)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print(f"\n📝 Администратор: {existing_admin.email if existing_admin else email}")
        print("🔐 Используйте этот email и пароль для входа в систему")
        print("\n⚠️  ВАЖНО: Перезапустите веб-сервер для применения изменений:")
        print("   cd /home/valstan/mikrokredit")
        print("   scripts/stop_service.sh")
        print("   scripts/start_service.sh")
        
    except Exception as e:
        print(f"\n❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Миграция прервана пользователем")
        sys.exit(1)

