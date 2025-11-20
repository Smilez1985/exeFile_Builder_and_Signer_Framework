import subprocess
import sys
import shutil
import importlib.util
import pkg_resources
import zipfile
import io
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
        """Lädt osslsigncode herunter, falls es fehlt."""
        exe_path = self.tools_dir / "osslsigncode.exe"
        if exe_path.exists():
            # Kurzer Test, ob die Datei auch ausführbar/gültig ist (Größe > 0)
            if exe_path.stat().st_size > 0:
                log.debug("Signier-Tool (osslsigncode) ist bereit.")
                return
            else:
                log.warning("Signier-Tool ist beschädigt (0 Byte). Lade neu...")

        log.warning("Signier-Tool (osslsigncode) fehlt. Starte Download...")
        self.network.wait_for_network()

        # NEUER LINK (Offizielles Repo, Version 2.10)
        url = "https://github.com/mtrojnar/osslsigncode/releases/download/2.10/osslsigncode-2.10-windows-x64-mingw.zip"
        
        try:
            log.info("Lade osslsigncode herunter...")
            r = requests.get(url)
            r.raise_for_status()
            
            log.info("Entpacke Tool...")
            found = False
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                # Wir suchen die .exe im Zip (egal in welchem Unterordner)
                for file in z.namelist():
                    if file.endswith("osslsigncode.exe"):
                        with z.open(file) as source, open(exe_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        found = True
                        break
            
            if found and exe_path.exists():
                log.success(f"Signier-Tool installiert: {exe_path}")
            else:
                raise FileNotFoundError("osslsigncode.exe nicht im Zip gefunden")
                
        except Exception as e:
            log.error(f"Download von osslsigncode fehlgeschlagen: {e}")
            # Wir löschen die kaputte Datei, damit beim nächsten Start ein neuer Versuch unternommen wird
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
