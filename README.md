# GearGUI - Zahnrad Studio für OpenSCAD

Ein benutzerfreundliches grafisches Tool zum Erstellen von Zahnrädern und Getrieben für **OpenSCAD**. Perfekt für Maker, 3D-Druck-Enthusiasten und Ingenieure.

![GearGUI Screenshot](screenshot.png) <!-- Hier später ein Screenshot einfügen -->

## ✨ Features

- **Unterstützte Zahnrad-Typen:**
  - Stirnrad (Spur Gear)
  - Herringbone (Doppel-Schrägverzahnung)
  - Zahnstange + Ritzel (Rack & Pinion)
  - Schnecke + Schneckenrad (Worm Gear)
  - Hohlrad (Ring Gear)
  - Planetengetriebe (Planetary Gear Set)
  - Kegelrad (Bevel Gear)

- **Echtzeit-Vorschau** mit Kamera-Steuerung und Animation
- **Automatische Berechnung** von Achsabständen, Übersetzungsverhältnissen und Montagebedingungen
- **Mehrsprachig**: Deutsch, Englisch, Russisch
- **Export** als `.scad`, `.stl`, `.dxf` und mehr
- **Direktes Öffnen** in OpenSCAD
- **Fertige EXE** für Windows (keine Python-Installation nötig)

## 📸 Screenshots

*(Füge hier Screenshots ein – z. B. Hauptfenster, Planetengetriebe-Vorschau, Herringbone)*

## 🚀 Schnellstart

### 1. Voraussetzungen
- **OpenSCAD** installiert ([Download](https://openscad.org/downloads.html))
- Optional: `gears.scad` Bibliothek von [chrisspen/gears](https://github.com/chrisspen/gears)

### 2. Verwendung

#### Als Python-Skript
```bash
pip install -r requirements.txt
python gear.py
