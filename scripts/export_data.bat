@echo off
chcp 65001 >nul
echo Скрипт экспорта данных микрокредита
echo =====================================
echo.

if "%1"=="--help" (
    echo Использование:
    echo   export_data.bat           # Экспорт в JSON
    echo   export_data.bat --sql     # Экспорт в SQL
    echo   export_data.bat --help    # Показать эту справку
    goto :end
)

if "%1"=="--sql" (
    echo Экспорт в SQL формат...
    python "%~dp0export_data.py" --sql
) else (
    echo Экспорт в JSON формат...
    python "%~dp0export_data.py" %1
)

:end
pause

