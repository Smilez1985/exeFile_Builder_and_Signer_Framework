import subprocess
import sys
import shutil
import os
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

    def _sanitize_args(self, args: list, project_root: Path) -> list:
        """
        Wandelt relative Pfade in Argumenten in absolute Pfade um.
        Löst das Problem, dass PyInstaller Pfade relativ zum Spec-Ordner sucht.
        """
        sanitized = []
        i = 0
        while i < len(args):
            arg = args[i]
            
            # --- FIX: --add-data "src;dest" ---
            if arg == "--add-data" and i + 1 < len(args):
                val = args[i+1]
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    # Wenn src relativ ist, machen wir es absolut zum Projekt-Root
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        val = f"{abs_src}{os.pathsep}{dest}"
                        log.debug(f"Pfad korrigiert: {src} -> {abs_src}")
                
                sanitized.append(arg)
                sanitized.append(val)
                i += 2
                continue

            # --- FIX: --add-data="src;dest" ---
            elif arg.startswith("--add-data="):
                prefix, val = arg.split("=", 1)
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        arg = f"{prefix}={abs_src}{os.pathsep}{dest}"
                        log.debug(f"Pfad korrigiert: {src} -> {abs_src}")
                sanitized.append(arg)
                i += 1
                continue

            # --- FIX: --icon ---
            elif arg.startswith("--icon="):
                prefix, val = arg.split("=", 1)
                icon_path = Path(val)
                if not icon_path.is_absolute():
                    abs_icon = (project_root / val).resolve()
                    arg = f"{prefix}={abs_icon}"
                sanitized.append(arg)
                i += 1
                continue
            
            # Argument unverändert übernehmen
            sanitized.append(arg)
            i += 1
            
        return sanitized

    def _run_process(self, cmd: list, cwd: Path = None, app_name_hint: str = "Output") -> Path:
        """Führt den Prozess aus und gibt den Pfad zur EXE zurück."""
        captured_logs = []

        try:
            log.debug(f"CWD: {cwd or '.'}")
            # log.debug(f"CMD: {' '.join(cmd)}") # Kann sehr lang sein
            
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
                    captured_logs.append(line)
                    if any(x in line for x in ["Error", "WARNING", "Building", "Copying", "Traceback"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                exe_path = self.dist_dir / f"{app_name_hint}.exe"
                if exe_path.exists():
                    log.success(f"Build erfolgreich! Datei: {exe_path}")
                    return exe_path
                else:
                    log.error(f"PyInstaller lief durch, aber Datei fehlt: {exe_path}")
                    # Fallback Suche
                    found = list(self.dist_dir.glob("*.exe"))
                    if found:
                        log.info(f"Gefundene Datei: {found[0]}")
                        return found[0]
                    return None
            else:
                log.error(f"PyInstaller abgebrochen (Exit Code {process.returncode})")
                log.error("================ ERROR LOG START ================")
                start_index = max(0, len(captured_logs) - 50) # Letzte 50 Zeilen
                for i in range(start_index, len(captured_logs)):
                    print(f"    > {captured_logs[i]}")
                log.error("================ ERROR LOG ENDE =================")
                return None

        except Exception as e:
            log.error(f"Kritischer System-Fehler im Builder: {e}")
            return None

    def build_with_config(self, pyinstaller_args: list, project_root: Path) -> Path:
        """
        GOLDSTANDARD: Führt PyInstaller mit der exakten Liste aus der Config-Datei aus.
        """
        # App Name extrahieren
        app_name = "App"
        if "--name" in pyinstaller_args:
            idx = pyinstaller_args.index("--name")
            if idx + 1 < len(pyinstaller_args):
                app_name = pyinstaller_args[idx+1]
        
        log.info(f"Starte Config-Build für '{app_name}' im Kontext '{project_root}'...")

        # FIX: Argumente bereinigen (Pfade absolut machen)
        clean_args = self._sanitize_args(pyinstaller_args, project_root)

        # Kommando bauen
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + clean_args
        
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
