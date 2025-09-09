from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import date, datetime
import webbrowser

from PyQt6.QtCore import Qt, QUrl, QDate, QLocale, QObject, QEvent
from PyQt6.QtGui import QAction, QColor, QBrush, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QToolBar,
    QApplication,
    QLabel,
    QSplitter,
    QHeaderView,
    QTextEdit,
    QFormLayout,
    QDateEdit,
    QDoubleSpinBox,
    QCheckBox,
    QTableWidgetSelectionRange,
    QScrollArea,
)

from ..repository_sa import loan_repo, installment_repo


class MouseWheelEventFilter(QObject):
    """Фильтр событий для отключения колесика мыши в полях ввода."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QDateEdit, QDoubleSpinBox)):
                return True
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self._create_mode = False
        self._last_selected_row = 0
        self._suppress_selection_prompt = False
        self._unsaved_changes = False
        self._current_loan_id = None
        self._mouse_wheel_filter = MouseWheelEventFilter()
        
        self.setWindowTitle("Микрокредиты - Органайзер")
        self.setGeometry(100, 100, 1400, 800)
        
        self._setup_global_styles()
        self._setup_ui()
        self._refresh_data()

    def _setup_global_styles(self):
        """Настройка глобальных стилей приложения."""
        # Устанавливаем стили для всего приложения
        app_style = """
        QMainWindow {
            font-size: 14px;
        }
        QLabel {
            font-size: 14px;
        }
        QPushButton {
            font-size: 14px;
            padding: 10px 16px;
            min-height: 35px;
        }
        QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox {
            font-size: 14px;
            padding: 8px;
            min-height: 30px;
        }
        QTableWidget {
            font-size: 14px;
        }
        QTableWidget::item {
            padding: 12px;
            min-height: 45px;
        }
        QHeaderView::section {
            font-size: 14px;
            padding: 10px;
            font-weight: bold;
        }
        QToolBar {
            font-size: 14px;
        }
        QStatusBar {
            font-size: 14px;
        }
        """
        self.setStyleSheet(app_style)

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        
        # Разделитель для левой и правой панелей
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Левая панель - список кредитов
        left_panel = self._create_loans_panel()
        splitter.addWidget(left_panel)
        
        # Правая панель - детали кредита
        right_panel = self._create_details_panel()
        splitter.addWidget(right_panel)
        
        # Настройка пропорций разделителя
        splitter.setSizes([600, 800])
        
        # Статус бар
        self.status_label = QLabel("Готово")
        self.statusBar().addWidget(self.status_label)

    def _create_loans_panel(self) -> QWidget:
        """Создание левой панели со списком кредитов."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Панель инструментов
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        add_action = QAction("Добавить", self)
        add_action.triggered.connect(self._add_loan)
        toolbar.addAction(add_action)
        
        refresh_action = QAction("Обновить", self)
        refresh_action.triggered.connect(self._refresh_data)
        toolbar.addAction(refresh_action)
        
        layout.addWidget(toolbar)
        
        # Таблица кредитов
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Банк", "Платеж", "Действие", "Взято", "Осталось", "Риск", "Дата"
        ])
        
        # Настройка таблицы
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Обработчики событий
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        layout.addWidget(self.table)
        
        return panel

    def _create_details_panel(self) -> QWidget:
        """Создание правой панели с деталями кредита."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Заголовок
        title_label = QLabel("Детали кредита")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; padding: 5px;")
        layout.addWidget(title_label)
        
        # Скроллируемая область
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Контейнер для полей
        details_widget = QWidget()
        details_layout = QFormLayout(details_widget)
        
        # Поля ввода
        self.org_name_edit = QLineEdit()
        self.org_name_edit.textChanged.connect(self._mark_unsaved)
        self.org_name_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.website_edit = QLineEdit()
        self.website_edit.textChanged.connect(self._mark_unsaved)
        self.website_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.loan_date_edit = QDateEdit()
        self.loan_date_edit.setDate(QDate.currentDate())
        self.loan_date_edit.setCalendarPopup(True)
        self.loan_date_edit.dateChanged.connect(self._mark_unsaved)
        self.loan_date_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.amount_borrowed_edit = QDoubleSpinBox()
        self.amount_borrowed_edit.setRange(0, 999999.99)
        self.amount_borrowed_edit.setDecimals(2)
        self.amount_borrowed_edit.valueChanged.connect(self._mark_unsaved)
        self.amount_borrowed_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDate(QDate.currentDate())
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.dateChanged.connect(self._mark_unsaved)
        self.due_date_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.risky_org_checkbox = QCheckBox("Рискованная организация")
        self.risky_org_checkbox.toggled.connect(self._mark_unsaved)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.textChanged.connect(self._mark_unsaved)
        
        self.payment_methods_edit = QTextEdit()
        self.payment_methods_edit.setMaximumHeight(80)
        self.payment_methods_edit.textChanged.connect(self._mark_unsaved)
        
        # Добавление полей в форму
        details_layout.addRow("Организация:", self.org_name_edit)
        details_layout.addRow("Сайт:", self.website_edit)
        details_layout.addRow("Дата оформления:", self.loan_date_edit)
        details_layout.addRow("Сумма взята:", self.amount_borrowed_edit)
        details_layout.addRow("Дата возврата:", self.due_date_edit)
        details_layout.addRow("", self.risky_org_checkbox)
        details_layout.addRow("Заметки:", self.notes_edit)
        details_layout.addRow("Способы/Комиссии:", self.payment_methods_edit)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self._save_loan)
        self.save_button.setEnabled(False)
        
        self.pay_button = QPushButton("Оплатить")
        self.pay_button.clicked.connect(self._open_payment_site)
        self.pay_button.setEnabled(False)
        
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.pay_button)
        buttons_layout.addStretch()
        
        details_layout.addRow(buttons_layout)
        
        # Разделитель
        separator = QLabel("─" * 50)
        details_layout.addRow(separator)
        
        # График платежей
        installments_label = QLabel("График платежей")
        installments_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        details_layout.addRow(installments_label)
        
        # Кнопка добавления платежа
        add_installment_layout = QHBoxLayout()
        
        self.installment_date_edit = QDateEdit()
        self.installment_date_edit.setDate(QDate.currentDate())
        self.installment_date_edit.setCalendarPopup(True)
        self.installment_date_edit.installEventFilter(self._mouse_wheel_filter)
        
        self.installment_amount_edit = QDoubleSpinBox()
        self.installment_amount_edit.setRange(0, 999999.99)
        self.installment_amount_edit.setDecimals(2)
        self.installment_amount_edit.installEventFilter(self._mouse_wheel_filter)
        
        add_installment_button = QPushButton("+")
        add_installment_button.clicked.connect(self._add_installment)
        add_installment_button.setMaximumWidth(30)
        
        add_installment_layout.addWidget(QLabel("Дата:"))
        add_installment_layout.addWidget(self.installment_date_edit)
        add_installment_layout.addWidget(QLabel("Сумма:"))
        add_installment_layout.addWidget(self.installment_amount_edit)
        add_installment_layout.addWidget(add_installment_button)
        add_installment_layout.addStretch()
        
        details_layout.addRow(add_installment_layout)
        
        # Таблица платежей
        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(4)
        self.installments_table.setHorizontalHeaderLabels([
            "Дата", "Сумма", "Оплачен", "Действие"
        ])
        self.installments_table.setAlternatingRowColors(True)
        self.installments_table.horizontalHeader().setStretchLastSection(True)
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        details_layout.addRow(self.installments_table)
        
        scroll_area.setWidget(details_widget)
        layout.addWidget(scroll_area)
        
        return panel

    def _refresh_data(self):
        """Обновление данных в таблице."""
        try:
            # Получаем все кредиты
            loans = loan_repo.get_all_loans()
            
            # Сортируем по дате ближайшего платежа
            loans.sort(key=lambda x: (
                "9999-12-31" if x["next_date"] is None else x["next_date"],
                x["id"] or 0
            ))
            
            # Заполняем таблицу
            self.table.setRowCount(len(loans))
            
            urgent_count = 0
            for row, loan in enumerate(loans):
                # ID
                self.table.setItem(row, 0, QTableWidgetItem(str(loan["id"] or "")))
                
                # Банк
                self.table.setItem(row, 1, QTableWidgetItem(loan["org_name"] or ""))
                
                # Платеж (дата)
                next_date_str = ""
                if loan["next_date"]:
                    try:
                        next_date = datetime.strptime(loan["next_date"], "%Y-%m-%d").date()
                        next_date_str = next_date.strftime("%d %B %Y")
                        
                        # Проверяем, является ли кредит "горящим"
                        days_left = (next_date - date.today()).days
                        if days_left < 5 and not loan["is_paid"]:
                            urgent_count += 1
                    except ValueError:
                        next_date_str = loan["next_date"]
                
                self.table.setItem(row, 2, QTableWidgetItem(next_date_str))
                
                # Действие
                if loan["is_paid"]:
                    action_button = QPushButton("Погашен")
                    action_button.setStyleSheet("""
                        background-color: #28a745; 
                        color: white; 
                        font-size: 12px;
                        padding: 8px 20px;
                        min-height: 30px;
                        min-width: 100px;
                        border: none;
                        border-radius: 5px;
                    """)
                    action_button.clicked.connect(lambda checked, url=loan["website"]: self._open_payment_site(url))
                else:
                    action_button = QPushButton("Оплатить")
                    action_button.setStyleSheet("""
                        background-color: #007bff; 
                        color: white; 
                        font-size: 12px;
                        padding: 8px 20px;
                        min-height: 30px;
                        min-width: 100px;
                        border: none;
                        border-radius: 5px;
                    """)
                    action_button.clicked.connect(lambda checked, url=loan["website"]: self._open_payment_site(url))
                
                self.table.setCellWidget(row, 3, action_button)
                
                # Взято
                self.table.setItem(row, 4, QTableWidgetItem(f"{loan['amount_borrowed']:.2f}"))
                
                # Осталось
                self.table.setItem(row, 5, QTableWidgetItem(f"{loan['remaining']:.2f}"))
                
                # Риск
                risk_text = "⚠️" if loan["risky_org"] else ""
                self.table.setItem(row, 6, QTableWidgetItem(risk_text))
                
                # Дата (последняя)
                last_date_str = ""
                if loan["last_date"]:
                    try:
                        last_date = datetime.strptime(loan["last_date"], "%Y-%m-%d").date()
                        last_date_str = last_date.strftime("%d %B %Y")
                    except ValueError:
                        last_date_str = loan["last_date"]
                
                self.table.setItem(row, 7, QTableWidgetItem(last_date_str))
                
                # Цветовая индикация строк
                if loan["is_paid"]:
                    # Зеленый для погашенных
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(QBrush(QColor(212, 237, 218)))
                elif loan["next_date"]:
                    try:
                        next_date = datetime.strptime(loan["next_date"], "%Y-%m-%d").date()
                        days_left = (next_date - date.today()).days
                        if days_left < 5:
                            # Красный для "горящих"
                            for col in range(self.table.columnCount()):
                                item = self.table.item(row, col)
                                if item:
                                    item.setBackground(QBrush(QColor(248, 215, 218)))
                        else:
                            # Желтый для обычных
                            for col in range(self.table.columnCount()):
                                item = self.table.item(row, col)
                                if item:
                                    item.setBackground(QBrush(QColor(255, 243, 205)))
                    except ValueError:
                        pass
            
            # Автоподбор ширины колонок
            self.table.resizeColumnsToContents()
            
            # Статус с общими данными
            total_remaining = sum(loan["remaining"] for loan in loans)
            self.status_label.setText(
                f"Горящие (<5 дней): {urgent_count} | Всего кредитов: {len(loans)} | Не оплачено всего: {total_remaining:.2f}"
            )
            
            # Выбираем первую строку, если не в режиме создания
            if not self._create_mode and self.table.rowCount() > 0:
                if not self.table.selectedItems():
                    self._suppress_selection_prompt = True
                    self.table.selectRow(0)
                    self._suppress_selection_prompt = False
                    self._last_selected_row = 0
                    self._update_details_from_selection()
            else:
                self._fill_details(None)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении данных: {e}")

    def _on_selection_changed(self):
        """Обработчик изменения выбора в таблице."""
        if self._suppress_selection_prompt:
            return
            
        if self._unsaved_changes:
            reply = QMessageBox.question(
                self, "Сохранить изменения?",
                "У вас есть несохраненные изменения. Сохранить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._save_loan()
            elif reply == QMessageBox.StandardButton.Cancel:
                # Возвращаемся к предыдущему выбору
                self._suppress_selection_prompt = True
                self.table.selectRow(self._last_selected_row)
                self._suppress_selection_prompt = False
                return
        
        self._update_details_from_selection()

    def _update_details_from_selection(self):
        """Обновление деталей на основе выбранной строки."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self._last_selected_row = current_row
            loan_id = int(self.table.item(current_row, 0).text())
            self._load_loan_details(loan_id)

    def _load_loan_details(self, loan_id: int):
        """Загрузка деталей кредита."""
        try:
            loan = loan_repo.get_loan_by_id(loan_id)
            if loan:
                self._current_loan_id = loan_id
                self._fill_details(loan)
                self._load_installments(loan_id)
            else:
                self._fill_details(None)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке кредита: {e}")

    def _fill_details(self, loan: Optional[dict]):
        """Заполнение полей деталей кредита."""
        if loan is None:
            self.org_name_edit.clear()
            self.website_edit.clear()
            self.loan_date_edit.setDate(QDate.currentDate())
            self.amount_borrowed_edit.setValue(0.0)
            self.due_date_edit.setDate(QDate.currentDate())
            self.risky_org_checkbox.setChecked(False)
            self.notes_edit.clear()
            self.payment_methods_edit.clear()
            self.pay_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self._unsaved_changes = False
        else:
            self.org_name_edit.setText(loan["org_name"] or "")
            self.website_edit.setText(loan["website"] or "")
            
            try:
                loan_date = datetime.strptime(loan["loan_date"], "%Y-%m-%d").date()
                self.loan_date_edit.setDate(QDate(loan_date))
            except ValueError:
                self.loan_date_edit.setDate(QDate.currentDate())
            
            self.amount_borrowed_edit.setValue(loan["amount_borrowed"])
            
            try:
                due_date = datetime.strptime(loan["due_date"], "%Y-%m-%d").date()
                self.due_date_edit.setDate(QDate(due_date))
            except ValueError:
                self.due_date_edit.setDate(QDate.currentDate())
            
            self.risky_org_checkbox.setChecked(loan["risky_org"])
            self.notes_edit.setPlainText(loan["notes"] or "")
            self.payment_methods_edit.setPlainText(loan["payment_methods"] or "")
            
            self.pay_button.setEnabled(bool(loan["website"]))
            self.save_button.setEnabled(True)
            self._unsaved_changes = False

    def _load_installments(self, loan_id: int):
        """Загрузка платежей для кредита."""
        try:
            installments = installment_repo.get_installments_by_loan_id(loan_id)
            
            self.installments_table.setRowCount(len(installments))
            
            for row, inst in enumerate(installments):
                # Дата
                try:
                    inst_date = datetime.strptime(inst["due_date"], "%Y-%m-%d").date()
                    date_str = inst_date.strftime("%d %B %Y")
                except ValueError:
                    date_str = inst["due_date"]
                
                self.installments_table.setItem(row, 0, QTableWidgetItem(date_str))
                
                # Сумма
                self.installments_table.setItem(row, 1, QTableWidgetItem(f"{inst['amount']:.2f}"))
                
                # Оплачен
                paid_text = "Да" if inst["paid"] else "Нет"
                self.installments_table.setItem(row, 2, QTableWidgetItem(paid_text))
                
                # Действие
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(5, 5, 5, 5)
                action_layout.setSpacing(8)
                
                toggle_button = QPushButton("Оплачен" if not inst["paid"] else "Не оплачен")
                toggle_button.setStyleSheet("""
                    background-color: #28a745; 
                    color: white; 
                    font-size: 12px;
                    padding: 6px 16px;
                    min-height: 25px;
                    min-width: 80px;
                    border: none;
                    border-radius: 4px;
                """ if not inst["paid"] else """
                    background-color: #dc3545; 
                    color: white; 
                    font-size: 12px;
                    padding: 6px 16px;
                    min-height: 25px;
                    min-width: 80px;
                    border: none;
                    border-radius: 4px;
                """)
                toggle_button.clicked.connect(lambda checked, inst_id=inst["id"], current_paid=inst["paid"]: self._toggle_installment_paid(inst_id, not current_paid))
                
                delete_button = QPushButton("Удалить")
                delete_button.setStyleSheet("""
                    background-color: #dc3545; 
                    color: white; 
                    font-size: 12px;
                    padding: 6px 16px;
                    min-height: 25px;
                    min-width: 70px;
                    border: none;
                    border-radius: 4px;
                """)
                delete_button.clicked.connect(lambda checked, inst_id=inst["id"]: self._delete_installment(inst_id))
                
                action_layout.addWidget(toggle_button)
                action_layout.addWidget(delete_button)
                
                action_widget = QWidget()
                action_widget.setLayout(action_layout)
                self.installments_table.setCellWidget(row, 3, action_widget)
            
            # Автоподбор высоты таблицы
            self.installments_table.setMaximumHeight(self.installments_table.rowHeight(0) * (len(installments) + 1) + 50)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке платежей: {e}")

    def _add_loan(self):
        """Добавление нового кредита."""
        self._create_mode = True
        self._current_loan_id = None
        self._fill_details(None)
        self.installments_table.setRowCount(0)
        self.save_button.setEnabled(True)
        self._unsaved_changes = False

    def _save_loan(self):
        """Сохранение кредита."""
        try:
            loan_data = {
                "org_name": self.org_name_edit.text().strip(),
                "website": self.website_edit.text().strip(),
                "loan_date": self.loan_date_edit.date().toString("yyyy-MM-dd"),
                "amount_borrowed": self.amount_borrowed_edit.value(),
                "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
                "risky_org": self.risky_org_checkbox.isChecked(),
                "notes": self.notes_edit.toPlainText().strip(),
                "payment_methods": self.payment_methods_edit.toPlainText().strip(),
            }
            
            if not loan_data["org_name"] or not loan_data["website"]:
                QMessageBox.warning(self, "Предупреждение", "Заполните название организации и сайт")
                return
            
            if self._create_mode:
                # Создание нового кредита
                loan_id = loan_repo.create_loan(loan_data)
                self._current_loan_id = loan_id
                self._create_mode = False
                QMessageBox.information(self, "Успех", "Кредит создан")
            else:
                # Обновление существующего кредита
                if loan_repo.update_loan(self._current_loan_id, loan_data):
                    QMessageBox.information(self, "Успех", "Кредит обновлен")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось обновить кредит")
                    return
            
            self._unsaved_changes = False
            self._refresh_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении кредита: {e}")

    def _add_installment(self):
        """Добавление нового платежа."""
        if not self._current_loan_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите или создайте кредит")
            return
        
        try:
            installment_data = {
                "loan_id": self._current_loan_id,
                "due_date": self.installment_date_edit.date().toString("yyyy-MM-dd"),
                "amount": self.installment_amount_edit.value(),
            }
            
            if installment_data["amount"] <= 0:
                QMessageBox.warning(self, "Предупреждение", "Сумма должна быть больше нуля")
                return
            
            installment_repo.create_installment(installment_data)
            QMessageBox.information(self, "Успех", "Платеж добавлен")
            
            # Очищаем поля
            self.installment_date_edit.setDate(QDate.currentDate())
            self.installment_amount_edit.setValue(0.0)
            
            # Обновляем данные
            self._refresh_data()
            if self._current_loan_id:
                self._load_installments(self._current_loan_id)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении платежа: {e}")

    def _toggle_installment_paid(self, installment_id: int, paid: bool):
        """Переключение статуса оплаты платежа."""
        try:
            if installment_repo.toggle_installment_paid(installment_id, paid):
                QMessageBox.information(self, "Успех", "Статус платежа обновлен")
                self._refresh_data()
                if self._current_loan_id:
                    self._load_installments(self._current_loan_id)
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить статус платежа")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении статуса платежа: {e}")

    def _delete_installment(self, installment_id: int):
        """Удаление платежа."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить этот платеж?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if installment_repo.delete_installment(installment_id):
                    QMessageBox.information(self, "Успех", "Платеж удален")
                    self._refresh_data()
                    if self._current_loan_id:
                        self._load_installments(self._current_loan_id)
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить платеж")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении платежа: {e}")

    def _open_payment_site(self, url: Optional[str] = None):
        """Открытие сайта для оплаты."""
        if url is None:
            url = self.website_edit.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Предупреждение", "Сайт не указан")
            return
        
        try:
            # Добавляем протокол, если его нет
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть сайт: {e}")

    def _on_cell_double_clicked(self, row: int, column: int):
        """Обработчик двойного клика по ячейке."""
        if column == 3:  # Кнопка действия
            return
        
        self._update_details_from_selection()

    def _mark_unsaved(self):
        """Отметка о наличии несохраненных изменений."""
        self._unsaved_changes = True
        self.save_button.setEnabled(True)
