import subprocess
import sys
import shutil
from pathlib import Path
from src.utils.helpers import log

class PyBuilder:
    """
    Wrapper-Klasse für PyInstaller.
    Unterstützt zwei Modi:
    1. GUI-Modus: Baut Argumente aus Einzelparametern zusammen.
    2. Config-Modus: Verarbeitet eine vorgefertigte Argumenten-Liste (Goldstandard).
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        # Verzeichnisse leeren/erstellen
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_base_args(self) -> list:
        """Liefert die unveränderlichen Framework-Pfade."""
        return [
            sys.executable, "-m", "PyInstaller",
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def _execute_pyinstaller(self, cmd: list, app_name: str, cwd: Path = None) -> Path:
        """Interne Methode zur Ausführung des Prozesses."""
        try:
            log.debug(f"Führe Kommando aus (CWD: {cwd or '.'}): {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                cwd=str(cwd) if cwd else None
            )

            # Echtzeit-Logging
            for line in process.stdout:
                line = line.strip()
                if line:
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                # Pfad zur EXE konstruieren
                exe_path = self.dist_dir / f"{app_name}.exe"
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei: {exe_path}")
                    return exe_path
                else:
                    log.error(f"PyInstaller fertig, aber Datei fehlt: {exe_path}")
                    return None
            else:
                log.error(f"PyInstaller Fehler (Code {process.returncode})")
                return None

        except Exception as e:
            log.error(f"Kritischer Build-Fehler: {e}")
            return None

    def build_from_config(self, pyinstaller_args: list, project_root: Path) -> Path:
        """
        Profi-Modus: Nimmt eine fertige Liste von Argumenten entgegen.
        
        Args:
            pyinstaller_args: Liste der Argumente aus der build_windows_exe.py
            project_root: Das Verzeichnis, in dem das Skript ausgeführt werden soll (für relative Pfade)
        """
        # 1. App Name extrahieren (für die Rückgabe des Pfades nötig)
        app_name = "Output"
        if "--name" in pyinstaller_args:
            idx = pyinstaller_args.index("--name")
            if idx + 1 < len(pyinstaller_args):
                app_name = pyinstaller_args[idx+1]
        
        # .exe Endung bereinigen, falls vorhanden
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        # 2. Framework-Pfade erzwingen (prepend)
        # Wir setzen unsere Pfade VOR die User-Args. PyInstaller nutzt in der Regel die letzten Flags,
        # aber Pfade wie distpath sollten wir kontrollieren, damit der Signer sie findet.
        # Um sicherzugehen, entfernen wir evtl. vorhandene Pfad-Argumente aus der User-Liste nicht,
        # sondern verlassen uns darauf, dass unsere am Anfang/Ende stehen.
        # Besser: Wir bauen das Kommando sauber auf.
        
        cmd = self._get_base_args() + pyinstaller_args
        
        log.info(f"Starte Config-Build für '{app_name}'...")
        return self._execute_pyinstaller(cmd, app_name, cwd=project_root)

    def build_from_gui(self, script_path: Path, app_name: str, icon_path: Path = None, 
                       one_file: bool = True, console: bool = True, clean: bool = True,
                       add_data: list = None) -> Path:
        """Standard GUI-Modus."""
        
        # Name bereinigen
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        log.info(f"Starte GUI-Build für '{app_name}'...")
        
        if not script_path.exists():
            log.error(f"Script nicht gefunden: {script_path}")
            return None

        # Argumente zusammenbauen
        args = []
        args.append(str(script_path))
        args.append(f"--name={app_name}")
        
        if one_file: args.append("--onefile")
        else: args.append("--onedir")
        
        if not console: args.append("--noconsole")
        
        if clean:
            args.append("--clean")
            args.append("--noconfirm")
            
        # Hidden Imports (Sicherheitsnetz für GUI User)
        args.extend(["--hidden-import=yaml", "--hidden-import=yaml.loader", 
                     "--hidden-import=win32api", "--hidden-import=win32con"])

        if icon_path and icon_path.exists():
            args.append(f"--icon={str(icon_path)}")
            
        if add_data:
            for item in add_data:
                args.append(f"--add-data={item}")

        # Base + Args
        cmd = self._get_base_args() + args
        
        return self._execute_pyinstaller(cmd, app_name)

    def cleanup(self):
        try:
            if self.work_dir.exists(): shutil.rmtree(self.work_dir)
            if self.spec_dir.exists(): shutil.rmtree(self.spec_dir)
        except: pass
