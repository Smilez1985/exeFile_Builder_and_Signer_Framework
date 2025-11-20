import subprocess
import sys
import shutil
import importlib.util
import pkg_resources
import zipfile
import io
import os
import requests
from pathlib import Path
from src.utils.helpers import log
from src.core.network import NetworkGuard

class EnvironmentManager:
    """
    Kümmert sich um die Vorbereitung der Build-Umgebung.
    Managed Python-Dependencies, OpenSSL und Signing-Tools.
    """
    
    def __init__(self):
        self.network = NetworkGuard()
        self.tools_dir = Path("tools")
        self.tools_dir.mkdir(exist_ok=True)

    def prepare_environment(self, project_path: Path):
        log.info(f"Analysiere Umgebung in: {project_path}")
        
        # 1. System Tools (OpenSSL & OSSLSIGNCODE)
        self._ensure_openssl()
        self._ensure_osslsigncode()

        # 2. Python Check
        if self._is_venv():
            log.debug("Aktives Virtual Environment (VENV) erkannt.")
        else:
            log.warning("ACHTUNG: Kein aktives VENV erkannt. Installation erfolgt global.")

        # 3. Dependencies
        if (project_path / "Requirements.txt").exists():
            self._install_pip(project_path / "Requirements.txt")

    def _ensure_osslsigncode(self):
        """Lädt osslsigncode und ALLE Abhängigkeiten (DLLs) herunter."""
        exe_path = self.tools_dir / "osslsigncode.exe"
        
        # Check: Existiert die Exe und ist sie größer als 0 Byte?
        if exe_path.exists() and exe_path.stat().st_size > 0:
            log.debug("Signier-Tool (osslsigncode) scheint vorhanden zu sein.")
            return

        log.warning("Signier-Tool (osslsigncode) fehlt oder ist beschädigt. Starte Download...")
        self.network.wait_for_network()

        # Offizieller Link zu Release 2.10 (MinGW Build mit DLLs)
        url = "https://github.com/mtrojnar/osslsigncode/releases/download/2.10/osslsigncode-2.10-windows-x64-mingw.zip"
        
        try:
            log.info("Lade osslsigncode herunter...")
            r = requests.get(url)
            r.raise_for_status()
            
            log.info("Entpacke Tool und DLLs...")
            found_exe = False
            
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for file_info in z.infolist():
                    # Wir ignorieren Ordner, wir wollen die Dateien direkt in 'tools/' haben (Flatten)
                    if file_info.is_dir():
                        continue
                        
                    filename = os.path.basename(file_info.filename)
                    if not filename:
                        continue
                    
                    # Wir brauchen die .exe UND alle .dll Dateien (Abhängigkeiten)
                    if filename.lower().endswith(('.exe', '.dll')):
                        target_path = self.tools_dir / filename
                        with z.open(file_info) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        
                        if filename == "osslsigncode.exe":
                            found_exe = True
                            log.debug(f"Entpackt: {filename}")

            if found_exe and exe_path.exists():
                log.success(f"Signier-Tool installiert in: {self.tools_dir}")
            else:
                raise FileNotFoundError("osslsigncode.exe war nicht im ZIP enthalten!")
                
        except Exception as e:
            log.error(f"Download/Entpacken fehlgeschlagen: {e}")
            # Aufräumen bei Fehler
            if exe_path.exists():
                exe_path.unlink()
            
    def _ensure_openssl(self):
        if shutil.which("openssl"):
            log.debug("OpenSSL ist verfügbar.")
            return
            
        log.warning("OpenSSL fehlt. Versuche Installation via Winget...")
        self.network.wait_for_network()
        try:
            cmd = ["powershell", "-Command", "winget install -e --id ShiningLight.OpenSSL --accept-source-agreements --accept-package-agreements --silent"]
            subprocess.run(cmd, check=True)
            log.success("OpenSSL Installation angestoßen.")
        except Exception as e:
            log.error(f"OpenSSL Install fehlgeschlagen: {e}")

    def _is_venv(self) -> bool:
        return (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

    def _check_package_installed(self, package_name: str) -> bool:
        clean_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].strip()
        if importlib.util.find_spec(clean_name) is not None: return True
        try: pkg_resources.get_distribution(clean_name); return True
        except: return False

    def _install_pip(self, req_file: Path):
        log.info("Prüfe Python Dependencies...")
        to_install = []
        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not self._check_package_installed(line):
                        to_install.append(line)
        except: pass

        if not to_install:
            log.success("Dependencies aktuell.")
            return

        log.info(f"Installiere {len(to_install)} Pakete...")
        self.network.wait_for_network()
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + to_install)
