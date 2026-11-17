@echo off
cd /d "%~dp0"
set PY=
py -3 --version >nul 2>&1 && set PY=py -3
if not defined PY (
  python --version >nul 2>&1 && set PY=python
)
if not defined PY (
  echo Nao encontrei o Python. Teste no PowerShell: py --version
  pause
  exit /b 1
)
echo Usando: %PY%
if not exist .venv\Scripts\activate.bat (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
python -m streamlit run app.py
pause
