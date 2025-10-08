from __future__ import annotations
from typing import Optional
from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QDateEdit,
    QDoubleSpinBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLabel,
    QWidget,
)

from ..models import Installment
from ..repository import (
    list_installments,
    add_installment,
    update_installment,
    delete_installment,
    mark_installment_paid,
    update_loan_paid_status_if_complete,
)


HEADERS = ["Дата", "Сумма", "Оплачен", "Дата оплаты", "ID"]


class InstallmentsDialog(QDialog):
    def __init__(self, parent=None, loan_id: Optional[int] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("График платежей")
        if loan_id is None:
            raise ValueError("loan_id is required")
        self.loan_id = loan_id

        # Controls for add/edit
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.amount_edit = QDoubleSpinBox()
        self.amount_edit.setDecimals(2)
        self.amount_edit.setMaximum(1_000_000_000)

        self.add_btn = QPushButton("Добавить платеж")
        self.add_btn.clicked.connect(self.on_add)

        self.edit_btn = QPushButton("Изменить выбранный")
        self.edit_btn.clicked.connect(self.on_edit)

        self.delete_btn = QPushButton("Удалить выбранный")
        self.delete_btn.clicked.connect(self.on_delete)

        self.toggle_paid_btn = QPushButton("Пометить оплачен/не оплачен")
        self.toggle_paid_btn.clicked.connect(self.on_toggle_paid)

        form = QFormLayout()
        form.addRow("Дата платежа", self.date_edit)
        form.addRow("Сумма", self.amount_edit)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.addLayout(form)
        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.edit_btn)
        top_layout.addWidget(self.delete_btn)
        top_layout.addWidget(self.toggle_paid_btn)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.summary = QLabel("")

        layout = QVBoxLayout(self)
        layout.addWidget(top)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)

        self.refresh()

    def current_selected_id(self) -> Optional[int]:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        id_item = self.table.item(row, 4)
        try:
            return int(id_item.text())
        except Exception:
            return None

    def on_add(self) -> None:
        inst = Installment(
            id=None,
            loan_id=self.loan_id,
            due_date=self.date_edit.date().toString("yyyy-MM-dd"),
            amount=float(self.amount_edit.value()),
            paid=False,
            paid_date=None,
            created_at="",
        )
        if inst.amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля")
            return
        add_installment(inst)
        self.refresh()

    def on_edit(self) -> None:
        inst_id = self.current_selected_id()
        if inst_id is None:
            QMessageBox.information(self, "Изменение", "Выберите платеж")
            return
        # Read current row values
        row = self.table.currentRow()
        due_str = self.table.item(row, 0).text()
        amount_str = self.table.item(row, 1).text()
        paid_text = self.table.item(row, 2).text()
        paid = paid_text.lower().startswith("д") or paid_text.lower().startswith("y")
        pd = self.table.item(row, 3).text() or None

        # Update with form fields
        due_new = self.date_edit.date().toString("yyyy-MM-dd")
        amt_new = float(self.amount_edit.value())
        if amt_new <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля")
            return
        update_installment(
            Installment(
                id=inst_id,
                loan_id=self.loan_id,
                due_date=due_new,
                amount=amt_new,
                paid=paid,
                paid_date=pd,
                created_at="",
            )
        )
        self.refresh()

    def on_delete(self) -> None:
        inst_id = self.current_selected_id()
        if inst_id is None:
            QMessageBox.information(self, "Удаление", "Выберите платеж")
            return
        if QMessageBox.question(self, "Подтвердите", "Удалить выбранный платеж?") == QMessageBox.StandardButton.Yes:
            delete_installment(inst_id)
            self.refresh()

    def on_toggle_paid(self) -> None:
        inst_id = self.current_selected_id()
        if inst_id is None:
            QMessageBox.information(self, "Статус", "Выберите платеж")
            return
        # Infer current status from table
        row = self.table.currentRow()
        paid_text = self.table.item(row, 2).text()
        currently_paid = paid_text.lower().startswith("д") or paid_text.lower().startswith("y")
        new_paid = not currently_paid
        paid_date_val = date.today().isoformat() if new_paid else None
        mark_installment_paid(inst_id, new_paid, paid_date_val)
        update_loan_paid_status_if_complete(self.loan_id)
        self.refresh()

    def refresh(self) -> None:
        insts = list_installments(self.loan_id)
        self.table.setRowCount(0)
        total = 0.0
        unpaid = 0.0
        for inst in insts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = [
                QTableWidgetItem(inst.due_date),
                QTableWidgetItem(f"{inst.amount:.2f}"),
                QTableWidgetItem("Да" if inst.paid else "Нет"),
                QTableWidgetItem(inst.paid_date or ""),
                QTableWidgetItem(str(inst.id) if inst.id is not None else ""),
            ]
            self.table.setItem(row, 0, items[0])
            self.table.setItem(row, 1, items[1])
            self.table.setItem(row, 2, items[2])
            self.table.setItem(row, 3, items[3])
            self.table.setItem(row, 4, items[4])
            total += inst.amount
            if not inst.paid:
                unpaid += inst.amount
        self.summary.setText(f"Всего по графику: {total:.2f} | Не оплачено: {unpaid:.2f}")
