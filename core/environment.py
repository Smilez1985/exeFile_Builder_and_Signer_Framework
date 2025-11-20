import subprocess
import sys
import os
from pathlib import Path
from src.utils.logger import log
from src.core.network import NetworkGuard

class EnvironmentManager:
    """
    Kümmert sich um die Vorbereitung der Build-Umgebung.
    Erkennt requirements.txt, pyproject.toml (Poetry) und installiert Dependencies.
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
            log.info("Laufe innerhalb eines Virtual Environments (VENV). Gut.")
        else:
            log.warning("ACHTUNG: Kein aktives VENV erkannt. Installiere Dependencies global (oder user-scope).")

        # 1. Poetry Check
        if (project_path / "pyproject.toml").exists() and (project_path / "poetry.lock").exists():
            self._install_poetry(project_path)
        # 2. Requirements.txt Check
        elif (project_path / "requirements.txt").exists():
            self._install_pip(project_path / "requirements.txt")
        else:
            log.info("Keine expliziten Dependency-Dateien gefunden.")

    def _is_venv(self) -> bool:
        """Prüft, ob wir in einer Venv laufen."""
        return (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

    def _install_pip(self, req_file: Path):
        log.info(f"Installiere pip Dependencies aus {req_file.name}...")
        
        def run_install():
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--upgrade"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

        try:
            self.network.run_guarded(run_install)
            log.success("Pip Dependencies installiert.")
        except subprocess.CalledProcessError as e:
            log.error(f"Pip Installation fehlgeschlagen: {e.stderr.decode()}")
            raise

    def _install_poetry(self, project_path: Path):
        log.info("Poetry Projekt erkannt. Installiere via Poetry...")
        
        # Prüfen ob Poetry installiert ist
        try:
            subprocess.run(["poetry", "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            log.error("Poetry ist nicht im PATH gefunden! Bitte installiere Poetry oder nutze requirements.txt.")
            return

        def run_poetry():
            subprocess.check_call(
                ["poetry", "install", "--no-root"],
                cwd=str(project_path),
                stdout=subprocess.DEVNULL
            )

        try:
            self.network.run_guarded(run_poetry)
            log.success("Poetry Dependencies installiert.")
        except Exception as e:
            log.error(f"Poetry Installation fehlgeschlagen: {e}")
