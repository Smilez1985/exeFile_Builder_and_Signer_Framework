import subprocess
import sys
import shutil
import importlib.util
import pkg_resources
from pathlib import Path
from src.utils.helpers import log
from src.core.network import NetworkGuard

class EnvironmentManager:
    """
    Kümmert sich um die Vorbereitung der Build-Umgebung.
    Managed Python-Dependencies (Pip/Poetry) UND System-Tools (OpenSSL).
    """
    
    def __init__(self):
        self.network = NetworkGuard()

    def prepare_environment(self, project_path: Path):
        """
        Hauptmethode: Prüft alles (System Tools + Python Packages).
        """
        log.info(f"Analysiere Umgebung in: {project_path}")
        
        # 1. System Tools prüfen (OpenSSL)
        self._ensure_system_tools()

        # 2. Python Environment prüfen
        if self._is_venv():
            log.debug("Aktives Virtual Environment (VENV) erkannt.")
        else:
            log.warning("ACHTUNG: Kein aktives VENV erkannt. Installation erfolgt global.")

        # 3. Python Dependencies installieren
        if (project_path / "pyproject.toml").exists() and (project_path / "poetry.lock").exists():
            self._install_poetry(project_path)
        elif (project_path / "requirements.txt").exists():
            self._install_pip(project_path / "requirements.txt")
        else:
            log.info("Keine expliziten Dependency-Dateien gefunden.")

    def _ensure_system_tools(self):
        """
        Prüft auf notwendige System-Tools (aktuell: OpenSSL).
        Versucht automatische Installation via Winget, falls fehlend.
        """
        log.info("Prüfe System-Tools...")
        
        if not shutil.which("openssl"):
            log.warning("OpenSSL wurde nicht im PATH gefunden!")
            log.info("Versuche automatische Installation via Winget (PowerShell)...")
            
            # Endlosschleife bis installiert (oder User Abbruch)
            while not shutil.which("openssl"):
                self.network.wait_for_network()
                
                log.info("Starte Download & Installation von OpenSSL...")
                try:
                    # Winget Silent Install via PowerShell
                    # Wir nutzen 'ShiningLight.OpenSSL' oder 'Git.Git' (da ist openssl drin). 
                    # ShiningLight ist direkter.
                    cmd = [
                        "powershell", "-Command",
                        "winget install -e --id ShiningLight.OpenSSL --accept-source-agreements --accept-package-agreements --silent"
                    ]
                    subprocess.run(cmd, check=True)
                    
                    log.info("Installation angestoßen. Prüfe erneut...")
                    
                    # Reload Path für den aktuellen Prozess schwierig, oft Neustart nötig.
                    # Wir prüfen zumindest, ob der Standardpfad existiert
                    possible_paths = [
                        Path(r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe"),
                        Path(r"C:\Program Files\OpenSSL\bin\openssl.exe")
                    ]
                    found = False
                    for p in possible_paths:
                        if p.exists():
                            log.success(f"OpenSSL gefunden unter: {p}")
                            # Zum PATH hinzufügen für diese Session
                            import os
                            os.environ["PATH"] += os.pathsep + str(p.parent)
                            found = True
                            break
                    
                    if not found and not shutil.which("openssl"):
                        log.warning("OpenSSL installiert, aber noch nicht im PATH. Bitte Shell neu starten oder Pfad prüfen.")
                        break # Brechen Loop ab, User muss ggf. eingreifen
                        
                except subprocess.CalledProcessError as e:
                    log.error(f"Installation fehlgeschlagen: {e}")
                    log.info("Warte 10 Sekunden vor nächstem Versuch...")
                    import time
                    time.sleep(10)
        else:
            log.debug("OpenSSL ist installiert und verfügbar.")

    def _is_venv(self) -> bool:
        return (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

    def _check_package_installed(self, package_name: str) -> bool:
        clean_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].strip()
        if importlib.util.find_spec(clean_name) is not None:
            return True
        try:
            pkg_resources.get_distribution(clean_name)
            return True
        except pkg_resources.DistributionNotFound:
            return False

    def _install_pip(self, req_file: Path):
        log.info(f"Prüfe Dependencies aus {req_file.name}...")
        to_install = []
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if not self._check_package_installed(line):
                    to_install.append(line)
        except Exception as e:
            log.error(f"Fehler beim Lesen von requirements.txt: {e}")
            return

        if not to_install:
            log.success("Dependencies bereits aktuell.")
            return

        log.info(f"Installiere {len(to_install)} fehlende Pakete...")
        self.network.wait_for_network()

        def run_install():
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + to_install,
                stdout=sys.stdout, stderr=subprocess.PIPE
            )

        try:
            self.network.run_with_retry(run_install)
            log.success("Pip Installation erfolgreich.")
        except Exception as e:
            log.error(f"Pip Fehler: {e}")

    def _install_poetry(self, project_path: Path):
        log.info("Poetry Projekt erkannt.")
        # Check Poetry Existenz
        if not shutil.which("poetry"):
            log.error("Poetry fehlt! Bitte manuell installieren (pip install poetry).")
            return

        self.network.wait_for_network()
        def run_poetry():
            subprocess.check_call(
                ["poetry", "install", "--no-root"],
                cwd=str(project_path),
                stdout=sys.stdout
            )
        try:
            self.network.run_with_retry(run_poetry)
            log.success("Poetry Install erfolgreich.")
        except Exception as e:
            log.error(f"Poetry Fehler: {e}")
