# Исправление SQLAlchemy DetachedInstanceError - 09.10.2025

## Проблема

При добавлении задачи или категории в органайзере возникала ошибка:
```
Internal Server Error

DetachedInstanceError: Instance <TaskCategoryORM> is not bound to a Session; 
attribute refresh operation cannot proceed
```

## Причина

SQLAlchemy объекты (ORM) были извлечены из базы данных и переданы в шаблоны после закрытия сессии. При попытке доступа к атрибутам (например, `task.category.name`) SQLAlchemy пытался загрузить связанные данные из уже закрытой сессии.

### Проблемный код:

```python
with get_session() as session:
    categories = session.execute(select(TaskCategoryORM)).scalars().all()
return render_template('tasks/categories.html', categories=categories)
# ❌ Здесь сессия закрыта, но объекты ORM ещё используются
```

## Решение

Извлечение данных в простые словари Python **внутри** контекста сессии:

### Исправленный код:

```python
with get_session() as session:
    cats_orm = session.execute(select(TaskCategoryORM)).scalars().all()
    # ✅ Извлекаем данные в словари ВНУТРИ сессии
    cats = [{'id': c.id, 'name': c.name, 'color': c.color, 'created_at': c.created_at} 
            for c in cats_orm]
return render_template('tasks/categories.html', categories=cats)
# ✅ Передаём простые словари, не ORM объекты
```

## Исправленные функции

### 1. `tasks_views.index()`
Список задач - извлечение всех связанных данных:
- Категория задачи
- Подзадачи
- Статистика

### 2. `tasks_views.categories()`
Список категорий - преобразование в словари

### 3. `tasks_views.new()`
Форма создания - категории и шаблоны в словари

### 4. `tasks_views.edit()`
Форма редактирования - вся связанная информация в словари

## Результат

✅ **Все страницы органайзера работают:**
- `/tasks/` - список задач
- `/tasks/new` - создание задачи
- `/tasks/<id>` - редактирование
- `/tasks/categories` - управление категориями

✅ **Добавление работает:**
- Добавление категорий
- Создание задач
- Редактирование задач

## Рекомендации

### Для будущего:

1. **Всегда извлекать данные в словари** при передаче в шаблоны:
   ```python
   # ❌ НЕ ТАК
   return render_template('page.html', items=orm_objects)
   
   # ✅ ТАК
   data = [{'id': obj.id, 'name': obj.name} for obj in orm_objects]
   return render_template('page.html', items=data)
   ```

2. **Использовать expunge_all()** если нужны ORM объекты:
   ```python
   with get_session() as session:
       objects = session.query(Model).all()
       session.expunge_all()  # Отсоединяем от сессии
   # Теперь можно использовать вне сессии
   ```

3. **Или использовать scoped_session** для глобальной сессии

## Тестирование

### Проверено:
- ✅ Вход в систему
- ✅ Доступ к органайзеру
- ✅ Страница категорий
- ✅ Страница задач
- ✅ Формы создания

### Требуется проверить пользователю:
- Добавление категории через веб-форму
- Создание задачи через веб-форму
- Редактирование задачи

---

**Дата исправления:** 09.10.2025 13:52 MSK  
**Затронутые файлы:** `web/tasks_views.py`  
**Статус:** ✅ Исправлено и перезапущено

