@echo off
echo Building Personal AI Assistant...
echo.

echo Installing dependencies...
pip install -r requirements.txt
echo.

echo Building executable...
pyinstaller --onefile ^
    --windowed ^
    --name "PersonalAI" ^
    --icon=icon.ico ^
    --add-data "models;models" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "." ^
    gui_app.py

echo.
echo Build complete! Check the 'dist' folder for the executable.
echo.
pause
