@echo off
chcp 65001 >nul
echo Скрипт импорта данных микрокредита
echo ====================================
echo.

if "%1"=="" (
    echo Использование:
    echo   import_data.bat ^<json_file^> [--clear]
    echo.
    echo Параметры:
    echo   json_file  - Путь к JSON файлу с данными
    echo   --clear    - Удалить существующие данные перед импортом
    echo.
    echo Пример:
    echo   import_data.bat mikrokredit_export_20240101_120000.json
    echo   import_data.bat mikrokredit_export_20240101_120000.json --clear
    goto :end
)

echo Импорт данных из файла: %1
python "%~dp0import_data.py" %1 %2

:end
pause

