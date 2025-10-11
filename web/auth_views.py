"""
Маршруты для аутентификации
Регистрация, вход, восстановление пароля, верификация email
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.auth import (
    authenticate_user, is_ip_blocked, add_login_attempt,
    clear_login_attempts, get_client_ip, get_block_time_remaining,
    create_user, generate_verification_token, verify_email_token,
    generate_password_reset_token, reset_password, get_user_by_email,
    is_valid_email, is_strong_password
)
from app.email_service import email_service
from app import audit_log

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    # Если уже авторизован - редирект
    if session.get('user_id'):
        return redirect(url_for('views.dashboard'))
    
    client_ip = get_client_ip()
    
    # Проверяем блокировку
    if is_ip_blocked(client_ip):
        remaining = get_block_time_remaining(client_ip)
        return render_template('auth/blocked.html', remaining=remaining)
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('auth/login.html')
        
        # Аутентификация
        user_id = authenticate_user(email, password)
        
        if user_id:
            # Успешный вход
            session['user_id'] = user_id
            session.permanent = True  # Cookie на 30 дней
            clear_login_attempts(client_ip)
            
            # Проверяем верификацию email
            user = get_user_by_email(email)
            if user and not user.email_verified:
                flash('Внимание: ваш email еще не подтвержден. Проверьте почту или запросите новое письмо.', 'warning')
            
            # Логирование успешного входа
            audit_log.log_user_login(user_id, email, client_ip, success=True)
            
            flash(f'Добро пожаловать!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('views.dashboard'))
        else:
            # Неверный email или пароль
            audit_log.log_user_login(0, email, client_ip, success=False)
            attempts_left = add_login_attempt(client_ip)
            
            if attempts_left == 0:
                # Заблокирован
                remaining = get_block_time_remaining(client_ip)
                return render_template('auth/blocked.html', remaining=remaining)
            else:
                flash(f'Неверный email или пароль. Осталось попыток: {attempts_left}', 'danger')
    
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    # Если уже авторизован - редирект
    if session.get('user_id'):
        return redirect(url_for('views.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Валидация
        if not email or not password:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return render_template('auth/register.html', email=email, full_name=full_name)
        
        if not is_valid_email(email):
            flash('Некорректный email адрес', 'danger')
            return render_template('auth/register.html', email=email, full_name=full_name)
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return render_template('auth/register.html', email=email, full_name=full_name)
        
        is_strong, error = is_strong_password(password)
        if not is_strong:
            flash(error, 'danger')
            return render_template('auth/register.html', email=email, full_name=full_name)
        
        # Проверяем существование пользователя
        existing_user = get_user_by_email(email)
        if existing_user:
            flash('Пользователь с таким email уже зарегистрирован', 'danger')
            return render_template('auth/register.html', full_name=full_name)
        
        # Создаем пользователя
        user_id = create_user(email, password, full_name)
        
        if not user_id:
            flash('Ошибка при создании аккаунта. Попробуйте снова', 'danger')
            return render_template('auth/register.html', email=email, full_name=full_name)
        
        # Логирование регистрации
        client_ip = get_client_ip()
        audit_log.log_user_registered(user_id, email, client_ip)
        
        # Генерируем токен верификации
        token = generate_verification_token(user_id)
        
        # Отправляем письмо с подтверждением
        email_sent = email_service.send_verification_email(email, full_name or email, token)
        
        if email_sent:
            flash('Регистрация успешна! Проверьте вашу почту для подтверждения email.', 'success')
        else:
            flash('Регистрация успешна! Email сервис временно недоступен, но вы можете войти в систему.', 'warning')
        
        # Автоматический вход после регистрации
        session['user_id'] = user_id
        session.permanent = True
        
        return redirect(url_for('views.dashboard'))
    
    return render_template('auth/register.html')


@bp.route('/verify-email/<token>')
def verify_email(token):
    """Подтверждение email по токену"""
    user_id = verify_email_token(token)
    
    if user_id:
        # Отправляем приветственное письмо
        from app.db_sa import get_session
        from app.models_sa import UserORM
        
        with get_session() as db:
            user = db.query(UserORM).filter_by(id=user_id).first()
            if user:
                email_service.send_welcome_email(user.email, user.full_name or user.email)
                # Логирование верификации
                audit_log.log_email_verified(user_id, user.email)
        
        flash('Email успешно подтвержден! Добро пожаловать в систему.', 'success')
        
        # Если пользователь уже залогинен - редирект на dashboard
        if session.get('user_id'):
            return redirect(url_for('views.dashboard'))
        else:
            return redirect(url_for('auth.login'))
    else:
        flash('Недействительная или истекшая ссылка подтверждения', 'danger')
        return redirect(url_for('auth.login'))


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Запрос восстановления пароля"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Пожалуйста, введите email', 'danger')
            return render_template('auth/forgot_password.html')
        
        # Всегда показываем успех (безопасность - не раскрываем существование email)
        flash('Если аккаунт с таким email существует, на него будет отправлено письмо с инструкциями', 'info')
        
        # Пытаемся отправить письмо
        user = get_user_by_email(email)
        if user:
            token = generate_password_reset_token(email)
            if token:
                email_service.send_password_reset_email(email, user.full_name or email, token)
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_page(token):
    """Установка нового пароля по токену"""
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if not new_password:
            flash('Пожалуйста, введите новый пароль', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if new_password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        is_strong, error = is_strong_password(new_password)
        if not is_strong:
            flash(error, 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Сбрасываем пароль
        success = reset_password(token, new_password)
        
        if success:
            flash('Пароль успешно изменен! Теперь вы можете войти с новым паролем.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Недействительная или истекшая ссылка восстановления', 'danger')
            return redirect(url_for('auth.forgot_password'))
    
    return render_template('auth/reset_password.html', token=token)


@bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Повторная отправка письма с подтверждением"""
    user_id = session.get('user_id')
    
    if not user_id:
        flash('Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('auth.login'))
    
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('auth.login'))
        
        if user.email_verified:
            flash('Ваш email уже подтвержден', 'info')
            return redirect(url_for('views.dashboard'))
        
        # Генерируем новый токен
        token = generate_verification_token(user_id)
        
        # Отправляем письмо с защитой от зависания
        email_sent = False
        if email_service.enabled:
            try:
                print(f"📤 Повторная отправка письма верификации на {user.email}...")
                email_sent = email_service.send_verification_email(
                    user.email,
                    user.full_name or user.email,
                    token
                )
                if email_sent:
                    print(f"✅ Письмо верификации отправлено на {user.email}")
            except Exception as e:
                print(f"⚠️  Ошибка при повторной отправке письма: {e}")
        
        if email_sent:
            flash('Письмо с подтверждением отправлено повторно. Проверьте почту.', 'success')
        else:
            flash('Email сервис не настроен. Обратитесь к администратору.', 'warning')
    
    return redirect(url_for('profile.index'))


@bp.route('/logout')
def logout():
    """Выход"""
    session.clear()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))
