"""
Маршруты для органайзера задач
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
from sqlalchemy import select, func
import json

from app.auth import login_required
from app.db_sa import get_session
from app.models_sa import (
    TaskORM, TaskCategoryORM, SubtaskORM, TaskReminderORM, ReminderTemplateORM,
    TaskScheduleORM, ReminderRuleORM, ReminderRuleTemplateORM
)
from app.reminder_generator import regenerate_task_reminders

bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@bp.route('/clear-cache')
@login_required
def clear_cache():
    """Страница для очистки кэша браузера"""
    return render_template('tasks/clear_cache.html')


@bp.route('/')
@login_required
def index():
    """Главная страница задач"""
    from app.auth import get_current_user
    user = get_current_user()
    
    filter_by = request.args.get('filter', 'all')
    category_id = request.args.get('category')
    
    with get_session() as session:
        # Базовый запрос - только задачи текущего пользователя
        query = select(TaskORM).where(TaskORM.user_id == user.id)
        
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
        
        # Получаем категории для фильтра - только для текущего пользователя
        categories_orm = session.execute(
            select(TaskCategoryORM).where(TaskCategoryORM.user_id == user.id)
        ).scalars().all()
        categories = [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories_orm]
        
        # Статистика - только для текущего пользователя
        stats = {
            'total': session.execute(
                select(func.count(TaskORM.id)).where(TaskORM.user_id == user.id)
            ).scalar() or 0,
            'completed': session.execute(
                select(func.count(TaskORM.id)).where(TaskORM.user_id == user.id, TaskORM.status == 1)
            ).scalar() or 0,
            'pending': session.execute(
                select(func.count(TaskORM.id)).where(TaskORM.user_id == user.id, TaskORM.status == 0)
            ).scalar() or 0,
            'overdue': session.execute(
                select(func.count(TaskORM.id)).where(
                    TaskORM.user_id == user.id,
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




# ==================== НОВАЯ ВЕРСИЯ С РАСПИСАНИЕМ (V2) ====================

@bp.route('/create', methods=['GET', 'POST'])
@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Создание новой задачи с расписанием"""
    from app.auth import get_current_user
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            with get_session() as session:
                now = datetime.now().isoformat()
                
                # Создаем задачу
                task_data = data['task']
                task = TaskORM(
                    user_id=user.id,
                    title=task_data['title'],
                    description=task_data.get('description', ''),
                    importance=task_data.get('importance', 2),
                    category_id=task_data.get('category_id') or None,
                    task_type='calendar_reminder',
                    schedule_config=task_data.get('schedule_config'),
                    status=0,
                    created_at=now,
                    updated_at=now
                )
                session.add(task)
                session.commit()
                
                return jsonify({'success': True, 'task_id': task.id})
        
        except Exception as e:
            print(f"Error creating task: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    # GET - показываем форму
    with get_session() as session:
        # Только категории текущего пользователя
        categories_orm = session.execute(
            select(TaskCategoryORM).where(TaskCategoryORM.user_id == user.id)
        ).scalars().all()
        categories = [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories_orm]
    
    return render_template(
        'tasks/edit_calendar.html',
        task_json='null',
        categories_json=json.dumps(categories)
    )


@bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    """Редактирование задачи"""
    from app.auth import get_current_user
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            with get_session() as session:
                task = session.get(TaskORM, task_id)
                if not task:
                    return jsonify({'error': 'Задача не найдена'}), 404
                
                now = datetime.now().isoformat()
                
                # Обновляем задачу
                task_data = data['task']
                task.title = task_data['title']
                task.description = task_data.get('description', '')
                task.importance = task_data.get('importance', 2)
                task.category_id = task_data.get('category_id') or None
                task.task_type = 'calendar_reminder'
                task.schedule_config = task_data.get('schedule_config')
                task.updated_at = now
                
                session.commit()
                
                return jsonify({'success': True})
        
        except Exception as e:
            print(f"Error updating task: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    # GET - показываем форму
    with get_session() as session:
        task_orm = session.get(TaskORM, task_id)
        if not task_orm or task_orm.user_id != user.id:
            flash('Задача не найдена или доступ запрещен', 'error')
            return redirect(url_for('tasks.index'))
        
        # Преобразуем задачу в JSON
        task_json = json.dumps({
            'id': task_orm.id,
            'title': task_orm.title,
            'description': task_orm.description or '',
            'importance': task_orm.importance,
            'category_id': task_orm.category_id,
            'schedule_config': task_orm.schedule_config or '{}'
        })
        
        # Категории - только для текущего пользователя
        categories_orm = session.execute(
            select(TaskCategoryORM).where(TaskCategoryORM.user_id == user.id)
        ).scalars().all()
        categories = [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories_orm]
    
    return render_template(
        'tasks/edit_calendar.html',
        task_json=task_json,
        categories_json=json.dumps(categories)
    )


@bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id):
    """Удаление задачи"""
    try:
        with get_session() as session:
            task = session.get(TaskORM, task_id)
            if not task:
                return jsonify({'error': 'Задача не найдена'}), 404
            
            session.delete(task)
            session.commit()
            
            return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error deleting task: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/reminder-templates', methods=['GET'])
@login_required
def get_reminder_templates():
    """Получить список шаблонов напоминаний"""
    try:
        task_type = request.args.get('task_type', '')
        category = request.args.get('category', '')
        
        with get_session() as session:
            query = select(ReminderRuleTemplateORM).where(
                ReminderRuleTemplateORM.is_active == True
            )
            
            # Фильтр по категории
            if category:
                query = query.where(ReminderRuleTemplateORM.category == category)
            
            query = query.order_by(ReminderRuleTemplateORM.category, ReminderRuleTemplateORM.id)
            
            templates_orm = session.execute(query).scalars().all()
            
            # Преобразуем в JSON
            templates = []
            for t in templates_orm:
                # Парсим suitable_for_task_types
                suitable_for = []
                if t.suitable_for_task_types:
                    try:
                        suitable_for = json.loads(t.suitable_for_task_types)
                    except:
                        pass
                
                # Фильтр по типу задачи
                if task_type and task_type not in suitable_for:
                    continue
                
                # Парсим правила
                rules = []
                try:
                    rules = json.loads(t.rules_json)
                except:
                    pass
                
                templates.append({
                    'id': t.id,
                    'name': t.name,
                    'description': t.description,
                    'category': t.category,
                    'icon': t.icon,
                    'rules': rules,
                    'suitable_for': suitable_for,
                    'is_system': t.is_system,
                    'usage_count': t.usage_count
                })
            
            return jsonify({
                'success': True,
                'templates': templates
            })
    
    except Exception as e:
        print(f"Error loading templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/reminder-preview', methods=['POST'])
@login_required
def get_reminder_preview():
    """Предпросмотр напоминаний для задачи"""
    try:
        data = request.get_json()
        
        # Создаем временную задачу для предпросмотра
        from datetime import datetime, timedelta
        from app.reminder_generator import ReminderGenerator
        
        task_data = data.get('task', {})
        schedules_data = data.get('schedules', [])
        rules_data = data.get('reminder_rules', [])
        
        # Если нет правил - возвращаем пустой список
        if not rules_data:
            return jsonify({'success': True, 'reminders': []})
        
        # Генерируем предпросмотр
        preview_reminders = []
        now = datetime.now()
        
        # Для каждого расписания
        for schedule in schedules_data:
            day_of_week = schedule['day_of_week']
            start_time = schedule['start_time']
            end_time = schedule.get('end_time')
            
            # Находим ближайшие даты для этого дня недели (следующие 2 недели)
            for days_ahead in range(14):
                check_date = now.date() + timedelta(days=days_ahead)
                
                # Проверяем день недели (1=Пн, 7=Вс)
                if check_date.isoweekday() == day_of_week:
                    # Создаем datetime для начала
                    start_hour, start_min = map(int, start_time.split(':'))
                    event_start = datetime.combine(check_date, datetime.min.time().replace(
                        hour=start_hour, minute=start_min
                    ))
                    
                    event_end = None
                    if end_time:
                        end_hour, end_min = map(int, end_time.split(':'))
                        event_end = datetime.combine(check_date, datetime.min.time().replace(
                            hour=end_hour, minute=end_min
                        ))
                    
                    # Применяем каждое правило
                    for rule in rules_data:
                        rule_obj = type('Rule', (), rule)()  # Создаем объект из словаря
                        
                        # Генерируем напоминания для этого события
                        if rule.get('rule_type') == 'before_start':
                            offset = rule.get('offset_minutes', 0)
                            reminder_time = event_start - timedelta(minutes=offset)
                            if reminder_time > now:
                                preview_reminders.append({
                                    'date': reminder_time.date().isoformat(),
                                    'time': reminder_time.time().strftime('%H:%M'),
                                    'datetime': reminder_time.isoformat(),
                                    'rule_type': rule.get('rule_type'),
                                    'day_name': check_date.strftime('%A'),
                                    'day_of_week': day_of_week
                                })
                        
                        elif rule.get('rule_type') == 'at_start':
                            # В момент начала (offset = 0)
                            if event_start > now:
                                preview_reminders.append({
                                    'date': event_start.date().isoformat(),
                                    'time': event_start.time().strftime('%H:%M'),
                                    'datetime': event_start.isoformat(),
                                    'rule_type': rule.get('rule_type'),
                                    'day_name': check_date.strftime('%A'),
                                    'day_of_week': day_of_week
                                })
                        
                        elif rule.get('rule_type') == 'before_end' and event_end:
                            offset = rule.get('offset_minutes', 0)
                            reminder_time = event_end - timedelta(minutes=offset)
                            if reminder_time > now:
                                preview_reminders.append({
                                    'date': reminder_time.date().isoformat(),
                                    'time': reminder_time.time().strftime('%H:%M'),
                                    'datetime': reminder_time.isoformat(),
                                    'rule_type': rule.get('rule_type'),
                                    'day_name': check_date.strftime('%A'),
                                    'day_of_week': day_of_week
                                })
                        
                        elif rule.get('rule_type') == 'periodic_before':
                            # Периодические напоминания до начала
                            interval = rule.get('interval_minutes', 30)
                            start_from = rule.get('start_from', '16:00')
                            stop_at = rule.get('stop_at', 30)
                            
                            # Парсим start_from
                            if ':' in str(start_from):
                                sh, sm = map(int, start_from.split(':'))
                                current = datetime.combine(check_date, datetime.min.time().replace(hour=sh, minute=sm))
                            else:
                                current = event_start - timedelta(minutes=int(start_from))
                            
                            # Генерируем напоминания
                            stop_time = event_start - timedelta(minutes=int(stop_at))
                            
                            while current <= stop_time and current > now:
                                preview_reminders.append({
                                    'date': current.date().isoformat(),
                                    'time': current.time().strftime('%H:%M'),
                                    'datetime': current.isoformat(),
                                    'rule_type': rule.get('rule_type'),
                                    'day_name': check_date.strftime('%A'),
                                    'day_of_week': day_of_week
                                })
                                current += timedelta(minutes=interval)
                        
                        elif rule.get('rule_type') == 'after_end' and event_end:
                            offset = rule.get('offset_minutes', 0)
                            reminder_time = event_end + timedelta(minutes=offset)
                            if reminder_time > now:
                                preview_reminders.append({
                                    'date': reminder_time.date().isoformat(),
                                    'time': reminder_time.time().strftime('%H:%M'),
                                    'datetime': reminder_time.isoformat(),
                                    'rule_type': rule.get('rule_type'),
                                    'day_name': check_date.strftime('%A'),
                                    'day_of_week': day_of_week
                                })
        
        # Сортируем по времени
        preview_reminders.sort(key=lambda r: r['datetime'])
        
        # Группируем по датам
        reminders_by_date = {}
        for reminder in preview_reminders:
            date_key = reminder['date']
            if date_key not in reminders_by_date:
                reminders_by_date[date_key] = []
            reminders_by_date[date_key].append(reminder)
        
        return jsonify({
            'success': True,
            'total_count': len(preview_reminders),
            'reminders_by_date': reminders_by_date,
            'all_reminders': preview_reminders[:100]  # Первые 100 для списка
        })
    
    except Exception as e:
        print(f"Error generating preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




@bp.route('/save-template', methods=['POST'])
@login_required
def save_user_template():
    """Сохранить пользовательский шаблон"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Название шаблона обязательно'}), 400
        
        rules = data.get('rules', [])
        if not rules:
            return jsonify({'error': 'Добавьте хотя бы одно правило'}), 400
        
        with get_session() as session:
            now = datetime.now().isoformat()
            
            # Определяем для каких типов задач подходит
            task_type = data.get('task_type', 'simple')
            suitable_for = [task_type]
            if task_type == 'recurring_event':
                suitable_for.append('event')
            
            template = ReminderRuleTemplateORM(
                name=name,
                description=data.get('description', f'Пользовательский шаблон'),
                category=data.get('category', 'custom'),
                icon='⭐',  # Иконка для пользовательских шаблонов
                rules_json=json.dumps(rules, ensure_ascii=False),
                suitable_for_task_types=json.dumps(suitable_for),
                is_system=False,
                is_active=True,
                usage_count=0,
                created_by=None,  # TODO: добавить user_id когда будет авторизация
                created_at=now,
                updated_at=now
            )
            
            session.add(template)
            session.commit()
            
            return jsonify({
                'success': True,
                'template_id': template.id,
                'message': f'Шаблон "{name}" успешно сохранен!'
            })
    
    except Exception as e:
        print(f"Error saving template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
