"""
Маршруты для аутентификации
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.auth import (
    verify_password, is_ip_blocked, add_login_attempt,
    clear_login_attempts, get_client_ip, get_block_time_remaining
)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    client_ip = get_client_ip()
    
    # Проверяем блокировку
    if is_ip_blocked(client_ip):
        remaining = get_block_time_remaining(client_ip)
        return render_template('auth/blocked.html', remaining=remaining)
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if verify_password(password):
            # Успешный вход
            session['authenticated'] = True
            session.permanent = True  # Cookie на 30 дней
            clear_login_attempts(client_ip)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('views.dashboard'))
        else:
            # Неверный пароль
            attempts_left = add_login_attempt(client_ip)
            
            if attempts_left == 0:
                # Заблокирован
                remaining = get_block_time_remaining(client_ip)
                return render_template('auth/blocked.html', remaining=remaining)
            else:
                flash(f'Неверный пароль. Осталось попыток: {attempts_left}', 'danger')
    
    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    """Выход"""
    session.clear()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))

