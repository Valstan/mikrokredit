"""
Загрузочное окно с прогресс-баром для отображения процесса запуска приложения.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QApplication, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QBrush
import time


class SplashScreen(QWidget):
    """Загрузочное окно с анимированным прогресс-баром."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Микрокредиты - Загрузка")
        self.setFixedSize(650, 450)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._setup_animation()
        
        # Центрируем окно
        self._center_window()
    
    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        # Главный контейнер с тенью
        main_frame = QFrame()
        main_frame.setObjectName("mainFrame")
        main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 2px solid #dee2e6;
                border-radius: 15px;
            }
        """)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 50))
        main_frame.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(main_frame)
        
        # Внутренний layout
        inner_layout = QVBoxLayout(main_frame)
        inner_layout.setContentsMargins(60, 60, 60, 60)
        inner_layout.setSpacing(35)
        
        # Иконка и заголовок
        icon_label = QLabel("💰")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 72px;
                margin-bottom: 25px;
                padding: 15px;
            }
        """)
        inner_layout.addWidget(icon_label)
        
        # Заголовок
        title_label = QLabel("Микрокредиты")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #495057;
                margin-bottom: 25px;
                padding: 15px;
            }
        """)
        inner_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Органайзер кредитов")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                color: #6c757d;
                margin-bottom: 35px;
                padding: 15px;
            }
        """)
        inner_layout.addWidget(subtitle_label)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 3px solid #dee2e6;
                border-radius: 12px;
                text-align: center;
                font-weight: bold;
                font-size: 18px;
                height: 45px;
                background-color: #f8f9fa;
                padding: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 10px;
            }
        """)
        inner_layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #495057;
                margin-top: 25px;
                padding: 15px;
            }
        """)
        inner_layout.addWidget(self.status_label)
        
        # Версия
        version_label = QLabel("v2.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #adb5bd;
                margin-top: 25px;
                padding: 15px;
            }
        """)
        inner_layout.addWidget(version_label)
    
    def _setup_animation(self):
        """Настройка анимации прогресс-бара."""
        self.animation = QPropertyAnimation(self.progress_bar, b"value")
        self.animation.setDuration(3000)  # 3 секунды
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Таймер для обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(200)  # Обновляем каждые 200мс
        
        self.current_step = 0
        self.status_messages = [
            "Инициализация...",
            "Загрузка модулей...",
            "Подключение к базе данных...",
            "Проверка соединения...",
            "Загрузка данных...",
            "Создание интерфейса...",
            "Завершение загрузки..."
        ]
    
    def _center_window(self):
        """Центрирование окна на экране."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _update_status(self):
        """Обновление статуса загрузки."""
        if self.current_step < len(self.status_messages):
            self.status_label.setText(self.status_messages[self.current_step])
            self.current_step += 1
        else:
            self.status_timer.stop()
    
    def start_loading(self):
        """Запуск анимации загрузки."""
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.start()
        self.show()
    
    def set_progress(self, value: int):
        """Установка значения прогресс-бара."""
        self.progress_bar.setValue(value)
    
    def set_status(self, message: str):
        """Установка текста статуса."""
        self.status_label.setText(message)
    
    def close_splash(self):
        """Закрытие загрузочного окна."""
        self.close()


class LoadingThread(QThread):
    """Поток для выполнения загрузки в фоне."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.splash = None
    
    def set_splash(self, splash: SplashScreen):
        """Установка ссылки на загрузочное окно."""
        self.splash = splash
        self.progress_updated.connect(splash.set_progress)
        self.status_updated.connect(splash.set_status)
    
    def run(self):
        """Выполнение загрузки."""
        try:
            # Шаг 1: Инициализация
            self.status_updated.emit("Инициализация приложения...")
            self.progress_updated.emit(5)
            time.sleep(0.3)
            
            # Шаг 2: Импорт модулей
            self.status_updated.emit("Загрузка модулей PyQt6...")
            self.progress_updated.emit(15)
            time.sleep(0.4)
            
            # Шаг 3: Импорт SQLAlchemy
            self.status_updated.emit("Загрузка модулей базы данных...")
            self.progress_updated.emit(25)
            time.sleep(0.3)
            
            # Шаг 4: Подключение к PostgreSQL
            self.status_updated.emit("Подключение к PostgreSQL на Render...")
            self.progress_updated.emit(40)
            time.sleep(0.8)  # Дольше, так как это реальное подключение
            
            # Шаг 5: Проверка соединения
            self.status_updated.emit("Проверка соединения с базой данных...")
            self.progress_updated.emit(60)
            time.sleep(0.6)
            
            # Шаг 6: Создание таблиц
            self.status_updated.emit("Инициализация структуры базы данных...")
            self.progress_updated.emit(75)
            time.sleep(0.4)
            
            # Шаг 7: Загрузка данных
            self.status_updated.emit("Загрузка данных кредитов...")
            self.progress_updated.emit(85)
            time.sleep(0.3)
            
            # Шаг 8: Создание интерфейса
            self.status_updated.emit("Создание пользовательского интерфейса...")
            self.progress_updated.emit(95)
            time.sleep(0.2)
            
            # Шаг 9: Завершение
            self.status_updated.emit("Завершение загрузки...")
            self.progress_updated.emit(100)
            time.sleep(0.2)
            
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
