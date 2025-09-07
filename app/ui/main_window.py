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

from ..models import Loan
from ..repository import (
    get_all_loans,
    add_loan,
    update_loan,
    delete_loan,
    get_next_payment_for_loan,
    list_installments,
    add_installment,
    delete_installment,
    mark_installment_paid,
    update_loan_paid_status_if_complete,
    get_installments_total,
    recalc_loan_amount_due,
    get_installments_unpaid_total,
    get_last_installment_date,
)


HEADERS = [
    "ID",
    "Банк",
    "Платеж (дата)",
    "Платеж",
    "Действие",
    "Взято",
    "Осталось",
    "Дата",
    "Риск",
]


class _NoWheelFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MikroKredit Organizer")
        self.resize(1300, 700)

        self._no_wheel = _NoWheelFilter(self)
        self._dirty: bool = False
        self._loading_details: bool = False
        self._suppress_selection_prompt: bool = False
        self._last_selected_row: int = -1

        # Toolbar
        toolbar = QToolBar("Главное меню", self)
        self.addToolBar(toolbar)

        action_add = QAction("Добавить", self)
        action_add.triggered.connect(self.on_new)
        toolbar.addAction(action_add)

        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self.on_delete)
        toolbar.addAction(action_delete)

        # Left: filter + table
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Фильтр по сайту/названию/заметкам...")
        self.filter_input.textChanged.connect(self.refresh)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.filter_input)
        left_layout.addWidget(self.table)

        # Right: editable details of selected loan
        self.edit_org = QLineEdit(); self.edit_org.textChanged.connect(self._mark_dirty)
        self.edit_site = QLineEdit(); self.edit_site.textChanged.connect(self._mark_dirty)
        self.edit_loan_date = QDateEdit(); self.edit_loan_date.setCalendarPopup(True); self.edit_loan_date.setDisplayFormat("d MMMM yyyy"); self.edit_loan_date.installEventFilter(self._no_wheel); self.edit_loan_date.dateChanged.connect(self._mark_dirty)
        self.edit_due_date = QDateEdit(); self.edit_due_date.setCalendarPopup(True); self.edit_due_date.setDisplayFormat("d MMMM yyyy"); self.edit_due_date.installEventFilter(self._no_wheel); self.edit_due_date.dateChanged.connect(self._mark_dirty)
        self.edit_amount_borrowed = QDoubleSpinBox(); self.edit_amount_borrowed.setDecimals(2); self.edit_amount_borrowed.setMaximum(1_000_000_000); self.edit_amount_borrowed.installEventFilter(self._no_wheel); self.edit_amount_borrowed.valueChanged.connect(self._mark_dirty)
        self.edit_amount_due = QDoubleSpinBox(); self.edit_amount_due.setDecimals(2); self.edit_amount_due.setMaximum(1_000_000_000); self.edit_amount_due.installEventFilter(self._no_wheel); self.edit_amount_due.valueChanged.connect(self._mark_dirty)
        self.edit_risky = QCheckBox("Рискованная организация (скрытые услуги)"); self.edit_risky.toggled.connect(self._mark_dirty)
        self.edit_notes = QTextEdit(); self.edit_notes.textChanged.connect(self._mark_dirty)
        self.edit_payment_methods = QTextEdit(); self.edit_payment_methods.textChanged.connect(self._mark_dirty)

        self.btn_open_site = QPushButton("Открыть сайт")
        self.btn_open_site.clicked.connect(self._open_selected_website)

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.on_save)

        details_form = QFormLayout()
        details_form.addRow("Организация", self.edit_org)
        details_form.addRow("Сайт", self.edit_site)
        details_form.addRow("", self.btn_open_site)
        details_form.addRow("Дата оформления", self.edit_loan_date)
        details_form.addRow("Дата возврата", self.edit_due_date)
        details_form.addRow("Сумма взята", self.edit_amount_borrowed)
        details_form.addRow("Сумма к возврату", self.edit_amount_due)

        # Inline installments controls (below 'Сумма к возврату')
        self.inst_date = QDateEdit(); self.inst_date.setCalendarPopup(True); self.inst_date.setDisplayFormat("d MMMM yyyy"); self.inst_date.setDate(QDate.currentDate()); self.inst_date.installEventFilter(self._no_wheel)
        self.inst_amount = QDoubleSpinBox(); self.inst_amount.setDecimals(2); self.inst_amount.setMaximum(1_000_000_000); self.inst_amount.installEventFilter(self._no_wheel)
        self.btn_inst_add = QPushButton("+")
        self.btn_inst_add.clicked.connect(self._on_inst_add)
        inst_controls = QHBoxLayout()
        inst_controls.addWidget(self.inst_date)
        inst_controls.addWidget(self.inst_amount)
        inst_controls.addWidget(self.btn_inst_add)
        inst_controls_widget = QWidget(); inst_controls_widget.setLayout(inst_controls)
        details_form.addRow("График платежей", inst_controls_widget)

        # Installments table and actions
        self.inst_table = QTableWidget(0, 5)
        self.inst_table.setHorizontalHeaderLabels(["Дата", "Сумма", "Оплачен", "Дата оплаты", "ID"])
        self.inst_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inst_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.inst_table.setAlternatingRowColors(True)
        self.inst_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Disable inner scrollbars; use outer scroll area instead
        self.inst_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inst_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.btn_inst_toggle = QPushButton("Оплачен/Не оплачен")
        self.btn_inst_toggle.clicked.connect(self._on_inst_toggle)
        self.btn_inst_delete = QPushButton("Удалить платеж")
        self.btn_inst_delete.clicked.connect(self._on_inst_delete)
        inst_action_row = QHBoxLayout()
        inst_action_row.addWidget(self.btn_inst_toggle)
        inst_action_row.addWidget(self.btn_inst_delete)
        inst_actions_widget = QWidget(); inst_actions_widget.setLayout(inst_action_row)

        details_form.addRow("Список платежей", self.inst_table)
        details_form.addRow("", inst_actions_widget)

        details_form.addRow("Рискованная", self.edit_risky)
        details_form.addRow("Заметки", self.edit_notes)
        details_form.addRow("Способы/Комиссии", self.edit_payment_methods)
        details_form.addRow("", self.btn_save)

        self.details_panel = QWidget()
        self.details_panel.setLayout(details_form)

        # Scroll area for right side
        right_scroll = QScrollArea()
        right_scroll.setWidget(self.details_panel)
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Splitter
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)

        # Selection change updates details
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self._create_mode: bool = False
        self.refresh()

    def _on_selection_changed(self) -> None:
        if self._suppress_selection_prompt:
            return
        new_row = self.table.currentRow()
        if new_row < 0:
            self._update_details_from_selection()
            return
        if self._dirty:
            res = QMessageBox.question(
                self,
                "Сохранить изменения?",
                "У вас есть несохраненные изменения. Сохранить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if res == QMessageBox.StandardButton.Cancel:
                # revert selection
                self._suppress_selection_prompt = True
                if 0 <= self._last_selected_row < self.table.rowCount():
                    self.table.selectRow(self._last_selected_row)
                self._suppress_selection_prompt = False
                return
            elif res == QMessageBox.StandardButton.Yes:
                self.on_save()
        self._last_selected_row = new_row
        self._update_details_from_selection()

    def _mark_dirty(self) -> None:
        if self._loading_details:
            return
        self._dirty = True

    def current_selected_id(self) -> Optional[int]:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        try:
            return int(id_item.text())
        except Exception:
            return None

    def on_new(self) -> None:
        self._create_mode = True
        self.table.clearSelection()
        self._fill_details(None)
        self.edit_org.setFocus()
        self._dirty = False

    def on_save(self) -> None:
        # Validate inputs
        org = self.edit_org.text().strip()
        site = self.edit_site.text().strip()
        if not org:
            QMessageBox.warning(self, "Ошибка", "Укажите название организации")
            return
        if not site:
            QMessageBox.warning(self, "Ошибка", "Укажите сайт организации")
            return
        if self.edit_amount_borrowed.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма взята должна быть больше нуля")
            return
        if self.edit_due_date.date() < self.edit_loan_date.date():
            QMessageBox.warning(self, "Ошибка", "Дата возврата не может быть раньше даты оформления")
            return

        loan_date_iso = self.edit_loan_date.date().toString("yyyy-MM-dd")
        due_date_iso = self.edit_due_date.date().toString("yyyy-MM-dd")
        selected_id = self.current_selected_id()

        if self._create_mode or selected_id is None:
            loan = Loan(
                id=None,
                website=site,
                loan_date=loan_date_iso,
                amount_borrowed=float(self.edit_amount_borrowed.value()),
                amount_due=float(self.edit_amount_due.value()),
                due_date=due_date_iso,
                risky_org=self.edit_risky.isChecked(),
                notes=self.edit_notes.toPlainText().strip(),
                payment_methods=self.edit_payment_methods.toPlainText().strip(),
                reminded_pre_due=False,
                created_at="",
                is_paid=False,
                org_name=org,
            )
            new_id = add_loan(loan)
            recalc_loan_amount_due(new_id)
            update_loan_paid_status_if_complete(new_id)
            self._create_mode = False
            self._dirty = False
            self.refresh()
            self._focus_row_by_id(new_id)
        else:
            # derive paid flag from installments
            derived_paid = (get_installments_unpaid_total(selected_id) == 0)
            loan = Loan(
                id=selected_id,
                website=site,
                loan_date=loan_date_iso,
                amount_borrowed=float(self.edit_amount_borrowed.value()),
                amount_due=float(self.edit_amount_due.value()),
                due_date=due_date_iso,
                risky_org=self.edit_risky.isChecked(),
                notes=self.edit_notes.toPlainText().strip(),
                payment_methods=self.edit_payment_methods.toPlainText().strip(),
                reminded_pre_due=False,
                created_at="",
                is_paid=derived_paid,
                org_name=org,
            )
            update_loan(loan)
            recalc_loan_amount_due(selected_id)
            update_loan_paid_status_if_complete(selected_id)
            self._dirty = False
            self.refresh()
            self._focus_row_by_id(selected_id)

    def on_delete(self) -> None:
        loan_id = self.current_selected_id()
        if loan_id is None:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления")
            return
        if QMessageBox.question(self, "Подтвердите", "Удалить выбранную запись?") == QMessageBox.StandardButton.Yes:
            delete_loan(loan_id)
            self.refresh()

    def _find_loan_by_id(self, loan_id: int) -> Optional[Loan]:
        for l in get_all_loans():
            if l.id == loan_id:
                return l
        return None

    def _format_date(self, iso: str) -> str:
        try:
            y, m, d = map(int, iso.split("-"))
            qd = QDate(y, m, d)
            return QLocale().toString(qd, "d MMMM yyyy")
        except Exception:
            return iso

    def refresh(self) -> None:
        all_loans = get_all_loans()
        needle = self.filter_input.text().strip().lower()
        if needle:
            loans = [
                l for l in all_loans
                if needle in (l.website or "").lower() or needle in (l.notes or "").lower() or needle in (l.org_name or "").lower()
            ]
        else:
            loans = all_loans

        # Build enriched data with derived paid status
        enriched: List[Tuple[Loan, Optional[str], Optional[float], float, float, Optional[str], bool]] = []
        for l in loans:
            unpaid_total = get_installments_unpaid_total(l.id) if l.id is not None else l.amount_due
            derived_paid = (unpaid_total == 0)
            if derived_paid:
                next_date = None
                next_amount = None
            else:
                nxt = get_next_payment_for_loan(l)
                next_date = nxt[0] if nxt else None
                next_amount = nxt[1] if nxt else None
            total_due = get_installments_total(l.id) if l.id is not None else l.amount_due
            last_date = get_last_installment_date(l.id) if l.id is not None else l.due_date
            enriched.append((l, next_date, next_amount, total_due, unpaid_total, last_date, derived_paid))
        enriched.sort(key=lambda x: ("9999-12-31" if x[1] is None else x[1], x[0].id or 0))

        self.table.setRowCount(0)
        urgent_count = 0
        for loan, next_date_iso, next_amount, total_due, unpaid_total, last_date_iso, derived_paid in enriched:
            color = None
            if derived_paid:
                color = QColor(204, 255, 204)
            else:
                if next_date_iso is not None:
                    days_left = self._days_until(next_date_iso)
                    if days_left < 5:
                        color = QColor(255, 204, 204)
                        urgent_count += 1
                    else:
                        color = QColor(255, 255, 204)
                else:
                    color = QColor(255, 255, 204)

            self._append_row(loan, next_date_iso, next_amount, total_due, unpaid_total, last_date_iso, derived_paid, color)

        # Auto-fit columns
        self.table.resizeColumnsToContents()

        self.status_label.setText(f"Горящие (<5 дней): {urgent_count} | Всего кредитов: {len(all_loans)}")

        if not self._create_mode:
            if self.table.rowCount() > 0 and not self.table.selectedItems():
                self._suppress_selection_prompt = True
                self.table.selectRow(0)
                self._suppress_selection_prompt = False
                self._last_selected_row = 0
                self._update_details_from_selection()
        else:
            self._fill_details(None)

    def _append_row(self, loan: Loan, next_date_iso: Optional[str], next_amount: Optional[float], total_due: float, unpaid_total: float, last_date_iso: Optional[str], derived_paid: bool, color: Optional['QColor']) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        # ID
        id_item = QTableWidgetItem(str(loan.id) if loan.id is not None else "")
        self._apply_item(id_item, color)
        self.table.setItem(row, 0, id_item)

        # Bank
        org_item = QTableWidgetItem(loan.org_name or "")
        self._apply_item(org_item, color)
        self.table.setItem(row, 1, org_item)

        # Next date (formatted)
        next_date_text = self._format_date(next_date_iso) if next_date_iso else ""
        next_date_item = QTableWidgetItem(next_date_text)
        self._apply_item(next_date_item, color)
        self.table.setItem(row, 2, next_date_item)

        # Next amount (Платеж)
        next_amount_item = QTableWidgetItem(f"{next_amount:.2f}" if next_amount is not None else "")
        next_amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._apply_item(next_amount_item, color)
        self.table.setItem(row, 3, next_amount_item)

        # Action button
        btn = QPushButton("Погашен" if derived_paid else "Оплатить")
        if derived_paid:
            btn.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; padding: 4px 8px; }")
        else:
            btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 4px 8px; }")
        btn.clicked.connect(lambda _, l=loan: self._open_loan_website(l))
        self.table.setCellWidget(row, 4, btn)

        # Amount borrowed (Взято)
        borrowed_item = QTableWidgetItem(f"{loan.amount_borrowed:.2f}")
        borrowed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._apply_item(borrowed_item, color)
        self.table.setItem(row, 5, borrowed_item)

        # Remaining unpaid (Осталось)
        remaining_item = QTableWidgetItem(f"{unpaid_total:.2f}")
        remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._apply_item(remaining_item, color)
        self.table.setItem(row, 6, remaining_item)

        # Last date (Дата)
        last_date_text = self._format_date(last_date_iso) if last_date_iso else ""
        last_date_item = QTableWidgetItem(last_date_text)
        self._apply_item(last_date_item, color)
        self.table.setItem(row, 7, last_date_item)

        # Risk
        risky_item = QTableWidgetItem("Да" if loan.risky_org else "Нет")
        self._apply_item(risky_item, color)
        self.table.setItem(row, 8, risky_item)

    def _open_loan_website(self, loan: Loan) -> None:
        url = (loan.website or "").strip()
        if not url:
            QMessageBox.information(self, "Открыть сайт", "В этом кредите не указан сайт организации")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        qurl = QUrl(url)
        if not qurl.isValid():
            QMessageBox.warning(self, "Открыть сайт", f"Некорректная ссылка: {url}")
            return
        ok = QDesktopServices.openUrl(qurl)
        if not ok:
            try:
                webbrowser.open(url)
            except Exception as e:
                QMessageBox.warning(self, "Открыть сайт", f"Не удалось открыть ссылку: {e}")

    def _apply_item(self, item: QTableWidgetItem, color: Optional['QColor']) -> None:
        if color is not None:
            item.setBackground(QBrush(color))

    @staticmethod
    def _days_until(date_iso: str) -> int:
        try:
            y, m, d = map(int, date_iso.split("-"))
            target = date(y, m, d)
            return (target - date.today()).days
        except Exception:
            return 0

    def _focus_row_by_id(self, loan_id: int) -> None:
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.text() == str(loan_id):
                self._suppress_selection_prompt = True
                self.table.selectRow(r)
                self._suppress_selection_prompt = False
                self.table.scrollToItem(item)
                self._last_selected_row = r
                break

    def _update_details_from_selection(self) -> None:
        if self._create_mode:
            return
        loan_id = self.current_selected_id()
        if loan_id is None:
            self._fill_details(None)
            return
        loan = self._find_loan_by_id(loan_id)
        self._fill_details(loan)

    def _open_selected_website(self) -> None:
        loan_id = self.current_selected_id()
        if loan_id is None:
            return
        loan = self._find_loan_by_id(loan_id)
        if loan is None:
            return
        self._open_loan_website(loan)

    def _fill_details(self, loan: Optional[Loan]) -> None:
        self._loading_details = True
        # Fill general fields
        if loan is None:
            today = QDate.currentDate()
            self.edit_org.setText("")
            self.edit_site.setText("")
            self.edit_loan_date.setDate(today)
            self.edit_due_date.setDate(today)
            self.edit_amount_borrowed.setValue(0.0)
            self.edit_amount_due.setValue(0.0)
            self.edit_risky.setChecked(False)
            self.edit_notes.setPlainText("")
            self.edit_payment_methods.setPlainText("")
            # Clear installments table
            self.inst_table.setRowCount(0)
            self._autosize_installments_table()
            self._loading_details = False
            self._dirty = False
            return
        self.edit_org.setText(loan.org_name or "")
        self.edit_site.setText(loan.website or "")
        y, m, d = map(int, loan.loan_date.split("-"))
        self.edit_loan_date.setDate(QDate(y, m, d))
        y2, m2, d2 = map(int, loan.due_date.split("-"))
        self.edit_due_date.setDate(QDate(y2, m2, d2))
        self.edit_amount_borrowed.setValue(float(loan.amount_borrowed))
        total_due = get_installments_total(loan.id) if loan.id is not None else loan.amount_due
        self.edit_amount_due.setValue(float(total_due))
        self.edit_risky.setChecked(bool(loan.risky_org))
        self.edit_notes.setPlainText(loan.notes or "")
        self.edit_payment_methods.setPlainText(loan.payment_methods or "")
        # Refresh installments for this loan
        self._refresh_installments(loan.id)
        self._loading_details = False
        self._dirty = False

    # ------- Installments helpers (inline) -------
    def _refresh_installments(self, loan_id: Optional[int]) -> None:
        self.inst_table.setRowCount(0)
        if loan_id is None:
            self._autosize_installments_table()
            return
        for inst in list_installments(loan_id):
            row = self.inst_table.rowCount()
            self.inst_table.insertRow(row)
            date_item = QTableWidgetItem(self._format_date(inst.due_date))
            amount_item = QTableWidgetItem(f"{inst.amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            paid_item = QTableWidgetItem("Да" if inst.paid else "Нет")
            paid_date_item = QTableWidgetItem(self._format_date(inst.paid_date) if inst.paid_date else "")
            id_item = QTableWidgetItem(str(inst.id) if inst.id is not None else "")
            self.inst_table.setItem(row, 0, date_item)
            self.inst_table.setItem(row, 1, amount_item)
            self.inst_table.setItem(row, 2, paid_item)
            self.inst_table.setItem(row, 3, paid_date_item)
            self.inst_table.setItem(row, 4, id_item)
        self.inst_table.resizeColumnsToContents()
        self._autosize_installments_table()
        # Update right panel amount due from installments
        total_due = get_installments_total(loan_id)
        self.edit_amount_due.setValue(float(total_due))

    def _autosize_installments_table(self) -> None:
        header_h = self.inst_table.horizontalHeader().height()
        rows_h = sum(self.inst_table.rowHeight(r) for r in range(self.inst_table.rowCount()))
        frame = 2 * self.inst_table.frameWidth()
        total = header_h + rows_h + frame + 4
        self.inst_table.setFixedHeight(max(total, header_h + 24))

    def _current_installment_id(self) -> Optional[int]:
        selected = self.inst_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        id_item = self.inst_table.item(row, 4)
        try:
            return int(id_item.text())
        except Exception:
            return None

    def _on_inst_add(self) -> None:
        if self._create_mode:
            QMessageBox.information(self, "График", "Сохраните кредит, затем добавляйте платежи")
            return
        loan_id = self.current_selected_id()
        if loan_id is None:
            QMessageBox.information(self, "График", "Выберите кредит в списке")
            return
        amount = float(self.inst_amount.value())
        if amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля")
            return
        date_iso = self.inst_date.date().toString("yyyy-MM-dd")
        add_installment(
            inst=type("_I", (), {
                "id": None,
                "loan_id": loan_id,
                "due_date": date_iso,
                "amount": amount,
                "paid": False,
                "paid_date": None,
                "created_at": "",
            })()
        )
        update_loan_paid_status_if_complete(loan_id)
        recalc_loan_amount_due(loan_id)
        self._refresh_installments(loan_id)
        # Refresh list to recalc next payment and colors
        self.refresh()
        self._focus_row_by_id(loan_id)

    def _on_inst_toggle(self) -> None:
        if self._create_mode:
            return
        loan_id = self.current_selected_id()
        if loan_id is None:
            return
        inst_id = self._current_installment_id()
        if inst_id is None:
            QMessageBox.information(self, "Статус", "Выберите платеж")
            return
        # Determine current paid status from table
        row = self.inst_table.currentRow()
        paid_text = self.inst_table.item(row, 2).text()
        currently_paid = paid_text.lower().startswith("д") or paid_text.lower().startswith("y")
        new_paid = not currently_paid
        paid_date_val = QDate.currentDate().toString("yyyy-MM-dd") if new_paid else None
        mark_installment_paid(inst_id, new_paid, paid_date_val)
        update_loan_paid_status_if_complete(loan_id)
        recalc_loan_amount_due(loan_id)
        self._refresh_installments(loan_id)
        self.refresh()
        self._focus_row_by_id(loan_id)

    def _on_inst_delete(self) -> None:
        if self._create_mode:
            return
        loan_id = self.current_selected_id()
        if loan_id is None:
            return
        inst_id = self._current_installment_id()
        if inst_id is None:
            QMessageBox.information(self, "Удаление", "Выберите платеж")
            return
        if QMessageBox.question(self, "Подтвердите", "Удалить выбранный платеж?") != QMessageBox.StandardButton.Yes:
            return
        delete_installment(inst_id)
        update_loan_paid_status_if_complete(loan_id)
        recalc_loan_amount_due(loan_id)
        self._refresh_installments(loan_id)
        self.refresh()
        self._focus_row_by_id(loan_id)
