@echo off
set PYTHON_EXE=D:\programme\anaconda\python.exe

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Cannot find %PYTHON_EXE%
  echo Please edit check_env.bat and run.bat to your Anaconda python path.
  exit /b 1
)

"%PYTHON_EXE%" -c "import sys; print('python =', sys.executable); import cv2; print('opencv =', cv2.__version__); import pyzbar; print('pyzbar = ok')"
