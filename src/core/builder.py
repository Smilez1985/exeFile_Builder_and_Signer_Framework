import subprocess
import sys
import shutil
from pathlib import Path
from src.utils.helpers import log

class PyBuilder:
    """
    Wrapper-Klasse für PyInstaller.
    Verwaltet den Build-Prozess von Python-Skripten zu Executables.
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        # Erstelle Verzeichnisstruktur
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def build(self, script_path: Path, app_name: str, icon_path: Path = None, 
              one_file: bool = True, console: bool = True, clean: bool = True) -> Path:
        """
        Führt PyInstaller mit den angegebenen Parametern aus.
        
        Args:
            script_path (Path): Pfad zur .py Datei.
            app_name (str): Name der fertigen .exe.
            icon_path (Path, optional): Pfad zum Icon (.ico).
            one_file (bool): Ob alles in eine einzelne EXE gepackt werden soll.
            console (bool): Ob ein Konsolenfenster angezeigt werden soll.
            clean (bool): Ob Cache vor dem Build bereinigt werden soll.
            
        Returns:
            Path: Pfad zur erstellten Executable oder None bei Fehler.
        """
        log.info(f"Starte Build-Prozess für '{app_name}'...")
        
        if not script_path.exists():
            log.error(f"Script nicht gefunden: {script_path}")
            return None

        # Basis-Kommando zusammenstellen
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(script_path),
            "--name", app_name,
            "--distpath", str(self.dist_dir),
            "--workpath", str(self.work_dir),
            "--specpath", str(self.spec_dir),
        ]

        # Optionen hinzufügen
        if one_file:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        if not console:
            cmd.append("--noconsole")
            
        if clean:
            cmd.append("--clean")
            cmd.append("--noconfirm")

        if icon_path and icon_path.exists():
            cmd.append(f"--icon={str(icon_path)}")
        elif icon_path:
            log.warning(f"Icon nicht gefunden, fahre ohne Icon fort: {icon_path}")

        # Ausführung
        try:
            log.debug(f"Führe Kommando aus: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            # Echtzeit-Output Logging
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Filtere irrelevante PyInstaller Infos für saubereren Log, 
                    # zeige aber Fehler und wichtige Schritte
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                exe_path = self.dist_dir / f"{app_name}.exe"
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei liegt unter: {exe_path}")
                    return exe_path
                else:
                    log.error("PyInstaller lief durch, aber keine EXE gefunden.")
                    return None
            else:
                log.error(f"PyInstaller beendet mit Fehlercode {process.returncode}")
                return None

        except Exception as e:
            log.error(f"Kritischer Fehler beim Build-Vorgang: {e}")
            return None

    def cleanup(self):
        """Löscht temporäre Build-Ordner (work, spec)."""
        try:
            log.info("Bereinige temporäre Build-Dateien...")
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            if self.spec_dir.exists():
                shutil.rmtree(self.spec_dir)
            log.success("Bereinigung abgeschlossen.")
        except Exception as e:
            log.warning(f"Konnte temporäre Dateien nicht vollständig löschen: {e}")
