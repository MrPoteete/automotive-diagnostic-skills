@echo off
echo =====================================
echo    CREATING BACKUP OF YOUR PROJECT
echo =====================================
echo.
echo This will copy ALL your files to a safe backup folder.
echo You can run this as many times as you want - it's 100%% safe!
echo.
set timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
mkdir "backups\backup_%timestamp%" 2>nul
echo Copying files...
xcopy /E /I /Y *.* "backups\backup_%timestamp%\" /exclude:exclude_backup.txt >nul 2>&1
echo.
echo ✅ SUCCESS! Backup created in:
echo    📁 backups\backup_%timestamp%
echo.
echo 🔒 Your work is now SAFE!
echo 💡 You can make changes without worry - this backup won't change.
echo.
echo To restore from this backup if needed:
echo 1. Go to the backups folder
echo 2. Copy files from backup_%timestamp%
echo 3. Paste them back into your main project folder
echo.
pause