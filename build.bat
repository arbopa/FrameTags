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

if not exist dist\FrameTags mkdir dist\FrameTags
copy /Y exiftool.exe dist\FrameTags\exiftool.exe >nul
if errorlevel 1 exit /b 1
xcopy /E /I /Y exiftool_files dist\FrameTags\exiftool_files >nul
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo Output folder: dist\FrameTags
echo Launch: dist\FrameTags\FrameTags.exe
endlocal
