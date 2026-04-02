#!/bin/bash
# EDV4 Kicker GT3 – Start (Mac / Linux)

if [ ! -d "EDV4_TK" ]; then
    echo "[FEHLER] Virtuelle Umgebung 'EDV4_TK' nicht gefunden."
    echo "         Bitte zuerst ./setup.sh ausführen."
    exit 1
fi

source EDV4_TK/bin/activate
python main.py "$@"
