import subprocess
import sys
import shutil
from pathlib import Path
from src.utils.helpers import log

class PyBuilder:
    """
    Wrapper-Klasse für PyInstaller.
    Unterstützt:
    1. GUI-Modus (Argumente werden aus GUI-Optionen generiert).
    2. Config-Modus (Argumente kommen fixfertig aus einer externen Konfigurationsdatei).
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_framework_paths(self) -> list:
        """Framework erzwingt seine Ausgabe-Pfade (damit der Signer sie findet)."""
        return [
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def _run_process(self, cmd: list, cwd: Path = None) -> Path:
        """Führt PyInstaller aus und gibt den Pfad zur EXE zurück."""
        app_name = "Output"
        
        # Versuchen, den App-Namen aus den Argumenten zu fischen (für die Rückgabe)
        if "--name" in cmd:
            idx = cmd.index("--name")
            if idx + 1 < len(cmd):
                app_name = cmd[idx+1]
        elif any(arg.startswith("--name=") for arg in cmd):
            for arg in cmd:
                if arg.startswith("--name="):
                    app_name = arg.split("=", 1)[1]
                    break
        
        # Bereinigung
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        try:
            log.debug(f"CMD (CWD={cwd or '.'}): {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                cwd=str(cwd) if cwd else None
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                exe_path = self.dist_dir / f"{app_name}.exe"
                if exe_path.exists():
                    log.success(f"Build erfolgreich: {exe_path}")
                    return exe_path
            
            log.error(f"PyInstaller Fehler (Code {process.returncode})")
            return None

        except Exception as e:
            log.error(f"Builder Crash: {e}")
            return None

    def build_with_args(self, pyinstaller_args: list, project_root: Path) -> Path:
        """
        PROFI-MODUS: Führt PyInstaller mit einer externen Liste aus.
        """
        log.info("Starte Build im Config-Modus...")
        
        # Wir kombinieren: Python + PyInstaller + Framework-Pfad-Zwang + Externe Argumente
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + pyinstaller_args
        
        return self._run_process(cmd, cwd=project_root)

    def build_from_gui(self, script_path: Path, app_name: str, icon_path: Path = None, 
                       one_file: bool = True, console: bool = True, clean: bool = True,
                       add_data: list = None) -> Path:
        """
        STANDARD-MODUS: Baut Argumente aus der GUI zusammen.
        """
        log.info(f"Starte Build im GUI-Modus für '{app_name}'...")
        
        # Name bereinigen
        if app_name.lower().endswith(".exe"): app_name = app_name[:-4]

        args = [str(script_path), f"--name={app_name}"]
        args.append("--onefile" if one_file else "--onedir")
        args.append("--console" if console else "--noconsole")
        if clean: args.extend(["--clean", "--noconfirm"])
        
        # Sicherheits-Netz für GUI-User (die keine Config haben)
        args.extend(["--hidden-import=yaml", "--hidden-import=win32api"])

        if icon_path and icon_path.exists():
            args.append(f"--icon={str(icon_path)}")
            
        if add_data:
            for item in add_data:
                args.append(f"--add-data={item}")

        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + args
        
        return self._run_process(cmd)

    def cleanup(self):
        try:
            if self.work_dir.exists(): shutil.rmtree(self.work_dir)
            if self.spec_dir.exists(): shutil.rmtree(self.spec_dir)
        except: pass
