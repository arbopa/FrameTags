@echo off
setlocal

if not exist main.py (
  echo Run this from the frametags project root.
  exit /b 1
)

python -m pip install -r build-requirements.txt
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --clean frametags.spec
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo Output folder: dist\FrameTags
endlocal
