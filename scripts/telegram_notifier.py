#!/usr/bin/env python3
"""
Telegram уведомления о горящих кредитах
Отправляет уведомления о займах со сроком оплаты <= 2 дней
"""

import sys
import os
from datetime import date, timedelta
import requests
from typing import List, Tuple

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db_sa import get_session
from app.models_sa import LoanORM, InstallmentORM
from sqlalchemy import select, func

# Конфигурация Telegram
TELEGRAM_TOKEN = "489021673:AAH7QDGmqzOMgT0W_wINvzWC1ihfljuFAKI"
TELEGRAM_CHAT_ID = "352096813"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Настройки уведомлений
DAYS_BEFORE_DUE = 2  # Уведомлять за 2 дня и менее


def send_telegram_message(text: str) -> bool:
    """Отправка сообщения в Telegram"""
    try:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False


def get_urgent_loans() -> List[dict]:
    """
    Получить список горящих кредитов
    Возвращает: [{'org_name': ..., 'website': ..., 'due_date': ..., 'amount': ..., 'days_left': ...}, ...]
    """
    urgent_loans = []
    today = date.today()
    threshold_date = today + timedelta(days=DAYS_BEFORE_DUE)
    
    with get_session() as session:
        # Получаем все неоплаченные займы
        loans = session.execute(
            select(LoanORM).where(LoanORM.is_paid == 0)
        ).scalars().all()
        
        for loan in loans:
            # Сразу получаем все данные внутри сессии
            loan_data = {
                'id': loan.id,
                'org_name': loan.org_name,
                'website': loan.website,
                'amount_due': loan.amount_due,
                'due_date': loan.due_date
            }
            # Проверяем ближайший неоплаченный платеж
            next_payment = session.execute(
                select(InstallmentORM)
                .where(
                    InstallmentORM.loan_id == loan.id,
                    InstallmentORM.paid == 0
                )
                .order_by(InstallmentORM.due_date.asc())
                .limit(1)
            ).scalar_one_or_none()
            
            if next_payment:
                # Есть платеж по рассрочке
                try:
                    payment_date = date.fromisoformat(next_payment.due_date)
                    days_left = (payment_date - today).days
                    
                    if days_left <= DAYS_BEFORE_DUE:
                        urgent_loans.append({
                            'org_name': loan_data['org_name'],
                            'website': loan_data['website'],
                            'due_date': next_payment.due_date,
                            'amount': next_payment.amount,
                            'days_left': days_left
                        })
                except ValueError:
                    pass  # Неверный формат даты
            else:
                # Нет платежей по рассрочке, проверяем основной срок
                try:
                    loan_due_date = date.fromisoformat(loan_data['due_date'])
                    days_left = (loan_due_date - today).days
                    
                    if days_left <= DAYS_BEFORE_DUE and loan_data['amount_due'] > 0:
                        urgent_loans.append({
                            'org_name': loan_data['org_name'],
                            'website': loan_data['website'],
                            'due_date': loan_data['due_date'],
                            'amount': loan_data['amount_due'],
                            'days_left': days_left
                        })
                except ValueError:
                    pass  # Неверный формат даты
    
    # Сортируем по количеству оставшихся дней
    urgent_loans.sort(key=lambda x: x['days_left'])
    return urgent_loans


def format_message(urgent_loans: List[dict]) -> str:
    """Форматирование сообщения для Telegram"""
    if not urgent_loans:
        return "🟢 <b>Горящих кредитов нет!</b>\n\nВсе платежи под контролем ✅"
    
    # Заголовок
    total_amount = sum(loan['amount'] for loan in urgent_loans)
    message = f"🔥 <b>ГОРЯЩИЕ КРЕДИТЫ</b> 🔥\n\n"
    message += f"📊 Всего: <b>{len(urgent_loans)}</b> кредит(ов)\n"
    message += f"💰 Сумма: <b>{total_amount:,.2f} ₽</b>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Список кредитов
    for loan in urgent_loans:
        due_date = loan['due_date']
        amount = loan['amount']
        days_left = loan['days_left']
        # Эмодзи в зависимости от срочности
        if days_left < 0:
            urgency = "🔴 ПРОСРОЧЕН"
            days_text = f"({abs(days_left)} дн. назад)"
        elif days_left == 0:
            urgency = "🔴 СЕГОДНЯ"
            days_text = ""
        elif days_left == 1:
            urgency = "🟠 ЗАВТРА"
            days_text = ""
        else:
            urgency = "🟡"
            days_text = f"(через {days_left} дн.)"
        
        # Название организации
        org_name = loan['org_name'] or "Без названия"
        
        # Формирование строки
        message += f"{urgency} <b>{org_name}</b> {days_text}\n"
        message += f"💳 Сумма: <b>{amount:,.2f} ₽</b>\n"
        message += f"📅 Срок: {due_date}\n"
        
        # Ссылка на сайт
        if loan['website']:
            message += f"🔗 <a href=\"{loan['website']}\">Перейти в личный кабинет</a>\n"
        
        message += "\n"
    
    # Футер
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "⏰ Не забудьте оплатить вовремя!"
    
    return message


def main():
    """Основная функция"""
    print(f"[{date.today()} {__import__('datetime').datetime.now().strftime('%H:%M:%S')}] Проверка горящих кредитов...")
    
    # Получаем список горящих кредитов
    urgent_loans = get_urgent_loans()
    
    print(f"Найдено горящих кредитов: {len(urgent_loans)}")
    
    # Формируем сообщение
    message = format_message(urgent_loans)
    
    # Отправляем в Telegram
    if send_telegram_message(message):
        print("✓ Уведомление отправлено в Telegram")
        return 0
    else:
        print("✗ Ошибка отправки уведомления")
        return 1


if __name__ == "__main__":
    sys.exit(main())

