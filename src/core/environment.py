import subprocess
import sys
import importlib.util
import pkg_resources
from pathlib import Path
from src.utils.helpers import log
from src.core.network import NetworkGuard

class EnvironmentManager:
    """
    Kümmert sich um die Vorbereitung der Build-Umgebung.
    Erkennt requirements.txt, pyproject.toml (Poetry) und installiert Dependencies.
    Integriert robusten Netzwerk-Check und Existenz-Prüfung.
    """
    
    def __init__(self):
        self.network = NetworkGuard()

    def prepare_environment(self, project_path: Path):
        """
        Analysiert den Projektordner und installiert fehlende Pakete.
        """
        log.info(f"Analysiere Umgebung in: {project_path}")
        
        # Check: Virtual Environment
        if self._is_venv():
            log.debug("Aktives Virtual Environment (VENV) erkannt.")
        else:
            log.warning("ACHTUNG: Kein aktives VENV erkannt. Installation erfolgt global/user-scope.")

        # 1. Poetry Check
        if (project_path / "pyproject.toml").exists() and (project_path / "poetry.lock").exists():
            self._install_poetry(project_path)
        # 2. Requirements.txt Check
        elif (project_path / "requirements.txt").exists():
            self._install_pip(project_path / "requirements.txt")
        else:
            log.info("Keine expliziten Dependency-Dateien (requirements.txt/poetry.lock) gefunden.")

    def _is_venv(self) -> bool:
        """Prüft, ob wir in einer Venv laufen."""
        return (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

    def _check_package_installed(self, package_name: str) -> bool:
        """
        Prüft, ob ein Paket bereits installiert ist.
        Bereinigt Versionsnummern (z.B. 'requests==2.31.0' -> 'requests').
        """
        clean_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].strip()
        
        # Methode 1: importlib (schnell)
        if importlib.util.find_spec(clean_name) is not None:
            return True
            
        # Methode 2: pkg_resources (genauer für installierte Metadaten)
        try:
            pkg_resources.get_distribution(clean_name)
            return True
        except pkg_resources.DistributionNotFound:
            return False

    def _install_pip(self, req_file: Path):
        """Liest requirements.txt und installiert fehlende Pakete."""
        log.info(f"Prüfe Dependencies aus {req_file.name}...")
        
        to_install = []
        
        # 1. Liste der fehlenden Pakete erstellen (If-Exist Abfrage)
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Einfacher Check auf Paketname
                if not self._check_package_installed(line):
                    to_install.append(line)
                else:
                    log.debug(f"Paket bereits vorhanden: {line}")

        except Exception as e:
            log.error(f"Konnte requirements.txt nicht lesen: {e}")
            return

        if not to_install:
            log.success("Alle Dependencies sind bereits installiert.")
            return

        # 2. Installation starten (nur wenn nötig)
        log.info(f"Installiere {len(to_install)} fehlende Pakete...")
        
        # Ping Loop: Sicherstellen, dass wir online sind
        self.network.wait_for_network()

        def run_install():
            # Wir übergeben die Liste der fehlenden Pakete direkt an Pip
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + to_install,
                stdout=sys.stdout, # Output anzeigen für User Feedback
                stderr=subprocess.PIPE
            )

        try:
            self.network.run_with_retry(run_install)
            log.success("Pip Dependencies erfolgreich installiert.")
        except Exception as e:
            log.error(f"Pip Installation fehlgeschlagen: {e}")
            raise

    def _install_poetry(self, project_path: Path):
        log.info("Poetry Projekt erkannt. Prüfe Umgebung...")
        
        # Prüfen ob Poetry installiert ist
        try:
            subprocess.run(["poetry", "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            log.error("Poetry ist nicht im PATH gefunden! Bitte installieren.")
            return

        # Ping Loop für Poetry
        self.network.wait_for_network()

        def run_poetry():
            log.info("Führe 'poetry install' aus...")
            subprocess.check_call(
                ["poetry", "install", "--no-root"],
                cwd=str(project_path),
                stdout=sys.stdout
            )

        try:
            self.network.run_with_retry(run_poetry)
            log.success("Poetry Dependencies aktualisiert.")
        except Exception as e:
            log.error(f"Poetry Installation fehlgeschlagen: {e}")
