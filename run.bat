@echo off
set PYTHON_EXE=D:\programme\anaconda\python.exe

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Cannot find %PYTHON_EXE%
  echo Please edit run.bat to your Anaconda python path.
  exit /b 1
)

"%PYTHON_EXE%" app.py qrcodes\detection --save-json
