from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, Float, Boolean, ForeignKey, Sequence
from typing import List, Optional


class Base(DeclarativeBase):
    pass


class LoanORM(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, Sequence('loans_id_seq'), primary_key=True, autoincrement=True)
    website: Mapped[str] = mapped_column(String, nullable=False)
    loan_date: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM-DD
    amount_borrowed: Mapped[float] = mapped_column(Float, nullable=False)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    risky_org: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_methods: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reminded_pre_due: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    org_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Новые поля v2
    loan_type: Mapped[Optional[str]] = mapped_column(String(50), default="single", nullable=True)  # single/installment
    category: Mapped[Optional[str]] = mapped_column(String(50), default="microloan", nullable=True)  # microloan/installment/credit_card
    interest_rate: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)  # Процентная ставка

    installments: Mapped[List["InstallmentORM"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan"
    )


class InstallmentORM(Base):
    __tablename__ = "installments"

    id: Mapped[int] = mapped_column(Integer, Sequence('installments_id_seq'), primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    paid_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    loan: Mapped[LoanORM] = relationship(back_populates="installments")


# ==================== ОРГАНАЙЗЕР ЗАДАЧ ====================

class TaskCategoryORM(Base):
    """Категории задач"""
    __tablename__ = "task_categories"

    id: Mapped[int] = mapped_column(Integer, Sequence('task_categories_id_seq'), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#3498db")
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    tasks: Mapped[List["TaskORM"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class TaskORM(Base):
    """Задачи"""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, Sequence('tasks_id_seq'), primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Статус: 0 = Не выполнено, 1 = Выполнено
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Важность: 1 = Важная, 2 = Нужная, 3 = Хотелось бы
    importance: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    
    # Даты
    due_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # YYYY-MM-DD HH:MM
    completed_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    
    # Категория
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True)
    
    # Повтор задачи
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON с правилами повтора
    
    # Новые поля для гибких расписаний
    task_type: Mapped[str] = mapped_column(String(50), default="simple", nullable=False)  # simple, event, recurring_event, calendar_reminder
    has_duration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON для календарного планировщика
    
    # Приостановка
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paused_until: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # YYYY-MM-DD
    
    category: Mapped[Optional[TaskCategoryORM]] = relationship(back_populates="tasks")
    reminders: Mapped[List["TaskReminderORM"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    subtasks: Mapped[List["SubtaskORM"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    schedules: Mapped[List["TaskScheduleORM"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    reminder_rules: Mapped[List["ReminderRuleORM"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class SubtaskORM(Base):
    """Подзадачи"""
    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(Integer, Sequence('subtasks_id_seq'), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped[TaskORM] = relationship(back_populates="subtasks")


class TaskReminderORM(Base):
    """Напоминания для задач"""
    __tablename__ = "task_reminders"

    id: Mapped[int] = mapped_column(Integer, Sequence('task_reminders_id_seq'), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    # Время напоминания
    reminder_time: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM-DD HH:MM:SS
    
    # Отправлено ли
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # ID сообщения в Telegram (для callback)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Пользователь отреагировал на напоминание
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped[TaskORM] = relationship(back_populates="reminders")


class ReminderTemplateORM(Base):
    """Старые шаблоны напоминаний (устаревшая таблица)"""
    __tablename__ = "reminder_templates"

    id: Mapped[int] = mapped_column(Integer, Sequence('reminder_templates_id_seq'), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # JSON с правилами: {"type": "before", "intervals": [1440, 60, 0]} - за 1 день, 1 час, в момент
    rules: Mapped[str] = mapped_column(Text, nullable=False)


class ReminderRuleTemplateORM(Base):
    """Новые шаблоны правил напоминаний"""
    __tablename__ = "reminder_rule_templates"
    
    id: Mapped[int] = mapped_column(Integer, Sequence('reminder_rule_templates_id_seq'), primary_key=True, autoincrement=True)
    
    # Основная информация
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # JSON с массивом правил
    rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Для каких типов задач подходит
    # suitable_for_task_types будет храниться как JSON строка
    suitable_for_task_types: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Метаданные
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class TaskScheduleORM(Base):
    """Расписание для задачи (когда задача происходит)"""
    __tablename__ = "task_schedules"

    id: Mapped[int] = mapped_column(Integer, Sequence('task_schedules_id_seq'), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    # День недели (1=Понедельник, 2=Вторник, ..., 7=Воскресенье)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Время начала (HH:MM формат)
    start_time: Mapped[str] = mapped_column(String, nullable=False)
    
    # Время окончания (HH:MM формат) - для событий с длительностью
    end_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Активно ли это расписание
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Метаданные
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped[TaskORM] = relationship(back_populates="schedules")


class ReminderRuleORM(Base):
    """Правила напоминаний для задачи"""
    __tablename__ = "reminder_rules"

    id: Mapped[int] = mapped_column(Integer, Sequence('reminder_rules_id_seq'), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    # Тип правила
    # 'before_start' - За X минут до начала (одноразово)
    # 'before_end' - За X минут до конца (одноразово)
    # 'periodic_before' - Периодически до начала
    # 'periodic_during' - Периодически во время события
    # 'after_end' - После окончания
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Для before_start/before_end: минуты до события
    offset_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Для periodic: интервал в минутах
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Для periodic_before: с какого времени начинать (HH:MM или минуты до начала)
    start_from: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Для periodic_before: до какого времени (обычно до начала события)
    stop_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Активно ли правило
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Порядок отображения
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Описание правила (для отображения)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Метаданные
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped[TaskORM] = relationship(back_populates="reminder_rules")
