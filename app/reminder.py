from __future__ import annotations
from typing import List
from datetime import date

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon, QStyle, QApplication

from .repository import get_due_soon_loans, mark_loan_reminded


class ReminderService(QObject):
    """Periodic checker that shows tray notifications for loans due within 7 days.

    It marks each loan as reminded once a notification is shown to avoid duplicates.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(self._default_icon())
        self.tray.setToolTip("MikroKredit Organizer")
        self.tray.setVisible(True)

        # Check immediately on start, then every 6 hours
        self.timer = QTimer(self)
        self.timer.setInterval(6 * 60 * 60 * 1000)
        self.timer.timeout.connect(self.check_and_notify)
        self.timer.start()

        QTimer.singleShot(2000, self.check_and_notify)

    def _default_icon(self) -> QIcon:
        app = QApplication.instance()
        if app is not None:
            return app.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton)
        return QIcon()

    def check_and_notify(self) -> None:
        loans = get_due_soon_loans(7)
        if not loans:
            return
        for loan in loans:
            self._notify_loan(loan.id, loan.website, loan.due_date, loan.amount_due)

    def _notify_loan(self, loan_id: int, website: str, due_date: str, amount_due: float) -> None:
        days_left = self._days_until(due_date)
        title = "Скоро срок погашения кредита"
        message = f"{website}: до {due_date} нужно вернуть {amount_due:.2f}. Осталось дней: {days_left}."
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 15000)
        mark_loan_reminded(loan_id)

    @staticmethod
    def _days_until(date_iso: str) -> int:
        try:
            y, m, d = map(int, date_iso.split("-"))
            target = date(y, m, d)
            return (target - date.today()).days
        except Exception:
            return 0
