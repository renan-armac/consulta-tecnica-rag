@echo off
REM Inicia a interface de chat. Requer Python e Ollama instalados.
cd /d "%~dp0"

REM Procura o Python: primeiro o lancador oficial "py", depois o comando "python".
where py >nul 2>nul && (set "PY=py") || (set "PY=python")

echo Usando: %PY%
"%PY%" -c "import streamlit, fpdf, pypdf" 2>nul || "%PY%" -m pip install -r requirements.txt

echo.
echo Abrindo o chat em http://localhost:8501
echo Mantenha esta janela aberta. Feche-a para encerrar o servidor.
echo.
"%PY%" -m streamlit run app.py
pause
