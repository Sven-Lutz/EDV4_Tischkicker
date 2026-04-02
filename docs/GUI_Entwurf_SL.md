# Kicker GT3 – GUI Entwurf

**Design-Sprache:** Dunkles Cockpit · Porsche-Rot (#C41E3A) als Akzent · Schwarz/Anthrazit

---

## Screen 1 – Start-Screen

```
┌─────────────────────────────────────────────┐
│  KICKER GT3                      EDV4 · 2026 │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌──────────────┐        │
│  │   MODUS      │  │   MODUS      │        │
│  │  1 gegen 1   │  │  2 gegen 2   │        │
│  └──────────────┘  └──────────────┘        │
│  (aktiver Modus rot hervorgehoben)          │
│                                             │
│  ┌─────────────┐  vs  ┌─────────────┐      │
│  │ TEAM LINKS  │      │ TEAM RECHTS │      │
│  │             │      │             │      │
│  │ [Spieler 1] │      │ [Spieler 1] │      │
│  │ [Spieler 2] │      │ [Spieler 2] │      │
│  │ (bei 2v2)   │      │ (bei 2v2)   │      │
│  └─────────────┘      └─────────────┘      │
│                                             │
│  Namen sind optional                        │
│                                             │
│       [ SPIEL STARTEN ]                     │
│                                             │
└─────────────────────────────────────────────┘
```

**Verhalten:**
- Modus-Auswahl aktiviert / deaktiviert zweiten Spieler-Slot
- Namen optional – läuft auch als "Links vs Rechts"
- Klick auf "Spiel starten" → Screen 2

---

## Screen 2 – Live-Dashboard (während des Spiels)

```
┌─────────────────────────────────────────────────────┐
│  KICKER GT3                          ● LIVE          │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ┌─────────────────────────────────────────────┐  │
│   │   Sven & Jonas      08:42      Max & Tim    │  │
│   │        3              –              1       │  │
│   │      (ROT)                        (WEISS)   │  │
│   └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Max Geschw│ │Akt.Geschw│ │ Abpralle │ │Schüsse │ │
│  │ 8.4 m/s  │ │ 3.1 m/s  │ │    24    │ │   17   │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                     │
│  ┌──────────────────────────┐  ┌──────────────────┐ │
│  │ Spielfeld & Trajektorie  │  │ Ereignisse       │ │
│  │                          │  │                  │ │
│  │  [Kicker-Feld mit Ball-  │  │ 08:21 Tor Links  │ │
│  │   Pfad als Overlay]      │  │       3:1        │ │
│  │                          │  │ 07:44 Höchstg.   │ │
│  │ Heatmap nach Stangen:    │  │       8.4 m/s    │ │
│  │ [Zone-Rechtecke eingefärbt  │ 06:03 Tor Links  │ │
│  │  von grün → rot je nach  │  │       2:1        │ │
│  │  Ballaufenthaltszeit]    │  │ 04:17 Tor Rechts │ │
│  │                          │  │       1:1        │ │
│  │ Top-Scorer Stange:       │  │                  │ │
│  │ Sturm 3 | Mitt 1 | ...   │  │                  │ │
│  └──────────────────────────┘  │ [ SPIEL BEENDEN ]│ │
│                                └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Verhalten:**
- Alle Werte aktualisieren sich live
- Heatmap wächst kontinuierlich während des Spiels
- Trajektorie zeigt die letzten N Frames des Balls
- "Spiel beenden" → Screen 3

---

## Screen 3 – Zusammenfassung (nach dem Spiel)

```
┌─────────────────────────────────────────────────────┐
│  KICKER GT3                    SPIELZUSAMMENFASSUNG  │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ┌─────────────────────────────────────────────┐  │
│   │  Sven & Jonas    12:34 min    Max & Tim     │  │
│   │       3      –      1                       │  │
│   │    SIEGER                                   │  │
│   └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Max Geschw│ │  Schüsse │ │ Abpralle │ │Kontakte│ │
│  │ 8.4 m/s  │ │    34    │ │    61    │ │  248   │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                     │
│  ┌──────────────────────────┐  ┌──────────────────┐ │
│  │ Heatmap (gesamtes Spiel) │  │ Torchronik       │ │
│  │                          │  │                  │ │
│  │  [Stangen-Zonen eingefärbt  │ 02:55 Tor Links  │ │
│  │   nach Gesamtaufenthalt] │  │       1:0        │ │
│  │                          │  │ 04:17 Tor Rechts │ │
│  │ Top-Scorer Stange:       │  │       1:1        │ │
│  │ Sturm 3 | Mitt 1 | ...   │  │ 06:03 Tor Links  │ │
│  │                          │  │       2:1        │ │
│  │                          │  │ 07:44 Höchstg.   │ │
│  │                          │  │       8.4 m/s    │ │
│  │                          │  │ 08:21 Tor Links  │ │
│  │                          │  │       3:1        │ │
│  └──────────────────────────┘  │                  │ │
│                                │ [NEUES SPIEL]    │ │
│                                │ [BEENDEN]        │ │
│                                └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Verhalten:**
- Keine Daten werden gespeichert – Session-based
- "Neues Spiel" → zurück zu Screen 1
- "Beenden" → Anwendung schließt sich

---

## Design-Tokens

| Element | Wert |
|---------|------|
| Hintergrund | `#0a0a0a` |
| Oberfläche | `#111111` |
| Akzent (Porsche-Rot) | `#C41E3A` |
| Border | `#222222` |
| Text primär | `#ffffff` |
| Text sekundär | `#555555` |
| Ball | `#ff6b00` (Orange) |
| Heatmap kalt | `#1a2e1a` (Dunkelgrün) |
| Heatmap heiß | `#C41E3A` (Rot) |

---

## Flow

```
Start-Screen
     │
     │  Spiel starten
     ▼
Live-Dashboard
     │
     │  Spiel beenden
     ▼
Zusammenfassung
     │
     ├── Neues Spiel → Start-Screen
     └── Beenden → App schließt
```

---

*Kicker GT3 – EDV4 Projekt · 2026*
