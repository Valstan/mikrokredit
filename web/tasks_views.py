"""
Маршруты для органайзера задач
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
from sqlalchemy import select, func
import json

from app.auth import login_required
from app.db_sa import get_session
from app.models_sa import TaskORM, TaskCategoryORM, SubtaskORM, TaskReminderORM, ReminderTemplateORM

bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@bp.route('/')
@login_required
def index():
    """Главная страница задач"""
    filter_by = request.args.get('filter', 'all')
    category_id = request.args.get('category')
    
    with get_session() as session:
        # Базовый запрос
        query = select(TaskORM)
        
        # Фильтры
        if filter_by == 'today':
            today = date.today().isoformat()
            query = query.where(TaskORM.due_date.like(f'{today}%'), TaskORM.status == 0)
        elif filter_by == 'overdue':
            now = datetime.now().isoformat()
            query = query.where(TaskORM.due_date < now, TaskORM.status == 0)
        elif filter_by == 'completed':
            query = query.where(TaskORM.status == 1)
        elif filter_by == 'important':
            query = query.where(TaskORM.importance == 1, TaskORM.status == 0)
        elif filter_by == 'pending':
            query = query.where(TaskORM.status == 0)
        
        if category_id:
            query = query.where(TaskORM.category_id == int(category_id))
        
        # Сортировка: сначала важные и просроченные
        query = query.order_by(TaskORM.importance.asc(), TaskORM.due_date.asc())
        
        tasks_orm = session.execute(query).scalars().all()
        
        # Преобразуем в словари
        tasks = []
        for task in tasks_orm:
            tasks.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'importance': task.importance,
                'due_date': task.due_date,
                'category_id': task.category_id,
                'category': {'name': task.category.name, 'color': task.category.color} if task.category else None,
                'subtasks': [{'title': st.title, 'completed': st.completed} for st in task.subtasks]
            })
        
        # Получаем категории для фильтра
        categories_orm = session.execute(select(TaskCategoryORM)).scalars().all()
        categories = [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories_orm]
        
        # Статистика
        stats = {
            'total': session.execute(select(func.count(TaskORM.id))).scalar() or 0,
            'completed': session.execute(select(func.count(TaskORM.id)).where(TaskORM.status == 1)).scalar() or 0,
            'pending': session.execute(select(func.count(TaskORM.id)).where(TaskORM.status == 0)).scalar() or 0,
            'overdue': session.execute(
                select(func.count(TaskORM.id)).where(
                    TaskORM.due_date < datetime.now().isoformat(),
                    TaskORM.status == 0
                )
            ).scalar() or 0,
            'today': 0
        }
        
    return render_template(
        'tasks/index.html',
        tasks=tasks,
        categories=categories,
        filter_by=filter_by,
        stats=stats
    )


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Создание новой задачи"""
    if request.method == 'POST':
        try:
            with get_session() as session:
                now = datetime.now().isoformat()
                
                task = TaskORM(
                    title=request.form.get('title', ''),
                    description=request.form.get('description'),
                    importance=int(request.form.get('importance', 2)),
                    due_date=request.form.get('due_date') or None,
                    category_id=int(request.form['category_id']) if request.form.get('category_id') else None,
                    created_at=now,
                    updated_at=now
                )
                
                session.add(task)
                session.flush()  # Получаем ID задачи
                
                # Добавляем подзадачи если есть
                subtasks_data = request.form.getlist('subtask_title[]')
                for idx, subtask_title in enumerate(subtasks_data):
                    if subtask_title.strip():
                        subtask = SubtaskORM(
                            task_id=task.id,
                            title=subtask_title.strip(),
                            order=idx,
                            created_at=now
                        )
                        session.add(subtask)
                
                # Применяем шаблон напоминаний если выбран
                template_id = request.form.get('reminder_template')
                if template_id and task.due_date:
                    apply_reminder_template(session, task, int(template_id))
                
                # Или добавляем кастомные напоминания
                reminder_times = request.form.getlist('reminder_time[]')
                for reminder_time in reminder_times:
                    if reminder_time.strip():
                        reminder = TaskReminderORM(
                            task_id=task.id,
                            reminder_time=reminder_time.strip(),
                            created_at=now
                        )
                        session.add(reminder)
                
                session.commit()
                flash('Задача создана успешно!', 'success')
                return redirect(url_for('tasks.index'))
                
        except Exception as e:
            flash(f'Ошибка при создании задачи: {e}', 'danger')
    
    with get_session() as session:
        cats_orm = session.execute(select(TaskCategoryORM)).scalars().all()
        categories = [{'id': c.id, 'name': c.name} for c in cats_orm]
        
        temps_orm = session.execute(select(ReminderTemplateORM)).scalars().all()
        templates = [{'id': t.id, 'name': t.name, 'description': t.description} for t in temps_orm]
        
    return render_template('tasks/edit.html', task=None, categories=categories, templates=templates)


