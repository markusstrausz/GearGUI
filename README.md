# Zahnrad Studio

Ein benutzerfreundliches grafisches Tool zum Erstellen von Zahnrädern und Getrieben für **OpenSCAD**. Perfekt für Maker, 3D-Druck-Enthusiasten und Ingenieure.

![Zahnrad Studio GUI](Bilder/GUI.png)

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

| Stirnradpaar | Herringbone |
|:---:|:---:|
| ![Stirnradpaar](Bilder/ScStirnradpaar.png) | ![Herringbone](Bilder/Herringbone.png) |

| Zahnstange | Wurmrad |
|:---:|:---:|
| ![Zahnstange](Bilder/Zahnstange.png) | ![Wurmrad](Bilder/Wurmrad.png) |

| Innenzahnrad | Planetengetriebe |
|:---:|:---:|
| ![Innenzahnrad](Bilder/Innenzahnrad.png) | ![Planetengetriebe](Bilder/Planetemgetriebe.png) |

| Tellerrad | |
|:---:|:---:|
| ![Tellerrad](Bilder/Tellerrad.png) | |

## 🚀 Schnellstart

### Voraussetzungen

- **OpenSCAD** installiert ([Download](https://openscad.org/downloads.html))
- Python 3.10 oder neuer (nur für den Skript-Modus)
- Optional: `gears.scad` Bibliothek von [chrisspen/gears](https://github.com/chrisspen/gears)

### Verwendung

#### Als fertige EXE (empfohlen für Windows)

Im Ordner `dist/` liegt eine vorkompilierte `gear.exe`, die direkt ohne Python-Installation gestartet werden kann.

#### Als Python-Skript

```bash
python gear.py
```

Für Vorschau, Export und das direkte Öffnen der Modelle sollte OpenSCAD installiert und im System erreichbar sein.

## 🔧 Technik

- Python-Anwendung mit Tkinter-Oberfläche
- Berechnungslogik in [gear_math.py](gear_math.py)
- Hauptanwendung in [gear.py](gear.py)
- Tests in [tests/](tests/)
- OpenSCAD-Bibliotheken über [gears-master/](gears-master/) und [BOSL2-master/](BOSL2-master/)
- EXE-Erstellung mit PyInstaller über `make_exe.bat`

## 🧪 Entwicklung

Für die Codepflege sind in [requirements-dev.txt](requirements-dev.txt) Werkzeuge wie **Black** und **Ruff** hinterlegt. Mit [smoke_test.py](smoke_test.py) sowie den Tests in [tests/](tests/) stehen einfache Prüfpfade für Berechnungen und Regressionen bereit.
