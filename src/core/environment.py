import subprocess
import sys
import shutil
import zipfile
import os
import importlib.util
from pathlib import Path
from typing import List, Optional

from src.utils.logger import log
from src.core.network import NetworkGuard

class EnvironmentManager:
    """
    Enterprise Environment Manager.
    Verantwortlich für:
    - Sicherstellung der Build-Tools (OpenSSL, osslsigncode)
    - Management der Python-Dependencies (pip/poetry)
    - Validierung der Laufzeitumgebung (VENV)
    """
    
    # Konstanten für externe Tools
    OSSLSIGNCODE_URL = "https://github.com/mtrojnar/osslsigncode/releases/download/2.10/osslsigncode-2.10-windows-x64-mingw.zip"
    # Optional: SHA256 Hash für maximale Sicherheit (hier als Platzhalter)
    OSSLSIGNCODE_HASH = None 

    def __init__(self):
        self.network = NetworkGuard()
        self.tools_dir = Path("tools")
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    def prepare_environment(self, project_path: Path) -> bool:
        """
        Hauptmethode: Bereitet die gesamte Umgebung vor.
        Gibt True zurück, wenn alles bereit ist.
        """
        log.info(f"Initialisiere Umgebung in: {project_path}")
        
        try:
            # 1. System Tools prüfen & laden
            if not self._ensure_system_tools():
                log.error("System-Tools konnten nicht bereitgestellt werden.")
                return False

            # 2. Python Umgebung prüfen
            if not self._check_venv():
                # Wir warnen nur, da der Launcher das VENV normalerweise erzwingt.
                # In einer strikten Enterprise-Umgebung würden wir hier abbrechen.
                log.warning("Kritisch: Skript läuft nicht in einem Virtual Environment!")

            # 3. Dependencies installieren
            self._install_dependencies(project_path)
            
            return True

        except Exception as e:
            log.error(f"Environment-Fehler: {e}")
            return False

    def _ensure_system_tools(self) -> bool:
        """Prüft und lädt notwendige Binaries (OpenSSL, osslsigncode)."""
        
        # A) OpenSSL Check
        if not shutil.which("openssl"):
            log.warning("OpenSSL nicht im PATH gefunden. Versuche Installation via Winget...")
            if not self._install_openssl_via_winget():
                log.error("OpenSSL fehlt. Bitte manuell installieren.")
                return False
        else:
            log.debug("OpenSSL ist verfügbar.")

        # B) Osslsigncode Check (Lokal im tools/ Ordner)
        ossl_exe = self.tools_dir / "osslsigncode.exe"
        
        # Validierung: Existiert Datei und ist sie größer als 0 Bytes?
        if ossl_exe.exists() and ossl_exe.stat().st_size > 0:
            log.debug("Signier-Tool (osslsigncode) ist bereit.")
            return True

        # Download Starten
        log.info("Lade Signier-Tool (osslsigncode) herunter...")
        zip_path = self.tools_dir / "tool_download.zip"
        
        # Robuster Download via NetworkGuard
        if self.network.download_file(self.OSSLSIGNCODE_URL, zip_path, self.OSSLSIGNCODE_HASH):
            # Entpacken
            return self._extract_tools(zip_path)
        else:
            log.error("Download des Signier-Tools fehlgeschlagen.")
            return False

    def _extract_tools(self, zip_path: Path) -> bool:
        """Entpackt die Tools flach in das tools-Verzeichnis."""
        try:
            log.info("Entpacke Tools...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                for file_info in z.infolist():
                    if file_info.is_dir():
                        continue
                    
                    filename = os.path.basename(file_info.filename)
                    # Wir brauchen die EXE und alle DLLs
                    if filename.lower().endswith(('.exe', '.dll')):
                        target = self.tools_dir / filename
                        with z.open(file_info) as source, open(target, "wb") as dest:
                            shutil.copyfileobj(source, dest)
            
            # Cleanup Zip
            zip_path.unlink()
            
            if (self.tools_dir / "osslsigncode.exe").exists():
                log.success(f"Tools installiert in: {self.tools_dir.absolute()}")
                return True
            else:
                log.error("osslsigncode.exe war nicht im Archiv enthalten!")
                return False

        except Exception as e:
            log.error(f"Fehler beim Entpacken: {e}")
            return False

    def _install_openssl_via_winget(self) -> bool:
        """Versucht OpenSSL via Windows Package Manager zu installieren."""
        self.network.wait_for_network()
        try:
            cmd = [
                "powershell", 
                "-Command", 
                "winget install -e --id ShiningLight.OpenSSL --accept-source-agreements --accept-package-agreements --silent"
            ]
            log.info("Starte Winget Installation für OpenSSL...")
            # Timeout von 5 Minuten für Installation
            subprocess.run(cmd, check=True, timeout=300, capture_output=True)
            log.success("OpenSSL Installation angestoßen (Neustart ggf. erforderlich).")
            return True
        except subprocess.TimeoutExpired:
            log.error("Timeout bei OpenSSL Installation.")
            return False
        except subprocess.CalledProcessError as e:
            log.warning(f"Winget Installation fehlgeschlagen (Code {e.returncode}).")
            return False

    def _check_venv(self) -> bool:
        """Prüft strikt auf aktives VENV."""
        is_venv = (hasattr(sys, 'real_prefix') or
                   (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
        return is_venv

    def _install_dependencies(self, project_path: Path):
        """Installiert Python Dependencies (requirements.txt)."""
        req_file = project_path / "Requirements.txt"
        
        if not req_file.exists():
            return

        log.info("Prüfe Python Dependencies...")
        
        # Smart Check: Müssen wir überhaupt installieren?
        if self._are_requirements_met(req_file):
            log.success("Dependencies sind bereits aktuell.")
            return

        self.network.wait_for_network()
        
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--disable-pip-version-check"]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            log.success("Dependencies erfolgreich installiert.")
        except subprocess.CalledProcessError as e:
            log.error(f"Pip Install fehlgeschlagen: {e}")
            raise

    def _are_requirements_met(self, req_file: Path) -> bool:
        """Prüft, ob Pakete fehlen, ohne pip aufzurufen (schneller)."""
        try:
            with open(req_file, 'r') as f:
                requirements = [
                    line.strip() for line in f 
                    if line.strip() and not line.startswith('#')
                ]
            
            for req in requirements:
                # Einfacher Namens-Check (ignoriert Versionen für Speed, außer == ist dabei)
                pkg_name = req.split('==')[0].split('>=')[0].strip()
                if not importlib.util.find_spec(pkg_name):
                    return False
            return True
        except Exception:
            return False # Im Zweifel neu installieren
