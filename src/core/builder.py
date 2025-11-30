import subprocess
import sys
import shutil
import os
from pathlib import Path
from src.utils.helpers import log

class PyBuilder:
    """
    Wrapper-Klasse für PyInstaller.
    DEBUG EDITION: Maximale Transparenz bei Fehlern.
    """

    def __init__(self):
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_framework_paths(self) -> list:
        return [
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def _sanitize_args(self, args: list, project_root: Path) -> list:
        """Wandelt relative Pfade in absolute um."""
        sanitized = []
        i = 0
        while i < len(args):
            arg = args[i]
            
            # --add-data "src;dest"
            if arg == "--add-data" and i + 1 < len(args):
                val = args[i+1]
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        val = f"{abs_src}{os.pathsep}{dest}"
                sanitized.append(arg)
                sanitized.append(val)
                i += 2
                continue

            # --add-data="src;dest"
            elif arg.startswith("--add-data="):
                prefix, val = arg.split("=", 1)
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        arg = f"{prefix}={abs_src}{os.pathsep}{dest}"
                sanitized.append(arg)
                i += 1
                continue

            # --icon
            elif arg.startswith("--icon="):
                prefix, val = arg.split("=", 1)
                icon_path = Path(val)
                if not icon_path.is_absolute():
                    abs_icon = (project_root / val).resolve()
                    arg = f"{prefix}={abs_icon}"
                sanitized.append(arg)
                i += 1
                continue
            
            sanitized.append(arg)
            i += 1
        return sanitized

    def _run_process(self, cmd: list, cwd: Path = None, app_name_hint: str = "Output") -> Path:
        captured_logs = []
        
        # DEBUG: Zeige exakt, was ausgeführt wird
        log.info(f"--- DEBUG: BUILD START ---")
        log.info(f"Target EXE Name: {app_name_hint}.exe")
        log.info(f"Working Directory: {cwd or '.'}")
        # log.debug(f"Full Command: {cmd}") # Bei Bedarf einkommentieren

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                cwd=str(cwd) if cwd else None
            )

            # Alles loggen
            for line in process.stdout:
                line = line.strip()
                if line:
                    captured_logs.append(line)
                    # Wir zeigen jetzt MEHR an, um zu sehen ob PyInstaller überhaupt startet
                    if any(x in line for x in ["PyInstaller:", "Python:", "Building", "Error", "WARNING"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                exe_path = self.dist_dir / f"{app_name_hint}.exe"
                
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei: {exe_path}")
                    return exe_path
                else:
                    log.error(f"FATAL: PyInstaller Success (0), aber Datei fehlt: {exe_path}")
                    
                    # Debug: Was liegt im Ordner?
                    log.info(f"Inhalt von {self.dist_dir}:")
                    found_files = list(self.dist_dir.glob("*"))
                    for f in found_files:
                        log.info(f" - {f.name}")
                        
                        # Fallback: Wenn wir eine EXE finden, nehmen wir sie (vielleicht hieß sie anders)
                        if f.suffix.lower() == ".exe" and app_name_hint == "App":
                            log.warning(f"Name Mismatch! Nehme gefundene Datei: {f.name}")
                            return f
                    
                    return None
            else:
                log.error(f"PyInstaller Crash (Code {process.returncode})")
                log.error("--- ERROR DUMP START ---")
                # Dump alles, damit wir den Fehler finden
                for l in captured_logs:
                    print(f"  > {l}")
                log.error("--- ERROR DUMP ENDE ---")
                return None

        except Exception as e:
            log.error(f"System-Fehler: {e}")
            return None

    def build_with_config(self, pyinstaller_args: list, project_root: Path) -> Path:
        """
        GOLDSTANDARD: Config-Build.
        """
        # Name Extraktion (Verbessert)
        app_name = "App"
        try:
            if "--name" in pyinstaller_args:
                idx = pyinstaller_args.index("--name")
                if idx + 1 < len(pyinstaller_args):
                    app_name = pyinstaller_args[idx+1]
            # Check auch nach --name=...
            else:
                for arg in pyinstaller_args:
                    if arg.startswith("--name="):
                        app_name = arg.split("=", 1)[1]
                        break
        except Exception as e:
            log.warning(f"Konnte App-Namen nicht parsen: {e}")

        # Bereinigung
        app_name = app_name.strip()
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]
        
        log.info(f"Starte Config-Build für '{app_name}' (Root: {project_root})")
        
        # DEBUG: Zeige empfangene Argumente (gekürzt)
        # log.info(f"Args (Raw): {pyinstaller_args[:5]} ...")

        clean_args = self._sanitize_args(pyinstaller_args, project_root)
        
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + clean_args
        
        return self._run_process(cmd, cwd=project_root, app_name_hint=app_name)

    def build_from_gui(self, script_path: Path, app_name: str, icon_path: Path = None, 
                       one_file: bool = True, console: bool = True, clean: bool = True,
                       add_data: list = None) -> Path:
        """Standard GUI-Modus."""
        if app_name.lower().endswith(".exe"): app_name = app_name[:-4]
        
        log.info(f"Starte GUI-Build für '{app_name}'...")
        
        args = [str(script_path), f"--name={app_name}"]
        args.append("--onefile" if one_file else "--onedir")
        args.append("--console" if console else "--noconsole")
        if clean: args.extend(["--clean", "--noconfirm"])
        
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
