import subprocess
import sys
import shutil
from pathlib import Path
from src.utils.helpers import log

class PyBuilder:
    """
    Wrapper-Klasse für PyInstaller.
    Verwaltet den Build-Prozess und erzwingt robuste Standard-Einstellungen.
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        # Verzeichnisse erstellen
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_base_cmd(self) -> list:
        """Liefert das Basis-Kommando inkl. aller Pfade."""
        return [
            sys.executable, "-m", "PyInstaller",
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def build(self, script_path: Path, app_name: str, icon_path: Path = None, 
              one_file: bool = True, console: bool = True, clean: bool = True,
              add_data: list = None) -> Path:
        """
        Führt den Build aus. 
        Integrierte 'Intelligence': Fügt automatisch kritische Hidden-Imports hinzu.
        """
        
        # 1. Namen bereinigen (kein .exe.exe)
        clean_name = app_name
        if clean_name.lower().endswith(".exe"):
            clean_name = clean_name[:-4]

        log.info(f"Starte Build für '{clean_name}'...")
        
        if not script_path.exists():
            log.error(f"Script nicht gefunden: {script_path}")
            return None

        # 2. Kommando zusammenbauen
        cmd = self._get_base_cmd()
        
        # Haupt-Optionen
        cmd.append(str(script_path))
        cmd.append(f"--name={clean_name}")
        cmd.append("--onefile" if one_file else "--onedir")
        cmd.append("--console" if console else "--noconsole")
        
        if clean:
            cmd.extend(["--clean", "--noconfirm"])

        # 3. ROBUSTHEITS-UPDATE: Hidden Imports erzwingen!
        # Wir packen alles ein, was oft Probleme macht. Das schadet nicht, wenn es fehlt,
        # rettet aber den Tag, wenn es gebraucht wird (wie bei PyYAML).
        critical_imports = [
            "yaml", "yaml.loader",          # Dein aktuelles Problem
            "win32api", "win32con",         # Für Windows Integration
            "win32timezone",                # Oft vergessen bei Datum-Sachen
            "pkg_resources.py2_warn",       # Alter Setuptools Fix
            "shutil"                        # Standard-Lib Sicherheit
        ]
        
        for imp in critical_imports:
            cmd.append(f"--hidden-import={imp}")

        # 4. Assets & Icon
        if icon_path and icon_path.exists():
            cmd.append(f"--icon={str(icon_path)}")
            
        if add_data:
            for item in add_data:
                cmd.append(f"--add-data={item}")
                log.debug(f"Asset integriert: {item}")

        # 5. Collect-All (Optional, aber mächtig für komplexe Libs)
        # cmd.append("--collect-all=yaml") 

        # Ausführung
        try:
            log.debug(f"CMD: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            # Live-Log
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Wir filtern den Spam, zeigen aber Wichtiges
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                exe_path = self.dist_dir / f"{clean_name}.exe"
                if exe_path.exists():
                    log.success(f"Build erfolgreich: {exe_path}")
                    return exe_path
            
            log.error(f"Build fehlgeschlagen (Code {process.returncode}).")
            return None

        except Exception as e:
            log.error(f"Builder Exception: {e}")
            return None

    def cleanup(self):
        try:
            if self.work_dir.exists(): shutil.rmtree(self.work_dir)
            if self.spec_dir.exists(): shutil.rmtree(self.spec_dir)
        except: pass
