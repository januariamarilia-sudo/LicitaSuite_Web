@echo off
title LicitaSuite 6.1 Professional FINAL - Gerar Aplicativo

echo =====================================================
echo LicitaSuite 6.1 Professional FINAL
echo Gerador de Executavel Windows
echo =====================================================
echo.

cd /d "%~dp0\.."

echo Pasta atual:
cd
echo.

IF NOT EXIST "main.py" (
    echo ERRO: main.py nao encontrado na pasta atual.
    echo Coloque a pasta build_tools dentro da pasta principal do LicitaSuite.
    pause
    exit /b 1
)

IF NOT EXIST "requirements.txt" (
    echo ERRO: requirements.txt nao encontrado.
    pause
    exit /b 1
)

echo [1/5] Atualizando pip...
python -m pip install --upgrade pip

echo.
echo [2/5] Instalando dependencias do projeto...
python -m pip install -r requirements.txt

echo.
echo [3/5] Instalando PyInstaller...
python -m pip install pyinstaller

echo.
echo [4/5] Limpando builds antigos...
IF EXIST "build" rmdir /s /q "build"
IF EXIST "dist" rmdir /s /q "dist"
IF EXIST "LicitaSuite.spec" del /q "LicitaSuite.spec"

echo.
echo [5/5] Gerando LicitaSuite.exe...
python -m PyInstaller --noconfirm --clean "build_tools\LicitaSuite.spec"

echo.
IF EXIST "dist\LicitaSuite\LicitaSuite.exe" (
    echo =====================================================
    echo CONCLUIDO COM SUCESSO
    echo.
    echo Aplicativo gerado em:
    echo dist\LicitaSuite\LicitaSuite.exe
    echo.
    echo Abra esse arquivo para testar.
    echo =====================================================
) ELSE (
    echo =====================================================
    echo ATENCAO: O executavel nao foi encontrado.
    echo Verifique as mensagens de erro acima.
    echo =====================================================
)

pause