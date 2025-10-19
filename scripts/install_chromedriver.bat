@echo off
echo Installing ChromeDriver for Selenium...
echo.

echo Step 1: Check if Chrome is installed
where chrome >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Google Chrome is not installed or not in PATH
    echo Please install Google Chrome first: https://www.google.com/chrome/
    pause
    exit /b 1
)
echo Chrome found ✓

echo.
echo Step 2: Download ChromeDriver
echo Please download ChromeDriver from: https://chromedriver.chromium.org/
echo.
echo 1. Go to https://chromedriver.chromium.org/
echo 2. Download the version that matches your Chrome version
echo 3. Extract the chromedriver.exe file
echo 4. Place it in a folder that's in your PATH (e.g., C:\Windows\System32)
echo    OR place it in the same folder as this script
echo.
echo After downloading, press any key to continue...
pause >nul

echo.
echo Step 3: Verify ChromeDriver installation
where chromedriver >nul 2>nul
if %errorlevel% equ 0 (
    echo ChromeDriver found in PATH ✓
    chromedriver --version
) else (
    echo ChromeDriver not found in PATH
    echo Please make sure chromedriver.exe is in your PATH or current directory
)

echo.
echo Installation complete!
echo You can now run the Selenium crawler with: python selenium_crawler.py
pause
