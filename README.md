# exeFile Builder & Signer Framework

Ein modulares, professionelles Framework zur Automatisierung des Build-Prozesses von Python zu Windows Executables (.exe). 
Es kombiniert Dependency-Management, Zertifikatserstellung (Code Signing) und PyInstaller-Kapselung in einer robusten Pipeline.

## 🚀 Features

* **Automatisches Environment Management:** * Erkennt `requirements.txt` oder `poetry` (pyproject.toml).
    * Installiert fehlende Abhängigkeiten automatisch.
    * **Smart Check:** Prüft, ob Pakete bereits existieren, um unnötige Installationen zu vermeiden.
    * **Network Guard:** Wartet automatisch auf eine aktive Internetverbindung ("Ping Loop"), bevor Downloads starten.
      
* **Zertifikats-Management:**
    * Erstellt automatisch Self-Signed Code Signing Zertifikate (.pfx).
    * Nutzt native PowerShell-Befehle (keine externe OpenSSL Abhängigkeit nötig).
    * Generiert Installations-Scripte (`install_cert.bat`) für Endanwender.
      
* **Build Wrapper:**
    * Abstrahiert PyInstaller Komplexität.
    * Unterstützt OneFile, Console/NoConsole, Icons.
      
* **Signierung:**
    * Signiert die fertige .exe via Authenticode.
    * Setzt Timestamp-Server für langfristige Gültigkeit.
      
* **GUI & CLI:**
    * Verfügt über eine moderne Dark-Mode GUI (`main_gui.py`).
    * Sowie einen CLI-Modus (`main.py`).

## 📂 Projektstruktur

```text
.
├── main.py                 # CLI Einstiegspunkt
├── main_gui.py             # GUI Einstiegspunkt
├── Requirements.txt        # Dependencies des Frameworks selbst
├── README.md
└── src
    ├── core
    │   ├── builder.py      # PyInstaller Wrapper
    │   ├── certs.py        # Zertifikats-Logik (PowerShell)
    │   ├── environment.py  # Dependency Manager (Pip/Poetry)
    │   ├── network.py      # Network Guard (Ping Loop)
    │   ├── orchestrator.py # Hauptlogik / Pipeline Controller
    │   └── signer.py       # Authenticode Signer
    ├── ui
    │   └── gui.py          # Tkinter GUI Implementierung
    └── utils
        └── helpers.py      # Logging und Hilfsfunktionen
```
🛠 Installation
Repository klonen.

Sicherstellen, dass Python 3.10+ installiert ist.

Framework-Abhängigkeiten installieren:

```Bash

pip install -r Requirements.txt

```
(Hinweis: Das Framework kann fehlende Projektabhängigkeiten später selbst nachladen).

💻 Nutzung
Option A: Grafische Oberfläche (GUI)
Starten Sie das Tool bequem per Mausklick:
```Bash

python main_gui.py
```
Wählen Sie Script-Datei, Icon und Namen aus und klicken Sie auf "START BUILD & SIGN". Der Output wird direkt im Fenster angezeigt.

Option B: Kommandozeile (CLI)
Für Server oder schnelle Builds:
```Bash

python main.py
```
🔑 Zertifikate & Trust
Da wir selbst-signierte Zertifikate erstellen, vertraut Windows diesen standardmäßig nicht. 
Das Framework erstellt im builds/-Ordner automatisch eine install_cert.bat. 
Führen Sie diese einmalig als Administrator aus, um das Zertifikat in den "Trusted People" Store zu importieren. 
Danach starten alle signierten Anwendungen ohne Warnung.

📝 Lizenz
MIT License - Copyright (c) 2025 Smilez1985


### **JSON Memory Prompt**

```json
{
  "timestamp": "2025-11-20T18:56:00",
  "project_context": "Lokaler KI-Assistent & exeFile Builder Framework",
  "decisions": [
    {
      "topic": "Framework Architektur",
      "details": "Das exeFile Framework ist modular aufgebaut (Builder, Signer, Certs, Environment, Orchestrator). Es nutzt nun eine Tkinter GUI (Dark Mode) und hat robuste Netzwerk-Checks (Ping Loop) sowie intelligente Dependency-Checks implementiert."
    },
    {
      "topic": "Environment Handling",
      "details": "Die Klasse EnvironmentManager in src/core/environment.py wurde erweitert. Sie prüft nun vor pip-Aufrufen mittels importlib/pkg_resources, ob Pakete fehlen, und wartet mittels NetworkGuard aktiv auf eine Internetverbindung."
    },
    {
      "topic": "GitHub Workflow",
      "details": "User wurde instruiert, Ordner mittels 'git mv' zu verschieben, um die Historie zu wahren."
    }
  ],
  "user_preferences": {
    "language": "Deutsch",
    "output_format": "Vollständige Dateien, keine Platzhalter",
    "framework_style": "Wrapper-basiert, nativ (keine unnötigen 3rd Party Libs für GUI)"
  },
  "current_status": "GUI (main_gui.py) und README.md erstellt. Environment.py gehärtet. Framework ist vollständig einsatzbereit."
}
