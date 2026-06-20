@echo off
setlocal

set "PYTHON_EXE=D:\programme\anaconda\python.exe"
set "APP_FILE=%~dp0local_qr_web.py"
set "QR_WEB_PORT=8600"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Cannot find Python: %PYTHON_EXE%
  pause
  exit /b 1
)

if not exist "%APP_FILE%" (
  echo [ERROR] Cannot find local_qr_web.py: %APP_FILE%
  pause
  exit /b 1
)

echo Starting local QR web app...
echo URL: http://127.0.0.1:%QR_WEB_PORT%
"%PYTHON_EXE%" "%APP_FILE%"

pause
