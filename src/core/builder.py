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
    2. Config-Modus (Goldstandard): Verarbeitet eine externe Argumenten-Liste exakt wie vorgegeben.
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        # Verzeichnisse leeren/erstellen
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_framework_paths(self) -> list:
        """Definiert, wo die Artefakte landen sollen (Framework-Hoheit)."""
        return [
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def _run_process(self, cmd: list, cwd: Path = None, app_name_hint: str = "Output") -> Path:
        """Führt den Prozess aus und gibt den Pfad zur EXE zurück."""
        try:
            # Logging für Debugging
            log.debug(f"CWD: {cwd or '.'}")
            log.debug(f"CMD: {' '.join(cmd)}")
            
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
                # Wir versuchen, den Namen der EXE zu erraten oder nutzen den Hint
                # Im Config-Modus steht der Name in der Liste (--name), das parsen wir im Wrapper
                exe_path = self.dist_dir / f"{app_name_hint}.exe"
                
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei: {exe_path}")
                    return exe_path
                else:
                    log.error(f"PyInstaller fertig, aber Datei fehlt: {exe_path}")
                    # Fallback: Manchmal heißt die Datei anders, wir listen das Verzeichnis
                    found = list(self.dist_dir.glob("*.exe"))
                    if found:
                        log.info(f"Gefundene Datei: {found[0]}")
                        return found[0]
                    return None
            else:
                log.error(f"PyInstaller Fehler (Code {process.returncode})")
                return None

        except Exception as e:
            log.error(f"Kritischer Build-Fehler: {e}")
            return None

    def build_with_config(self, pyinstaller_args: list, project_root: Path) -> Path:
        """
        GOLDSTANDARD: Führt PyInstaller mit der exakten Liste aus der Config-Datei aus.
        
        Args:
            pyinstaller_args: Die Liste PYINSTALLER_CMD_ARGS aus der Datei.
            project_root: Das Root-Verzeichnis des externen Projekts (für relative Pfade).
        """
        # App Name extrahieren (nur für den Dateinamen-Check am Ende)
        app_name = "App"
        if "--name" in pyinstaller_args:
            idx = pyinstaller_args.index("--name")
            if idx + 1 < len(pyinstaller_args):
                app_name = pyinstaller_args[idx+1]
        
        log.info(f"Starte Config-Build für '{app_name}' im Kontext '{project_root}'...")

        # Kommando: Python -> PyInstaller -> Framework-Pfade -> USER ARGS
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + pyinstaller_args
        
        return self._run_process(cmd, cwd=project_root, app_name_hint=app_name)

    def build_from_gui(self, script_path: Path, app_name: str, icon_path: Path = None, 
                       one_file: bool = True, console: bool = True, clean: bool = True,
                       add_data: list = None) -> Path:
        """Standard GUI-Modus (Fallback)."""
        
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        log.info(f"Starte GUI-Build für '{app_name}'...")
        
        args = [str(script_path), f"--name={app_name}"]
        args.append("--onefile" if one_file else "--onedir")
        args.append("--console" if console else "--noconsole")
        
        if clean:
            args.extend(["--clean", "--noconfirm"])
            
        # Standard Hidden Imports für GUI-Nutzer
        args.extend(["--hidden-import=yaml", "--hidden-import=win32api", "--hidden-import=win32con"])

        if icon_path and icon_path.exists():
            args.append(f"--icon={str(icon_path)}")
            
        if add_data:
            for item in add_data:
                args.append(f"--add-data={item}")

        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + args
        
        return self._run_process(cmd, app_name_hint=app_name)

    def cleanup(self):
        try:
            if self.work_dir.exists(): shutil.rmtree(self.work_dir)
            if self.spec_dir.exists(): shutil.rmtree(self.spec_dir)
        except: pass
