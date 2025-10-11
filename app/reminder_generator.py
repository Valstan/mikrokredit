"""
Сервис генерации напоминаний на основе правил
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from sqlalchemy import select

from app.db_sa import get_session
from app.models_sa import (
    TaskORM, TaskScheduleORM, ReminderRuleORM, TaskReminderORM
)


class ReminderGenerator:
    """Генератор напоминаний из правил"""
    
    @staticmethod
    def generate_reminders_for_task(task_id: int, days_ahead: int = 1) -> int:
        """
        Генерирует напоминания для задачи на следующие N дней
        
        Args:
            task_id: ID задачи
            days_ahead: На сколько дней вперед генерировать (по умолчанию 1 день)
            
        Returns:
            Количество созданных напоминаний
        """
        with get_session() as session:
            task = session.get(TaskORM, task_id)
            if not task:
                return 0
            
            # Удаляем старые несработавшие напоминания (будущие)
            now = datetime.now().isoformat()
            old_reminders = session.execute(
                select(TaskReminderORM).where(
                    TaskReminderORM.task_id == task_id,
                    TaskReminderORM.sent == False,
                    TaskReminderORM.reminder_time >= now
                )
            ).scalars().all()
            
            for reminder in old_reminders:
                session.delete(reminder)
            
            session.commit()
            
            # Генерируем новые напоминания
            count = 0
            
            if task.task_type == 'simple':
                # Для простой задачи с дедлайном
                count = ReminderGenerator._generate_simple_task_reminders(session, task)
            
            elif task.task_type in ['event', 'recurring_event']:
                # Для событий с расписанием
                count = ReminderGenerator._generate_event_reminders(
                    session, task, days_ahead
                )
            
            session.commit()
            
            return count
    
    @staticmethod
    def _generate_simple_task_reminders(session, task: TaskORM) -> int:
        """Генерация напоминаний для простой задачи"""
        if not task.due_date:
            return 0
        
        count = 0
        due_datetime = datetime.fromisoformat(task.due_date)
        
        # Получаем правила
        rules = session.execute(
            select(ReminderRuleORM).where(
                ReminderRuleORM.task_id == task.id,
                ReminderRuleORM.is_active == True
            ).order_by(ReminderRuleORM.order_index)
        ).scalars().all()
        
        for rule in rules:
            reminders = ReminderGenerator._apply_rule_to_datetime(
                rule, due_datetime, None
            )
            
            for reminder_time in reminders:
                if reminder_time > datetime.now():
                    reminder = TaskReminderORM(
                        task_id=task.id,
                        reminder_time=reminder_time.isoformat(),
                        sent=False,
                        created_at=datetime.now().isoformat()
                    )
                    session.add(reminder)
                    count += 1
        
        return count
    
    @staticmethod
    def _generate_event_reminders(session, task: TaskORM, days_ahead: int) -> int:
        """Генерация напоминаний для событий с расписанием"""
        count = 0
        
        # Проверяем приостановку
        if task.is_paused and task.paused_until:
            paused_until = date.fromisoformat(task.paused_until)
            if date.today() < paused_until:
                return 0  # Задача приостановлена
        
        # Получаем расписание
        schedules = session.execute(
            select(TaskScheduleORM).where(
                TaskScheduleORM.task_id == task.id,
                    TaskScheduleORM.is_active == True
            )
        ).scalars().all()
        
        if not schedules:
            return 0
        
        # Получаем правила
        rules = session.execute(
            select(ReminderRuleORM).where(
                ReminderRuleORM.task_id == task.id,
                ReminderRuleORM.is_active == True
            ).order_by(ReminderRuleORM.order_index)
        ).scalars().all()
        
        if not rules:
            return 0
        
        # Генерируем для каждого дня
        today = date.today()
        for day_offset in range(days_ahead):
            current_date = today + timedelta(days=day_offset)
            day_of_week = current_date.isoweekday()  # 1=Пн, 7=Вс
            
            # Находим расписание для этого дня
            schedule = None
            for s in schedules:
                if s.day_of_week == day_of_week:
                    schedule = s
                    break
            
            if not schedule:
                continue
            
            # Создаем datetime для начала и конца события
            start_datetime = ReminderGenerator._combine_date_time(
                current_date, schedule.start_time
            )
            end_datetime = ReminderGenerator._combine_date_time(
                current_date, schedule.end_time
            ) if schedule.end_time else None
            
            # Применяем правила
            for rule in rules:
                reminders = ReminderGenerator._apply_rule_to_datetime(
                    rule, start_datetime, end_datetime
                )
                
                for reminder_time in reminders:
                    if reminder_time > datetime.now():
                        reminder = TaskReminderORM(
                            task_id=task.id,
                            reminder_time=reminder_time.isoformat(),
                            sent=False,
                            created_at=datetime.now().isoformat()
                        )
                        session.add(reminder)
                        count += 1
        
        return count
    
    @staticmethod
    def _apply_rule_to_datetime(
        rule: ReminderRuleORM,
        start_datetime: datetime,
        end_datetime: datetime = None
    ) -> List[datetime]:
        """
        Применяет правило к конкретному времени события
        
        Returns:
            Список моментов времени для напоминаний
        """
        reminders = []
        
        if rule.rule_type == 'before_start' or rule.rule_type == 'at_start':
            # За X минут до начала (или в момент начала если offset = 0)
            offset = rule.offset_minutes if rule.offset_minutes is not None else 0
            reminder_time = start_datetime - timedelta(minutes=offset)
            reminders.append(reminder_time)
        
        elif rule.rule_type == 'before_end':
            # За X минут до конца
            if end_datetime and rule.offset_minutes:
                reminder_time = end_datetime - timedelta(minutes=rule.offset_minutes)
                reminders.append(reminder_time)
        
        elif rule.rule_type == 'periodic_before':
            # Периодически до начала
            reminders = ReminderGenerator._generate_periodic_before(
                rule, start_datetime
            )
        
        elif rule.rule_type == 'periodic_during':
            # Периодически во время события
            if end_datetime and rule.interval_minutes:
                current = start_datetime
                while current < end_datetime:
                    if current >= datetime.now():
                        reminders.append(current)
                    current += timedelta(minutes=rule.interval_minutes)
        
        elif rule.rule_type == 'after_end':
            # После окончания
            if end_datetime and rule.offset_minutes:
                reminder_time = end_datetime + timedelta(minutes=rule.offset_minutes)
                reminders.append(reminder_time)
        
        return reminders
    
    @staticmethod
    def _generate_periodic_before(
        rule: ReminderRuleORM,
        start_datetime: datetime
    ) -> List[datetime]:
        """
        Генерирует периодические напоминания до начала
        
        Примеры:
        - start_from="16:00", stop_at="30" -> с 16:00 до 30 минут до начала
        - start_from="240", stop_at="30" -> с 240 минут до начала до 30 минут до начала
        """
        reminders = []
        
        if not rule.interval_minutes or not rule.start_from or not rule.stop_at:
            return reminders
        
        # Определяем начальную точку
        if ':' in rule.start_from:
            # Фиксированное время (например, "16:00")
            start_time = datetime.strptime(rule.start_from, '%H:%M').time()
            start_point = datetime.combine(start_datetime.date(), start_time)
        else:
            # Минуты до начала (например, "240")
            minutes_before = int(rule.start_from)
            start_point = start_datetime - timedelta(minutes=minutes_before)
        
        # Определяем конечную точку (минуты до начала)
        stop_minutes = int(rule.stop_at)
        end_point = start_datetime - timedelta(minutes=stop_minutes)
        
        # Генерируем напоминания с интервалом
        current = start_point
        while current <= end_point:
            if current >= datetime.now():
                reminders.append(current)
            current += timedelta(minutes=rule.interval_minutes)
        
        return reminders
    
    @staticmethod
    def _combine_date_time(d: date, time_str: str) -> datetime:
        """Объединяет дату и время (HH:MM) в datetime"""
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        return datetime.combine(d, time_obj)
    
    @staticmethod
    def regenerate_all_tasks_reminders(days_ahead: int = 1) -> Dict[str, int]:
        """
        Регенерирует напоминания для всех активных задач
        
        Запускать раз в день через cron
        """
        with get_session() as session:
            # Получаем все активные задачи (не выполненные)
            tasks = session.execute(
                select(TaskORM).where(TaskORM.status == 0)
            ).scalars().all()
            
            total_reminders = 0
            tasks_processed = 0
            
            for task in tasks:
                count = ReminderGenerator.generate_reminders_for_task(
                    task.id, days_ahead
                )
                total_reminders += count
                tasks_processed += 1
            
            return {
                'tasks_processed': tasks_processed,
                'reminders_created': total_reminders
            }


# Вспомогательная функция для использования после сохранения задачи
def regenerate_task_reminders(task_id: int) -> int:
    """
    Удобная функция для вызова из views после сохранения задачи
    """
    return ReminderGenerator.generate_reminders_for_task(task_id)

