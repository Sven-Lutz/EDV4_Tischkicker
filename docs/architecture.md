# Architektur – EDV4 Kicker GT3

## Grundprinzip

Das System verarbeitet jeden Kamera-Frame in Echtzeit und leitet daraus
alle Spielstatistiken ab. Es gibt keine Datenbank und kein Training –
alles läuft live im Arbeitsspeicher der Session.

## Geplante Komponenten

| Komponente                   | Branch                   | Verantwortung                      |
| ---------------------------- | ------------------------ | ---------------------------------- |
| `VideoSource`                | `feature/video-source`   | Kamerazugriff, Frame-Lieferung     |
| `BallDetector`               | `feature/ball-detection` | HSV-Filter, x/y-Position pro Frame |
| `GameEvent` / `BallPosition` | `feature/game-events`    | Gemeinsame Datenklassen            |
| `GoalDetector`               | `feature/goal-detection` | Torzonenerkennung, Spielstand      |
| `Statistics`                 | `feature/statistics`     | Geschwindigkeit, Heatmap, Zonen    |
| `Controller`                 | `feature/controller`     | Orchestrierung des Hauptloops      |
| GUI                          | `feature/gui`            | Live-Dashboard, Start-Screen       |

## Geplanter Datenfluss
```
Webcam
  → VideoSource      (liefert Frames)
  → BallDetector     (erkennt Ball → BallPosition)
  → GoalDetector     (prüft auf Tor → GameEvent)
  → Statistics       (berechnet Kennzahlen)
  → GUI              (zeigt alles live an)
```

## Abhängigkeiten zwischen Komponenten

`GameEvent` und `BallPosition` sind die gemeinsame Schnittstelle –
sie werden zuerst definiert, damit alle anderen Komponenten parallel
entwickelt werden können.
```
GameEvent / BallPosition  ← wird zuerst fertiggestellt
        ↓
BallDetector   GoalDetector   Statistics   GUI
        ↓
    Controller  ← verdrahtet alles, kommt zuletzt
```

## Offene Entscheidungen

- Welches GUI-Framework? (Tkinter, PyQt, OpenCV-Overlay)
- HSV-Werte für den Ball – müssen am echten Tisch kalibriert werden
- Definition der Torzonen – Pixelgrenzen abhängig von Kameraposition