@bp.route('/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id: int):
    """Редактирование задачи"""
    if request.method == 'POST':
        try:
            with get_session() as session:
                task = session.get(TaskORM, task_id)
                if not task:
                    flash('Задача не найдена', 'danger')
                    return redirect(url_for('tasks.index'))
                
                task.title = request.form.get('title', task.title)
                task.description = request.form.get('description')
                task.importance = int(request.form.get('importance', task.importance))
                task.due_date = request.form.get('due_date') or None
                task.category_id = int(request.form['category_id']) if request.form.get('category_id') else None
                task.updated_at = datetime.now().isoformat()
                
                # Обновляем подзадачи (простая логика - удалить все и создать заново)
                session.execute(select(SubtaskORM).where(SubtaskORM.task_id == task_id))
                for subtask in task.subtasks:
                    session.delete(subtask)
                
                subtasks_data = request.form.getlist('subtask_title[]')
                for idx, subtask_title in enumerate(subtasks_data):
                    if subtask_title.strip():
                        subtask = SubtaskORM(
                            task_id=task.id,
                            title=subtask_title.strip(),
                            order=idx,
                            created_at=datetime.now().isoformat()
                        )
                        session.add(subtask)
                
                # Обновляем напоминания (удалить неотправленные и создать новые)
                # Удаляем только неотправленные напоминания
                old_reminders = session.execute(
                    select(TaskReminderORM).where(
                        TaskReminderORM.task_id == task_id,
                        TaskReminderORM.sent == 0
                    )
                ).scalars().all()
                for reminder in old_reminders:
                    session.delete(reminder)
                
                # Добавляем новые напоминания
                reminder_times = request.form.getlist('reminder_time[]')
                now = datetime.now().isoformat()
                for reminder_time in reminder_times:
                    if reminder_time.strip():
                        reminder = TaskReminderORM(
                            task_id=task.id,
                            reminder_time=reminder_time.strip(),
                            created_at=now
                        )
                        session.add(reminder)
                
                # Или применяем шаблон
                template_id = request.form.get('reminder_template')
                if template_id and task.due_date:
                    apply_reminder_template(session, task, int(template_id))
                
                session.commit()
                flash('Задача обновлена!', 'success')
                return redirect(url_for('tasks.index'))
                
        except Exception as e:
            flash(f'Ошибка при обновлении: {e}', 'danger')
    
    with get_session() as session:
        task = session.get(TaskORM, task_id)
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('tasks.index'))
        
        cats_orm = session.execute(select(TaskCategoryORM)).scalars().all()
        categories = [{'id': c.id, 'name': c.name} for c in cats_orm]
        
        temps_orm = session.execute(select(ReminderTemplateORM)).scalars().all()
        templates = [{'id': t.id, 'name': t.name, 'description': t.description} for t in temps_orm]
        
        # Загружаем связанные данные
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'importance': task.importance,
            'status': task.status,
            'due_date': task.due_date,
            'category_id': task.category_id,
            'subtasks': [{'title': st.title, 'completed': st.completed} for st in task.subtasks],
            'reminders': [{'reminder_time': r.reminder_time, 'sent': r.sent} for r in task.reminders]
        }
        
    return render_template('tasks/edit.html', task=task_data, categories=categories, templates=templates)


@bp.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete(task_id: int):
    """Пометить задачу как выполненную"""
    with get_session() as session:
        task = session.get(TaskORM, task_id)
        if task:
            task.status = 1
            task.completed_at = datetime.now().isoformat()
            task.updated_at = datetime.now().isoformat()
            session.commit()
            flash('Задача отмечена как выполненная!', 'success')
        else:
            flash('Задача не найдена', 'danger')
    
    return redirect(url_for('tasks.index'))


@bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id: int):
    """Удалить задачу"""
    with get_session() as session:
        task = session.get(TaskORM, task_id)
        if task:
            session.delete(task)
            session.commit()
            flash('Задача удалена', 'success')
        else:
            flash('Задача не найдена', 'danger')
    
    return redirect(url_for('tasks.index'))


@bp.route('/categories')
@login_required
def categories():
    """Управление категориями"""
    with get_session() as session:
        cats_orm = session.execute(select(TaskCategoryORM)).scalars().all()
        cats = [{'id': c.id, 'name': c.name, 'color': c.color, 'created_at': c.created_at} for c in cats_orm]
    return render_template('tasks/categories.html', categories=cats)


@bp.route('/categories/new', methods=['POST'])
@login_required
def category_new():
    """Создание категории"""
    try:
        with get_session() as session:
            category = TaskCategoryORM(
                name=request.form.get('name', ''),
                color=request.form.get('color', '#3498db'),
                icon=request.form.get('icon'),
                created_at=datetime.now().isoformat()
            )
            session.add(category)
            session.commit()
            flash('Категория создана!', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    
    return redirect(url_for('tasks.categories'))


def apply_reminder_template(session, task: TaskORM, template_id: int):
    """Применить шаблон напоминаний к задаче"""
    template = session.get(ReminderTemplateORM, template_id)
    if not template or not task.due_date:
        return
    
    try:
        rules = json.loads(template.rules)
        due_datetime = datetime.fromisoformat(task.due_date)
        
        if rules.get('type') == 'before':
            # Интервалы до дедлайна (в минутах)
            for minutes_before in rules.get('intervals', []):
                reminder_time = due_datetime - timedelta(minutes=minutes_before)
                reminder = TaskReminderORM(
                    task_id=task.id,
                    reminder_time=reminder_time.isoformat(),
                    created_at=datetime.now().isoformat()
                )
                session.add(reminder)
        
        elif rules.get('type') == 'range':
            # Диапазон времени с частотой
            start_time = datetime.fromisoformat(rules.get('start'))
            end_time = datetime.fromisoformat(rules.get('end'))
            frequency_minutes = rules.get('frequency_minutes', 60)
            
            current_time = start_time
            while current_time <= end_time:
                reminder = TaskReminderORM(
                    task_id=task.id,
                    reminder_time=current_time.isoformat(),
                    created_at=datetime.now().isoformat()
                )
                session.add(reminder)
                current_time += timedelta(minutes=frequency_minutes)
                
    except Exception as e:
        print(f"Ошибка применения шаблона: {e}")

