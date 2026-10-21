@echo off
chcp 65001 >nul
setlocal
title ЛогиХаб – аналитический дашборд
cd /d "%~dp0"

echo.
echo   ЛогиХаб – аналитический дашборд (Попов А.С., 5ИТб-2)
echo   ---------------------------------------------------
echo.

rem === 1. Папка проекта: рядом с этим файлом, в подпапке или скачать с GitHub ===
set "APP="
if exist "%~dp0app.py" set "APP=%~dp0"
if not defined APP if exist "%~dp0logihub-dashboard\app.py" set "APP=%~dp0logihub-dashboard\"
if not defined APP if exist "%~dp0logihub-dashboard-main\app.py" set "APP=%~dp0logihub-dashboard-main\"
if not defined APP if exist "%USERPROFILE%\logihub-dashboard\app.py" set "APP=%USERPROFILE%\logihub-dashboard\"
if not defined APP call :download
if not defined APP goto :fail
cd /d "%APP%"
echo   Папка проекта: %CD%

rem === 2. Python 3.11+ ===
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=python"
if not defined PY goto :nopython

rem === 3. Виртуальное окружение и библиотеки (только при первом запуске) ===
if not exist ".venv\Scripts\python.exe" (
    echo   Создаю виртуальное окружение .venv ...
    %PY% -m venv .venv || goto :fail
)
".venv\Scripts\python.exe" -c "import dash, dash_bootstrap_components, pandas, plotly" >nul 2>&1
if errorlevel 1 (
    echo   Устанавливаю библиотеки, это около минуты ...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fail
)

rem === 4. Запуск: браузер откроется сам, папка с CSV – тоже ===
echo.
echo   Дашборд: http://127.0.0.1:8050
echo   Перетащите на страницу файл data\logistics_orders.csv (папка откроется рядом).
echo   Чтобы остановить дашборд, закройте это окно.
echo.
start "" explorer /select,"%CD%\data\logistics_orders.csv"
start "" /b cmd /c "ping -n 6 127.0.0.1 >nul & start "" http://127.0.0.1:8050"
".venv\Scripts\python.exe" app.py
goto :end

:download
echo   Рядом нет проекта – скачиваю его с GitHub в %USERPROFILE%\logihub-dashboard ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12';" ^
  "$z=Join-Path $env:TEMP 'logihub.zip'; $d=Join-Path $env:TEMP 'logihub-unzip';" ^
  "Invoke-WebRequest 'https://github.com/starpxand/logihub-dashboard/archive/refs/heads/main.zip' -OutFile $z -UseBasicParsing;" ^
  "if (Test-Path $d) { Remove-Item $d -Recurse -Force }; Expand-Archive $z $d;" ^
  "Move-Item (Join-Path $d 'logihub-dashboard-main') (Join-Path $env:USERPROFILE 'logihub-dashboard')"
if exist "%USERPROFILE%\logihub-dashboard\app.py" set "APP=%USERPROFILE%\logihub-dashboard\"
exit /b

:nopython
echo   Не найден Python 3.11 или новее.
echo   Установите его с python.org (при установке отметьте «Add python.exe to PATH»)
echo   и запустите этот файл ещё раз. Сейчас откроется страница загрузки.
start "" https://www.python.org/downloads/
goto :end

:fail
echo.
echo   Не получилось запустить дашборд – сообщение об ошибке выше.
echo   Ручной запуск описан в README: https://github.com/starpxand/logihub-dashboard

:end
echo.
pause
