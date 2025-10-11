"""
Личный кабинет пользователя
Профиль, настройки, уведомления, Telegram привязка
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.auth import login_required, get_current_user, update_user_password, is_valid_email, is_strong_password
from app.db_sa import get_session
from app.models_sa import UserORM
from datetime import datetime

bp = Blueprint('profile', __name__, url_prefix='/profile')


@bp.route('/')
@login_required
def index():
    """Просмотр профиля"""
    user = get_current_user()
    return render_template('profile/index.html', user=user)


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Редактирование профиля"""
    user = get_current_user()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Обновляем данные
        with get_session() as db:
            db_user = db.query(UserORM).filter_by(id=user.id).first()
            if db_user:
                db_user.full_name = full_name if full_name else None
                db_user.phone = phone if phone else None
                db_user.updated_at = datetime.now().isoformat()
                db.flush()
        
        flash('Профиль успешно обновлен', 'success')
        return redirect(url_for('profile.index'))
    
    return render_template('profile/edit.html', user=user)


@bp.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email():
    """Смена email адреса"""
    user = get_current_user()
    
    if request.method == 'POST':
        new_email = request.form.get('new_email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Валидация
        if not new_email or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('profile/change_email.html', user=user)
        
        if not is_valid_email(new_email):
            flash('Некорректный email адрес', 'danger')
            return render_template('profile/change_email.html', user=user)
        
        if new_email == user.email:
            flash('Новый email совпадает с текущим', 'warning')
            return redirect(url_for('profile.index'))
        
        # Проверяем текущий пароль
        from app.auth import authenticate_user, generate_verification_token
        from app.email_service import email_service
        
        user_id = authenticate_user(user.email, password)
        if not user_id:
            flash('Неверный пароль', 'danger')
            return render_template('profile/change_email.html', user=user)
        
        # Проверяем не занят ли новый email
        from app.auth import get_user_by_email
        existing = get_user_by_email(new_email)
        if existing:
            flash('Этот email уже используется другим пользователем', 'danger')
            return render_template('profile/change_email.html', user=user)
        
        # Сначала обновляем email в БД
        old_email = user.email
        with get_session() as db:
            db_user = db.query(UserORM).filter_by(id=user.id).first()
            if db_user:
                db_user.email = new_email
                db_user.email_verified = False
                db_user.email_verified_at = None
                db_user.updated_at = datetime.now().isoformat()
                db.commit()  # Сразу коммитим
        
        # Генерируем токен (отдельная транзакция)
        token = generate_verification_token(user.id)
        
        # Логирование
        try:
            from app import audit_log
            audit_log.log_security_event('EMAIL_CHANGED', f'user_id={user.id}, old={old_email}, new={new_email}')
        except Exception as e:
            print(f"⚠️  Audit log error: {e}")
        
        # Отправляем письмо синхронно (с timeout 5 секунд внутри)
        if email_service.enabled:
            try:
                print(f"📤 Отправка письма верификации на {new_email}...")
                email_sent = email_service.send_verification_email(new_email, user.full_name or new_email, token)
                if email_sent:
                    print(f"✅ Письмо верификации успешно отправлено на {new_email}")
                else:
                    print(f"⚠️  Письмо не отправлено (SMTP не настроен)")
            except Exception as e:
                print(f"⚠️  Ошибка при отправке письма верификации: {e}")
                import traceback
                traceback.print_exc()
        
        flash(f'Email изменен на {new_email}. Проверьте почту для подтверждения нового адреса.', 'success')
        return redirect(url_for('profile.index'))
    
    return render_template('profile/change_email.html', user=user)


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Смена пароля"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Валидация
        if not current_password or not new_password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('profile/change_password.html')
        
        if new_password != confirm_password:
            flash('Новые пароли не совпадают', 'danger')
            return render_template('profile/change_password.html')
        
        is_strong, error = is_strong_password(new_password)
        if not is_strong:
            flash(error, 'danger')
            return render_template('profile/change_password.html')
        
        # Проверяем текущий пароль
        from app.auth import authenticate_user
        user = get_current_user()
        user_id = authenticate_user(user.email, current_password)
        
        if not user_id:
            flash('Неверный текущий пароль', 'danger')
            return render_template('profile/change_password.html')
        
        # Обновляем пароль
        success = update_user_password(user.id, new_password)
        
        if success:
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('profile.index'))
        else:
            flash('Ошибка при изменении пароля', 'danger')
    
    return render_template('profile/change_password.html')


@bp.route('/security')
@login_required
def security():
    """Настройки безопасности"""
    user = get_current_user()
    return render_template('profile/security.html', user=user)


@bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    """Настройки уведомлений и привязка Telegram"""
    user = get_current_user()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_settings':
            # Обновление настроек уведомлений
            email_notifications = request.form.get('email_notifications') == 'on'
            telegram_notifications = request.form.get('telegram_notifications') == 'on'
            
            with get_session() as db:
                db_user = db.query(UserORM).filter_by(id=user.id).first()
                if db_user:
                    db_user.email_notifications = email_notifications
                    db_user.telegram_notifications = telegram_notifications
                    db_user.updated_at = datetime.now().isoformat()
                    db.flush()
            
            flash('Настройки уведомлений обновлены', 'success')
            
        elif action == 'generate_code':
            # Генерация кода для привязки Telegram
            from app.telegram_auth import generate_link_code
            code = generate_link_code(user.id)
            # Перенаправляем с кодом в параметре
            return redirect(url_for('profile.notifications', code=code))
        
        elif action == 'unlink_telegram':
            # Отвязка Telegram
            with get_session() as db:
                db_user = db.query(UserORM).filter_by(id=user.id).first()
                if db_user:
                    db_user.telegram_chat_id = None
                    db_user.telegram_username = None
                    db_user.updated_at = datetime.now().isoformat()
                    db.flush()
            
            flash('Telegram аккаунт отвязан', 'success')
        
        return redirect(url_for('profile.notifications'))
    
    return render_template('profile/notifications.html', user=user)


@bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Удаление аккаунта"""
    user = get_current_user()
    password = request.form.get('password', '')
    
    if not password:
        flash('Пожалуйста, введите пароль для подтверждения', 'danger')
        return redirect(url_for('profile.security'))
    
    # Проверяем пароль
    from app.auth import authenticate_user
    user_id = authenticate_user(user.email, password)
    
    if not user_id:
        flash('Неверный пароль', 'danger')
        return redirect(url_for('profile.security'))
    
    # Удаляем пользователя (CASCADE удалит все связанные данные)
    with get_session() as db:
        db_user = db.query(UserORM).filter_by(id=user.id).first()
        if db_user:
            db.delete(db_user)
            db.flush()
    
    # Выходим из системы
    session.clear()
    flash('Ваш аккаунт удален. Спасибо за использование системы!', 'info')
    return redirect(url_for('auth.login'))

