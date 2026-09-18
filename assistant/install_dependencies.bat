@echo off
setlocal
title JARVIS — установка зависимостей

cd /d "%~dp0"

echo.
echo ==========================================
echo        JARVIS — УСТАНОВКА
echo ==========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo Python не найден.
        echo Установи Python 3.11+ и запусти этот файл снова.
        pause
        exit /b 1
    )
)

echo Обновление pip...
%PY% -m pip install --upgrade pip

echo.
echo Установка зависимостей...
%PY% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Не удалось установить зависимости.
    echo Для PyAudio на некоторых системах требуется отдельный wheel.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo      ВСЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ
echo ==========================================
echo.
pause
