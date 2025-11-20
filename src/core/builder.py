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
              one_file: bool = True, console: bool = True, clean: bool = True,
              add_data: list = None) -> Path:
        """
        Führt PyInstaller mit den angegebenen Parametern aus.
        """
        # FIX: Sicherstellen, dass app_name keine .exe Endung hat (vermeidet .exe.exe)
        clean_app_name = app_name
        if clean_app_name.lower().endswith(".exe"):
            clean_app_name = clean_app_name[:-4]

        log.info(f"Starte Build-Prozess für '{clean_app_name}'...")
        
        if not script_path.exists():
            log.error(f"Script nicht gefunden: {script_path}")
            return None

        # Basis-Kommando
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(script_path),
            "--name", clean_app_name, # Bereinigten Namen nutzen
            "--distpath", str(self.dist_dir),
            "--workpath", str(self.work_dir),
            "--specpath", str(self.spec_dir),
        ]

        # Optionen
        if one_file: cmd.append("--onefile")
        else: cmd.append("--onedir")

        if not console: cmd.append("--noconsole")
            
        if clean:
            cmd.append("--clean")
            cmd.append("--noconfirm")

        if icon_path and icon_path.exists():
            cmd.append(f"--icon={str(icon_path)}")
            
        # Assets hinzufügen
        if add_data:
            for data_item in add_data:
                cmd.append(f"--add-data={data_item}")
                log.debug(f"Asset hinzugefügt: {data_item}")

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

            for line in process.stdout:
                line = line.strip()
                if line:
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                # Wir suchen nach dem bereinigten Namen + .exe
                exe_path = self.dist_dir / f"{clean_app_name}.exe"
                
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei liegt unter: {exe_path}")
                    return exe_path
                else:
                    log.error(f"PyInstaller lief durch, aber Datei nicht gefunden: {exe_path}")
                    return None
            else:
                log.error(f"PyInstaller beendet mit Fehlercode {process.returncode}")
                return None

        except Exception as e:
            log.error(f"Kritischer Fehler beim Build-Vorgang: {e}")
            return None

    def cleanup(self):
        try:
            log.info("Bereinige temporäre Build-Dateien...")
            if self.work_dir.exists(): shutil.rmtree(self.work_dir)
            if self.spec_dir.exists(): shutil.rmtree(self.spec_dir)
            log.success("Bereinigung abgeschlossen.")
        except Exception as e:
            log.warning(f"Fehler bei Bereinigung: {e}")
