# ExeFile Builder & Signer Framework (Enterprise Edition)

Ein professionelles, modulares Framework zur Automatisierung des Build-Prozesses von Python zu signierten Windows Executables (.exe). 
Es kombiniert robustes Dependency-Management, Zertifikatserstellung (Code Signing) und PyInstaller-Kapselung in einer "Self-Healing" Pipeline.

## 🚀 Features

* **Automatisches Environment Management:**
    * Erstellt und verwaltet ein isoliertes Virtual Environment (`.venv`).
    * **Self-Healing:** Lädt fehlende Tools (`osslsigncode`, `OpenSSL`) und Python-Pakete automatisch nach.
    * **Network Guard:** Wartet bei Verbindungsabbrüchen automatisch auf das Internet ("Ping Loop").
* **Zertifikats-Management:**
    * Erstellt automatisch Self-Signed Code Signing Zertifikate (RSA 4096 bit).
    * Unterstützt den Import bestehender PFX-Dateien.
    * Generiert `install_cert.bat` für die einfache Installation beim Endkunden.
* **Build Modi:**
    * **GUI-Modus:** Einfache Konfiguration per Klick für Standard-Skripte.
    * **Config-Modus (Goldstandard):** Akzeptiert externe Python-Konfigurationsdateien (z.B. `build_windows_exe.py`) via Drag & Drop für komplexe Projekte mit spezifischen Import-Regeln.
* **Signierung:**
    * Signiert die fertige .exe nativ mit `osslsigncode` (kein PowerShell nötig).
    * Setzt Timestamp-Server für langfristige Gültigkeit.

## 📂 Projektstruktur

```text
.
├── start_launcher.bat      # DER EINSTIEGSPUNKT (Doppelklick hier!)
├── launcher.ps1            # Setup- & Start-Logik (PowerShell)
├── main_gui.py             # GUI Einstiegspunkt
├── Requirements.txt        # Definierte Versionen (PyYAML==6.0.3 etc.)
├── README.md
├── CHANGELOG.md
└── src
    ├── core
    │   ├── builder.py      # PyInstaller Wrapper (mit Config-Support)
    │   ├── certs.py        # Zertifikats-Logik
    │   ├── environment.py  # Dependency & Tool Manager
    │   ├── network.py      # Network Guard (Ping Loop)
    │   ├── orchestrator.py # Pipeline Controller
    │   └── signer.py       # Binary Signer (osslsigncode)
    ├── ui
    │   └── gui.py          # Tkinter GUI (Dark Mode)
    └── utils
        └── logger.py       # Enterprise Logging

```
* **🛠 Installation & Start**

Es ist keine manuelle Installation von Python oder Git erforderlich. Der Launcher übernimmt alles.

* Repository klonen oder herunterladen.

* Doppelklick auf start_launcher.bat.

* Zurücklehnen. Das Framework richtet sich selbst ein.

* **💻 Nutzung**
  
**Option A: Standard Build (Einfach)**
* Für einfache Skripte ohne spezielle Anforderungen.

* Ziehe dein Python-Script (.py) in das Feld "Start Script".

* (Optional) Ziehe ein Icon (.ico) in das Icon-Feld.

* Klicke auf "🚀 START BUILD & SIGN".

**Option B: Config Build (Goldstandard / Profi)**
* Für komplexe Projekte (wie llm_conversion_framework), die eine eigene Build-Konfiguration mitbringen.

* Ziehe das Haupt-Script (z.B. orchestrator/main.py) in das Feld "Start Script".

* Ziehe die Konfigurationsdatei des Projekts (z.B. scripts/build_windows_exe.py) in die Liste "Zusatz-Dateien & Ordner" (Assets).

* Klicke auf "🚀 START BUILD & SIGN".

* -> Das Framework erkennt die Konfiguration automatisch ("Smart Scan") und nutzt exakt die dort definierten Argumente (Hidden Imports, Pfade, etc.).

* **🔑 Zertifikate & Weitergabe** 
Das Framework erstellt im Ordner builds/dist/ ein komplettes Distributions-Paket.

**Inhalt des Pakets:**

* DeineApp.exe (Signiert)

* DeinCert.cer (Öffentlicher Schlüssel)

* install_cert.bat (Installations-Skript)

* ANLEITUNG_LESEN.txt (Hilfe für den Nutzer)

**Wichtig für Empfänger: Da wir selbst-signierte Zertifikate nutzen, muss der Empfänger einmalig die install_cert.bat als Administrator ausführen, damit Windows der Anwendung vertraut.**

* **📝 Lizenz**
MIT License - Copyright (c) 2025 Smilez1985
