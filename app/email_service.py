"""
Email сервис для отправки уведомлений
Поддержка: подтверждение регистрации, восстановление пароля, приветственные письма
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os


class EmailService:
    """Сервис отправки email"""
    
    def __init__(self):
        # Получаем конфигурацию из переменных окружения или secrets
        try:
            from app.secrets import (
                SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
                EMAIL_FROM, SITE_URL
            )
            self.smtp_host = SMTP_HOST
            self.smtp_port = SMTP_PORT
            self.smtp_user = SMTP_USER
            self.smtp_password = SMTP_PASSWORD
            self.email_from = EMAIL_FROM
            self.site_url = SITE_URL
        except ImportError:
            # Fallback на переменные окружения
            self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
            self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
            self.smtp_user = os.getenv('SMTP_USER', '')
            self.smtp_password = os.getenv('SMTP_PASSWORD', '')
            self.email_from = os.getenv('EMAIL_FROM', 'noreply@mikrokredit.local')
            self.site_url = os.getenv('SITE_URL', 'http://localhost:5000')
        
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
        """
        Внутренний метод для отправки email
        Returns: True если успешно, иначе False
        """
        if not self.enabled:
            print(f"⚠️  Email не настроен. Письмо '{subject}' не отправлено на {to_email}")
            print(f"💡 Для настройки email добавьте SMTP параметры в app/secrets.py")
            return False
        
        try:
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = to_email
            
            # Добавляем текстовую и HTML версии
            if text_body:
                part1 = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(part1)
            
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part2)
            
            # Отправляем с коротким таймаутом
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email отправлен: {subject} → {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки email на {to_email}: {e}")
            return False
    
    def send_verification_email(self, user_email: str, user_name: str, token: str) -> bool:
        """Отправить письмо с подтверждением регистрации"""
        verification_url = f"{self.site_url}/auth/verify-email/{token}"
        
        subject = "Подтвердите вашу регистрацию"
        
        # HTML версия
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #007bff; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-top: none; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 МикроКредит</h1>
                </div>
                <div class="content">
                    <h2>Добро пожаловать, {user_name or 'пользователь'}!</h2>
                    <p>Спасибо за регистрацию в системе МикроКредит.</p>
                    <p>Для завершения регистрации, пожалуйста, подтвердите ваш email адрес, нажав на кнопку ниже:</p>
                    <p style="text-align: center;">
                        <a href="{verification_url}" class="button">Подтвердить email</a>
                    </p>
                    <p>Или скопируйте эту ссылку в браузер:</p>
                    <p style="word-break: break-all; color: #007bff;">{verification_url}</p>
                    <p><small>Ссылка действительна в течение 24 часов.</small></p>
                </div>
                <div class="footer">
                    <p>Если вы не регистрировались в системе МикроКредит, просто проигнорируйте это письмо.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        text_body = f"""
        Добро пожаловать в МикроКредит!
        
        Спасибо за регистрацию. Для завершения регистрации подтвердите ваш email адрес:
        
        {verification_url}
        
        Ссылка действительна в течение 24 часов.
        
        Если вы не регистрировались в системе, просто проигнорируйте это письмо.
        """
        
        return self._send_email(user_email, subject, html_body, text_body)
    
    def send_password_reset_email(self, user_email: str, user_name: str, token: str) -> bool:
        """Отправить письмо с восстановлением пароля"""
        reset_url = f"{self.site_url}/auth/reset-password/{token}"
        
        subject = "Восстановление пароля"
        
        # HTML версия
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-top: none; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Восстановление пароля</h1>
                </div>
                <div class="content">
                    <h2>Здравствуйте, {user_name or 'пользователь'}!</h2>
                    <p>Вы запросили восстановление пароля для вашего аккаунта в системе МикроКредит.</p>
                    <p>Для установки нового пароля нажмите на кнопку ниже:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Сбросить пароль</a>
                    </p>
                    <p>Или скопируйте эту ссылку в браузер:</p>
                    <p style="word-break: break-all; color: #007bff;">{reset_url}</p>
                    <p><small>Ссылка действительна в течение 24 часов.</small></p>
                </div>
                <div class="footer">
                    <p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>
                    <p>Ваш пароль останется прежним.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        text_body = f"""
        Восстановление пароля
        
        Здравствуйте, {user_name or 'пользователь'}!
        
        Вы запросили восстановление пароля. Для установки нового пароля перейдите по ссылке:
        
        {reset_url}
        
        Ссылка действительна в течение 24 часов.
        
        Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
        """
        
        return self._send_email(user_email, subject, html_body, text_body)
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Отправить приветственное письмо"""
        subject = "Добро пожаловать в МикроКредит!"
        
        # HTML версия
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-top: none; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .features {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Добро пожаловать!</h1>
                </div>
                <div class="content">
                    <h2>Здравствуйте, {user_name or 'пользователь'}!</h2>
                    <p>Ваш email успешно подтвержден. Теперь у вас есть полный доступ к системе МикроКредит.</p>
                    
                    <div class="features">
                        <h3>📊 Что вы можете делать:</h3>
                        <ul>
                            <li><strong>💳 Управление займами:</strong> отслеживайте все ваши займы в одном месте</li>
                            <li><strong>✅ Органайзер задач:</strong> создавайте задачи с напоминаниями</li>
                            <li><strong>📱 Telegram уведомления:</strong> получайте напоминания прямо в Telegram</li>
                            <li><strong>📈 Аналитика:</strong> следите за статистикой и прогнозами</li>
                        </ul>
                    </div>
                    
                    <p style="text-align: center;">
                        <a href="{self.site_url}" class="button">Перейти в систему</a>
                    </p>
                    
                    <p><strong>💡 Совет:</strong> Привяжите свой Telegram аккаунт в настройках профиля, чтобы получать уведомления о важных событиях.</p>
                </div>
                <div class="footer">
                    <p>С уважением,<br>Команда МикроКредит</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        text_body = f"""
        Добро пожаловать в МикроКредит!
        
        Здравствуйте, {user_name or 'пользователь'}!
        
        Ваш email успешно подтвержден. Теперь у вас есть полный доступ к системе.
        
        Что вы можете делать:
        - Управление займами
        - Органайзер задач с напоминаниями
        - Telegram уведомления
        - Аналитика и статистика
        
        Перейдите в систему: {self.site_url}
        
        Совет: Привяжите свой Telegram аккаунт в настройках профиля.
        
        С уважением,
        Команда МикроКредит
        """
        
        return self._send_email(user_email, subject, html_body, text_body)


# Глобальный экземпляр сервиса
email_service = EmailService()

