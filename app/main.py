import sys
import os
import logging

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QLocale

# Ensure project root is on sys.path so absolute imports like 'app.db' work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db_sa import engine
from app.models_sa import Base
from app.ui.main_window_sa import MainWindow


# Configure logging to file and console
LOG_PATH = os.path.join(PROJECT_ROOT, "mikrokredit.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def _excepthook(exctype, value, tb):
    logging.exception("Uncaught exception", exc_info=(exctype, value, tb))
    try:
        QMessageBox.critical(None, "Ошибка", f"Необработанное исключение: {value}")
    except Exception:
        pass


sys.excepthook = _excepthook


def init_database():
    """Инициализация базы данных."""
    try:
        # Создаем таблицы, если их нет
        Base.metadata.create_all(bind=engine)
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        raise


def main() -> int:
    logging.info("Starting MikroKredit Organizer")
    init_database()
    app = QApplication(sys.argv)
    # Set Russian locale for human-friendly date formatting
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
