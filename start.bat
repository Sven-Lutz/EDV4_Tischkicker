@echo off
:: EDV4 Kicker GT3 – Start (Windows)

if not exist "EDV4_TK\" (
    echo [FEHLER] Virtuelle Umgebung 'EDV4_TK' nicht gefunden.
    echo          Bitte zuerst setup.bat ausfuehren.
    pause
    exit /b 1
)

call EDV4_TK\Scripts\activate
python main.py %*
