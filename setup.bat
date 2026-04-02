@echo off
chcp 65001 >nul

echo.
echo ========================================
echo   EDV4 Kicker GT3 – Setup
echo ========================================
echo.

:: Python prüfen
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden.
    echo          Bitte installiere Python 3.11+ von https://python.org
    echo          Wichtig: "Add Python to PATH" beim Setup ankreuzen!
    pause
    exit /b 1
)

:: Virtuelle Umgebung erstellen
echo [1/3] Erstelle virtuelle Umgebung 'EDV4_TK'...
python -m venv EDV4_TK

if not exist "EDV4_TK\" (
    echo [FEHLER] Virtuelle Umgebung konnte nicht erstellt werden.
    pause
    exit /b 1
)

:: Abhängigkeiten installieren
echo [2/3] Installiere Abhaengigkeiten...
EDV4_TK\Scripts\pip install --upgrade pip --quiet
EDV4_TK\Scripts\pip install -r requirements.txt --quiet

:: Kamera prüfen
echo [3/3] Pruefe Kamera-Zugriff...
EDV4_TK\Scripts\python -c "import cv2; cap=cv2.VideoCapture(0); print('           Kamera gefunden.' if cap.isOpened() else '           Keine Kamera – USB-Kabel pruefen.'); cap.release()" 2>nul

echo.
echo ========================================
echo   Setup abgeschlossen!
echo ========================================
echo.
echo   Umgebung aktivieren:
echo   EDV4_TK\Scripts\activate
echo.
echo   Programm starten:
echo   python main.py
echo.
pause
