#!/bin/bash
# EDV4 Tischkicker – Setup (Mac / Linux)

echo ""
echo "========================================"
echo "  EDV4 Kicker GT3 – Setup"
echo "========================================"
echo ""

# Python-Version prüfen
if ! command -v python3 &> /dev/null; then
    echo "[FEHLER] Python3 nicht gefunden."
    echo "         Bitte installiere Python 3.11+ von https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_VERSION" -lt 11 ]; then
    echo "[WARNUNG] Python 3.11+ empfohlen. Gefunden: 3.${PYTHON_VERSION}"
fi

# Virtuelle Umgebung erstellen
echo "[1/3] Erstelle virtuelle Umgebung 'EDV4_TK'..."
python3 -m venv EDV4_TK

if [ ! -d "EDV4_TK" ]; then
    echo "[FEHLER] Virtuelle Umgebung konnte nicht erstellt werden."
    exit 1
fi

# Abhängigkeiten installieren
echo "[2/3] Installiere Abhängigkeiten..."
EDV4_TK/bin/pip install --upgrade pip --quiet
EDV4_TK/bin/pip install -r requirements.txt --quiet

# Kamera-Zugriff prüfen (optional)
echo "[3/3] Prüfe Kamera-Zugriff..."
EDV4_TK/bin/python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('           Kamera gefunden.')
    cap.release()
else:
    print('           Keine Kamera gefunden – USB-Kabel prüfen.')
" 2>/dev/null

echo ""
echo "========================================"
echo "  Setup abgeschlossen!"
echo "========================================"
echo ""
echo "  Umgebung aktivieren:"
echo "  source EDV4_TK/bin/activate"
echo ""
echo "  Programm starten:"
echo "  python main.py"
echo ""
