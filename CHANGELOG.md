# Changelog

Alle nennenswerten Änderungen am **ExeFile Builder & Signer Framework** werden in dieser Datei dokumentiert.

## [1.1.0] - 2025-11-30 - "Enterprise Edition"

Dieses Release markiert den Übergang von einem Skript-basierten Tool zu einem robusten Enterprise-Framework.

### 🚀 Neue Features
* **Binary Signing Engine (`osslsigncode`):**
    * Ersetzt die fehleranfälligen PowerShell-Skripte durch das Industriestandard-Tool `osslsigncode`.
    * Beseitigt Probleme mit `ExecutionPolicy`, Encoding (Umlaute) und Berechtigungen.
    * Unterstützt OpenSSL 3.0+ Legacy Provider automatisch.
* **Smart Config Mode (Goldstandard):**
    * **Intelligente Erkennung:** Ziehen Sie eine externe Python-Konfigurationsdatei (z.B. `build_windows_exe.py`) in die Asset-Liste der GUI.
    * Das Framework lädt automatisch die `PYINSTALLER_CMD_ARGS` und führt den Build exakt nach diesen Vorgaben aus.
    * **Kontext-Sensitiv:** Der Build wird im Root-Verzeichnis des externen Projekts ausgeführt, damit relative Pfade funktionieren.
* **Enterprise Network Guard:**
    * Implementierung einer "Ping-Loop", die aktiv auf eine Internetverbindung wartet, bevor Downloads starten.
    * Automatischer Download und Entpacken fehlender Tools (inkl. DLLs) mit Integritätsprüfung.
* **Self-Healing Launcher:**
    * Der `launcher.ps1` erzwingt nun die Nutzung eines isolierten `VENV`.
    * Repariert automatisch defekte Python-Umgebungen oder fehlende Dependencies (`PyYAML`, `pywin32`).

### 🛠 Verbesserungen
* **Builder Core:**
    * **Crash Dumps:** Bei Fehlern wird nun das vollständige PyInstaller-Log (stderr) ausgegeben, statt nur "Exit Code 1".
    * **Path Sanitizer:** Wandelt relative Pfade aus externen Configs automatisch in absolute Pfade um.
* **Logging:**
    * Neues `EnterpriseLogger` Modul mit Log-Rotation (max. 10MB), Thread-Safety und UTF-8 Zwang.
* **Distribution:**
    * Das finale Paket enthält nun automatisch: Signierte EXE, Public Key (.cer), Install-Skript (.bat) und eine `ANLEITUNG_LESEN.txt`.

### 🐛 Bug Fixes
* Behoben: `ModuleNotFoundError: No module named 'yaml'` durch erzwungene Hidden Imports und korrekte `Requirements.txt` Versionierung (`PyYAML==6.0.3`).
* Behoben: Absturz beim Signieren durch fehlende DLLs (Arbeitsverzeichnis-Fix im Signer).
* Behoben: 404 Fehler beim Tool-Download (Update auf `mtrojnar` Repository).
* Behoben: Namenskonflikte (z.B. `.exe.exe`) durch intelligente Namensbereinigung im Builder.
