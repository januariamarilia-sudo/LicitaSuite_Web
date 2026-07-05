@echo off
title LicitaSuite Web 1.0 Free

cd /d "%~dp0\.."

echo ==========================================
echo LicitaSuite Web 1.0 Free
echo ==========================================
echo.

echo Instalando dependencias web...
python -m pip install -r web\requirements_web.txt

echo.
echo Abrindo no navegador...
echo Endereco:
echo http://localhost:8501
echo.

python -m streamlit run web\app.py

pause