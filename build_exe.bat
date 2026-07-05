@echo off
title LicitaSuite - Gerar Executavel

echo ==========================================
echo LicitaSuite - Gerador de Executavel
echo ==========================================
echo.

cd /d "%~dp0\.."

echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo Gerando executavel...
pyinstaller --noconfirm --clean ^
  --name LicitaSuite ^
  --windowed ^
  --add-data "config;config" ^
  --add-data "docs;docs" ^
  main.py

echo.
echo ==========================================
echo Concluido.
echo O executavel estara em:
echo dist\LicitaSuite\LicitaSuite.exe
echo ==========================================
pause