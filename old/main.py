import sys
import os
import logging
import time

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QLocale, QTimer

# Ensure project root is on sys.path so absolute imports like 'app.db' work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db_sa import engine
from app.models_sa import Base
from app.ui.main_window_sa import MainWindow
from app.ui.splash_screen import SplashScreen, LoadingThread


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


class AppLoader:
    """Класс для управления загрузкой приложения с загрузочным окном."""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.splash = None
        self.loading_thread = None
    
    def start_loading(self):
        """Запуск процесса загрузки."""
        # Создаем приложение
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Микрокредиты")
        self.app.setApplicationVersion("1.0")
        
        # Set Russian locale for human-friendly date formatting
        QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
        
        # Создаем загрузочное окно
        self.splash = SplashScreen()
        self.splash.start_loading()
        
        # Создаем поток загрузки
        self.loading_thread = LoadingThread()
        self.loading_thread.set_splash(self.splash)
        self.loading_thread.finished.connect(self._on_loading_finished)
        self.loading_thread.error_occurred.connect(self._on_loading_error)
        
        # Запускаем поток
        self.loading_thread.start()
        
        # Показываем загрузочное окно
        self.splash.show()
        
        return self.app.exec()
    
    def _on_loading_finished(self):
        """Обработчик завершения загрузки."""
        try:
            # Инициализируем базу данных
            self.splash.set_status("Инициализация базы данных...")
            init_database()
            
            # Создаем главное окно
            self.splash.set_status("Создание интерфейса...")
            self.main_window = MainWindow()
            
            # Закрываем загрузочное окно
            self.splash.close_splash()
            
            # Показываем главное окно
            self.main_window.show()
            
            logging.info("Application loaded successfully")
            
        except Exception as e:
            self._on_loading_error(str(e))
    
    def _on_loading_error(self, error_message: str):
        """Обработчик ошибки загрузки."""
        logging.error(f"Loading error: {error_message}")
        
        # Закрываем загрузочное окно
        if self.splash:
            self.splash.close_splash()
        
        # Показываем ошибку
        QMessageBox.critical(None, "Ошибка загрузки", 
                           f"Не удалось запустить приложение:\n{error_message}")
        
        # Выходим из приложения
        if self.app:
            self.app.quit()


def main() -> int:
    logging.info("Starting MikroKredit Organizer")
    
    # Создаем загрузчик приложения
    loader = AppLoader()
    return loader.start_loading()


if __name__ == "__main__":
    raise SystemExit(main())
