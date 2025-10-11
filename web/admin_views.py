"""
Административная панель
Управление пользователями, статистика системы
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import admin_required, get_current_user
from app.db_sa import get_session
from app.models_sa import UserORM, LoanORM, TaskORM, TaskCategoryORM
from sqlalchemy import func
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/users')
@admin_required
def users():
    """Список всех пользователей"""
    with get_session() as db:
        users_list = db.query(UserORM).order_by(UserORM.created_at.desc()).all()
        
        # Статистика по каждому пользователю
        users_data = []
        for user in users_list:
            loans_count = db.query(func.count(LoanORM.id)).filter_by(user_id=user.id).scalar()
            tasks_count = db.query(func.count(TaskORM.id)).filter_by(user_id=user.id).scalar()
            
            users_data.append({
                'user': user,
                'loans_count': loans_count,
                'tasks_count': tasks_count
            })
    
    return render_template('admin/users.html', users_data=users_data)


@bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """Детальная информация о пользователе"""
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('admin.users'))
        
        # Статистика
        loans_count = db.query(func.count(LoanORM.id)).filter_by(user_id=user.id).scalar()
        tasks_count = db.query(func.count(TaskORM.id)).filter_by(user_id=user.id).scalar()
        categories_count = db.query(func.count(TaskCategoryORM.id)).filter_by(user_id=user.id).scalar()
        
        stats = {
            'loans_count': loans_count,
            'tasks_count': tasks_count,
            'categories_count': categories_count
        }
    
    return render_template('admin/user_detail.html', user=user, stats=stats)


@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_active(user_id):
    """Активация/деактивация пользователя"""
    current_user = get_current_user()
    
    # Нельзя деактивировать самого себя
    if user_id == current_user.id:
        flash('Вы не можете деактивировать свой аккаунт', 'danger')
        return redirect(url_for('admin.users'))
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('admin.users'))
        
        user.is_active = not user.is_active
        user.updated_at = datetime.now().isoformat()
        db.flush()
        
        status = 'активирован' if user.is_active else 'деактивирован'
        flash(f'Пользователь {user.email} {status}', 'success')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))


@bp.route('/users/<int:user_id>/make-admin', methods=['POST'])
@admin_required
def make_admin(user_id):
    """Назначить/снять администратора"""
    current_user = get_current_user()
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('admin.users'))
        
        # Нельзя снять админа у самого себя если это последний админ
        if user_id == current_user.id and user.is_admin:
            admin_count = db.query(func.count(UserORM.id)).filter_by(is_admin=True).scalar()
            if admin_count <= 1:
                flash('Вы не можете снять права администратора у себя, так как вы единственный админ', 'danger')
                return redirect(url_for('admin.user_detail', user_id=user_id))
        
        user.is_admin = not user.is_admin
        user.updated_at = datetime.now().isoformat()
        db.flush()
        
        status = 'назначен администратором' if user.is_admin else 'снят с прав администратора'
        flash(f'Пользователь {user.email} {status}', 'success')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))


@bp.route('/stats')
@admin_required
def stats():
    """Общая статистика системы"""
    with get_session() as db:
        # Общая статистика
        total_users = db.query(func.count(UserORM.id)).scalar()
        active_users = db.query(func.count(UserORM.id)).filter_by(is_active=True).scalar()
        admin_users = db.query(func.count(UserORM.id)).filter_by(is_admin=True).scalar()
        verified_users = db.query(func.count(UserORM.id)).filter_by(email_verified=True).scalar()
        telegram_users = db.query(func.count(UserORM.id)).filter(UserORM.telegram_chat_id.isnot(None)).scalar()
        
        total_loans = db.query(func.count(LoanORM.id)).scalar()
        total_tasks = db.query(func.count(TaskORM.id)).scalar()
        total_categories = db.query(func.count(TaskCategoryORM.id)).scalar()
        
        # Последние регистрации
        recent_users = db.query(UserORM).order_by(UserORM.created_at.desc()).limit(5).all()
    
    stats_data = {
        'users': {
            'total': total_users,
            'active': active_users,
            'admins': admin_users,
            'verified': verified_users,
            'telegram': telegram_users
        },
        'content': {
            'loans': total_loans,
            'tasks': total_tasks,
            'categories': total_categories
        },
        'recent_users': recent_users
    }
    
    return render_template('admin/stats.html', stats=stats_data)

