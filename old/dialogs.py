from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QDateEdit,
    QDoubleSpinBox,
    QCheckBox,
    QTextEdit,
    QMessageBox,
    QTabWidget,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
)

from ..models import Loan, Installment
from ..repository import (
    list_installments,
    add_installment,
    update_installment,
    delete_installment,
    mark_installment_paid,
    update_loan_paid_status_if_complete,
)


SCHED_HEADERS = ["Дата", "Сумма", "Оплачен", "Дата оплаты", "ID"]


class LoanDialog(QDialog):
    def __init__(self, parent=None, loan: Optional[Loan] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Кредит")

        # --- Main tab widgets ---
        self.org_name = QLineEdit()
        self.website = QLineEdit()
        self.loan_date = QDateEdit()
        self.loan_date.setCalendarPopup(True)
        self.loan_date.setDate(QDate.currentDate())

        self.amount_borrowed = QDoubleSpinBox()
        self.amount_borrowed.setDecimals(2)
        self.amount_borrowed.setMaximum(1_000_000_000)

        # `amount_due` is calculated from the schedule and should not be edited by the user
        self.amount_due = QDoubleSpinBox()
        self.amount_due.setDecimals(2)
        self.amount_due.setMaximum(1_000_000_000)
        self.amount_due.setReadOnly(True)

        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())

        self.risky_org = QCheckBox("Есть скрытые страховки/услуги — быть внимательным")
        self.is_paid = QCheckBox("Кредит выплачен")
        self.notes = QTextEdit()
        self.payment_methods = QTextEdit()

        form = QFormLayout()
        form.addRow("Название организации", self.org_name)
        form.addRow("Сайт организации", self.website)
        form.addRow("Дата оформления", self.loan_date)
        form.addRow("Сумма взята", self.amount_borrowed)
        form.addRow("Сумма к возврату", self.amount_due)
        form.addRow("Дата возврата", self.due_date)
        form.addRow("Рискованная организация", self.risky_org)
        form.addRow("Кредит выплачен", self.is_paid)
        form.addRow("Заметки (галочки/услуги)", self.notes)
        form.addRow("Способы оплаты и комиссии", self.payment_methods)

        main_tab = QWidget()
        main_tab.setLayout(form)

        # --- Schedule tab widgets ---
        self.schedule_info = QLabel("Сохраните кредит, затем добавьте платежи")
        self.s_date = QDateEdit(); self.s_date.setCalendarPopup(True); self.s_date.setDate(QDate.currentDate())
        self.s_amount = QDoubleSpinBox(); self.s_amount.setDecimals(2); self.s_amount.setMaximum(1_000_000_000)

        self.s_add = QPushButton("Добавить")
        self.s_edit = QPushButton("Изменить")
        self.s_delete = QPushButton("Удалить")
        self.s_toggle = QPushButton("Оплачен/Не оплачен")

        s_form = QFormLayout()
        s_form.addRow("Дата платежа", self.s_date)
        s_form.addRow("Сумма", self.s_amount)

        s_btns = QHBoxLayout()
        s_btns.addWidget(self.s_add)
        s_btns.addWidget(self.s_edit)
        s_btns.addWidget(self.s_delete)
        s_btns.addWidget(self.s_toggle)

        self.s_table = QTableWidget(0, len(SCHED_HEADERS))
        self.s_table.setHorizontalHeaderLabels(SCHED_HEADERS)
        self.s_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.s_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.s_table.setAlternatingRowColors(True)
        self.s_table.horizontalHeader().setStretchLastSection(True)

        s_tab_layout = QVBoxLayout()
        s_tab_layout.addWidget(self.schedule_info)
        s_tab_layout.addLayout(s_form)
        s_tab_layout.addLayout(s_btns)
        s_tab_layout.addWidget(self.s_table)

        schedule_tab = QWidget()
        schedule_tab.setLayout(s_tab_layout)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(main_tab, "Основное")
        tabs.addTab(schedule_tab, "График платежей")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

        # Wire schedule handlers
        self.s_add.clicked.connect(self._sched_add)
        self.s_edit.clicked.connect(self._sched_edit)
        self.s_delete.clicked.connect(self._sched_delete)
        self.s_toggle.clicked.connect(self._sched_toggle)

        self._editing_id: Optional[int] = None
        if loan is not None:
            self._populate_from_loan(loan)
        self._update_schedule_enabled()
        if self._editing_id is not None:
            self._refresh_schedule()

    def _populate_from_loan(self, loan: Loan) -> None:
        self._editing_id = loan.id
        self.org_name.setText(loan.org_name or "")
        self.website.setText(loan.website)
        y, m, d = map(int, loan.loan_date.split("-"))
        self.loan_date.setDate(QDate(y, m, d))
        self.amount_borrowed.setValue(float(loan.amount_borrowed))
        self.amount_due.setValue(float(loan.amount_due))
        y2, m2, d2 = map(int, loan.due_date.split("-"))
        self.due_date.setDate(QDate(y2, m2, d2))
        self.risky_org.setChecked(bool(loan.risky_org))
        self.is_paid.setChecked(bool(loan.is_paid))
        self.notes.setPlainText(loan.notes)
        self.payment_methods.setPlainText(loan.payment_methods)

    def _on_accept(self) -> None:
        if not self.org_name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите название организации")
            return
        if not self.website.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите сайт организации")
            return
        if self.amount_borrowed.value() <= 0 or self.amount_due.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Суммы должны быть больше нуля")
            return
        if self.due_date.date() < self.loan_date.date():
            QMessageBox.warning(self, "Ошибка", "Дата возврата не может быть раньше даты оформления")
            return
        self.accept()

    def get_loan(self) -> Loan:
        ld = self.loan_date.date().toString("yyyy-MM-dd")
        dd = self.due_date.date().toString("yyyy-MM-dd")
        return Loan(
            id=self._editing_id,
            website=self.website.text().strip(),
            loan_date=ld,
            amount_borrowed=float(self.amount_borrowed.value()),
            amount_due=float(self.amount_due.value()),
            due_date=dd,
            risky_org=self.risky_org.isChecked(),
            notes=self.notes.toPlainText().strip(),
            payment_methods=self.payment_methods.toPlainText().strip(),
            reminded_pre_due=False,
            created_at="",
            is_paid=self.is_paid.isChecked(),
            org_name=self.org_name.text().strip(),
        )

    # ---- Schedule helpers ----
    def _update_schedule_enabled(self) -> None:
        enabled = self._editing_id is not None
        for w in (self.s_date, self.s_amount, self.s_add, self.s_edit, self.s_delete, self.s_toggle, self.s_table):
            w.setEnabled(enabled)
        self.schedule_info.setText("График платежей для этого кредита" if enabled else "Сохраните кредит, затем добавьте платежи")

    def _refresh_schedule(self) -> None:
        if self._editing_id is None:
            return
        insts = list_installments(self._editing_id)
        self.s_table.setRowCount(0)
        for inst in insts:
            row = self.s_table.rowCount()
            self.s_table.insertRow(row)
            items = [
                QTableWidgetItem(inst.due_date),
                QTableWidgetItem(f"{inst.amount:.2f}"),
                QTableWidgetItem("Да" if inst.paid else "Нет"),
                QTableWidgetItem(inst.paid_date or ""),
                QTableWidgetItem(str(inst.id) if inst.id is not None else ""),
            ]
            for col, item in enumerate(items):
                if col == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.s_table.setItem(row, col, item)

    def _current_installment_id(self) -> Optional[int]:
        selected = self.s_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        id_item = self.s_table.item(row, 4)
        try:
            return int(id_item.text())
        except Exception:
            return None

    def _sched_add(self) -> None:
        if self._editing_id is None:
            QMessageBox.information(self, "График", "Сохраните кредит, затем добавляйте платежи")
            return
        amt = float(self.s_amount.value())
        if amt <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля")
            return
        inst = Installment(
            id=None,
            loan_id=self._editing_id,
            due_date=self.s_date.date().toString("yyyy-MM-dd"),
            amount=amt,
            paid=False,
            paid_date=None,
            created_at="",
        )
        add_installment(inst)
        self._refresh_schedule()

    def _sched_edit(self) -> None:
        if self._editing_id is None:
            return
        inst_id = self._current_installment_id()
        if inst_id is None:
            QMessageBox.information(self, "Изменение", "Выберите платеж")
            return
        amt = float(self.s_amount.value())
        if amt <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля")
            return
        inst = Installment(
            id=inst_id,
            loan_id=self._editing_id,
            due_date=self.s_date.date().toString("yyyy-MM-dd"),
            amount=amt,
            paid=self._current_row_paid(),
            paid_date=self._current_row_paid_date(),
            created_at="",
        )
        update_installment(inst)
        self._refresh_schedule()

    def _sched_delete(self) -> None:
        inst_id = self._current_installment_id()
        if inst_id is None:
            QMessageBox.information(self, "Удаление", "Выберите платеж")
            return
        delete_installment(inst_id)
        self._refresh_schedule()

    def _sched_toggle(self) -> None:
        inst_id = self._current_installment_id()
        if inst_id is None:
            QMessageBox.information(self, "Статус", "Выберите платеж")
            return
        currently_paid = self._current_row_paid()
        new_paid = not currently_paid
        paid_date_val = date.today().isoformat() if new_paid else None
        mark_installment_paid(inst_id, new_paid, paid_date_val)
        update_loan_paid_status_if_complete(self._editing_id)
        self._refresh_schedule()

    def _current_row_paid(self) -> bool:
        selected = self.s_table.selectedItems()
        if not selected:
            return False
        row = selected[0].row()
        txt = self.s_table.item(row, 2).text()
        return txt.lower().startswith("д") or txt.lower().startswith("y")

    def _current_row_paid_date(self) -> Optional[str]:
        selected = self.s_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        t = self.s_table.item(row, 3).text()
        return t or None
