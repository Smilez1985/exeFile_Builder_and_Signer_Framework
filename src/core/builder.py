import subprocess
import sys
import shutil
import os
from pathlib import Path
from typing import List, Optional

from src.utils.logger import log

class PyBuilder:
    """
    Enterprise PyInstaller Wrapper.
    
    Verantwortlichkeiten:
    - Kapselung des PyInstaller-Subprozesses.
    - Echtzeit-Logging mit Filterung (Noise Reduction).
    - Fehler-Forensik (Crash Dumps bei Fehlern).
    - Pfad-Sanitisierung für externe Projekt-Konfigurationen.
    """

    def __init__(self):
        # Framework-interne Arbeitsverzeichnisse
        self.build_dir = Path("builds")
        self.dist_dir = self.build_dir / "dist"
        self.work_dir = self.build_dir / "work"
        self.spec_dir = self.build_dir / "spec"
        
        # Initialisierung der Struktur
        for d in [self.dist_dir, self.work_dir, self.spec_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_framework_paths(self) -> List[str]:
        """
        Definiert die Output-Pfade hart, damit das Framework (Signer)
        die Artefakte garantiert wiederfindet.
        """
        return [
            "--distpath", str(self.dist_dir.absolute()),
            "--workpath", str(self.work_dir.absolute()),
            "--specpath", str(self.spec_dir.absolute()),
        ]

    def _sanitize_args(self, args: List[str], project_root: Path) -> List[str]:
        """
        Korrigiert relative Pfade in Argumenten, damit PyInstaller sie
        auch aus einem anderen Arbeitsverzeichnis heraus findet.
        
        Behandelt: --add-data, --icon, --add-binary
        """
        sanitized = []
        i = 0
        while i < len(args):
            arg = args[i]
            
            # Fall 1: --add-data "src;dest" (Zwei Argumente)
            if arg in ["--add-data", "--add-binary"] and i + 1 < len(args):
                val = args[i+1]
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        val = f"{abs_src}{os.pathsep}{dest}"
                        # log.debug(f"Pfad korrigiert: {src} -> {abs_src}")
                
                sanitized.append(arg)
                sanitized.append(val)
                i += 2
                continue

            # Fall 2: --add-data="src;dest" (Ein Argument mit =)
            elif arg.startswith(("--add-data=", "--add-binary=")):
                key, val = arg.split("=", 1)
                if os.pathsep in val:
                    src, dest = val.split(os.pathsep, 1)
                    src_path = Path(src)
                    if not src_path.is_absolute():
                        abs_src = (project_root / src).resolve()
                        arg = f"{key}={abs_src}{os.pathsep}{dest}"
                sanitized.append(arg)
                i += 1
                continue

            # Fall 3: --icon (Pfad zum Icon)
            elif arg.startswith("--icon="):
                key, val = arg.split("=", 1)
                icon_path = Path(val)
                if not icon_path.is_absolute():
                    abs_icon = (project_root / val).resolve()
                    arg = f"{key}={abs_icon}"
                sanitized.append(arg)
                i += 1
                continue
            
            # Standard: Argument übernehmen
            sanitized.append(arg)
            i += 1
            
        return sanitized

    def _run_process(self, cmd: List[str], cwd: Optional[Path] = None, app_name_hint: str = "Output") -> Optional[Path]:
        """
        Führt den PyInstaller-Prozess sicher aus.
        Fängt stdout/stderr ab und gibt im Fehlerfall einen Dump aus.
        """
        captured_logs = []
        
        log.info(f"--- BUILD START: {app_name_hint} ---")
        # log.debug(f"CWD: {cwd or '.'}")
        
        try:
            # Wir nutzen Popen für Echtzeit-Output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr in stdout für chronologischen Log
                text=True,
                encoding='utf-8',
                cwd=str(cwd) if cwd else None
            )

            # Echtzeit-Filterung
            for line in process.stdout:
                line = line.strip()
                if line:
                    captured_logs.append(line)
                    # Wir zeigen dem User nur relevante Infos, speichern aber alles für den Fehlerfall
                    if any(key in line for key in ["Error", "WARNING", "Building", "Copying", "Traceback", "Appended"]):
                        log.debug(f"[PyInstaller] {line}")

            process.wait()

            if process.returncode == 0:
                # ERFOLG: Wir suchen die Datei
                exe_path = self.dist_dir / f"{app_name_hint}.exe"
                
                if exe_path.exists():
                    log.success(f"Build erfolgreich abgeschlossen: {exe_path.name}")
                    return exe_path
                else:
                    # Fallback Suche: Falls der Name in der Spec anders definiert war
                    log.error(f"PyInstaller meldet Erfolg, aber '{exe_path.name}' fehlt.")
                    found_exes = list(self.dist_dir.glob("*.exe"))
                    if found_exes:
                        log.warning(f"Alternative Datei gefunden: {found_exes[0].name}")
                        return found_exes[0]
                    return None
            else:
                # FEHLER: Crash Dump ausgeben
                log.error(f"Build fehlgeschlagen (Exit Code {process.returncode}).")
                log.error("--- PYINSTALLER ERROR LOG (LETZTE 50 ZEILEN) ---")
                
                start_idx = max(0, len(captured_logs) - 50)
                for i in range(start_idx, len(captured_logs)):
                    # Direktes print für Lesbarkeit im Error-Block, oder via log.error ohne Formatierung
                    print(f"    > {captured_logs[i]}")
                
                log.error("--- ENDE ERROR LOG ---")
                return None

        except Exception as e:
            log.error(f"Systemfehler im Builder-Prozess: {e}")
            return None

    def build_with_config(self, pyinstaller_args: List[str], project_root: Path) -> Optional[Path]:
        """
        Modus A: Goldstandard (Config-basiert).
        Nutzt externe Argumente, sanitisiert Pfade und führt im Projekt-Kontext aus.
        """
        # App Name extrahieren (Best Effort)
        app_name = "App"
        if "--name" in pyinstaller_args:
            idx = pyinstaller_args.index("--name")
            if idx + 1 < len(pyinstaller_args):
                app_name = pyinstaller_args[idx+1]
        
        # Bereinigung (.exe Endung entfernen)
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        log.info(f"Initialisiere Config-Build für '{app_name}'...")
        
        # Pfad-Sanitisierung (WICHTIG!)
        clean_args = self._sanitize_args(pyinstaller_args, project_root)
        
        # Kommando zusammenbauen
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + clean_args
        
        return self._run_process(cmd, cwd=project_root, app_name_hint=app_name)

    def build_from_gui(self, script_path: Path, app_name: str, icon_path: Optional[Path] = None, 
                       one_file: bool = True, console: bool = True, clean: bool = True,
                       add_data: List[str] = None) -> Optional[Path]:
        """
        Modus B: GUI (Fallback/Schnellstart).
        Baut Argumente selbst und erzwingt Sicherheits-Imports (yaml, win32).
        """
        # Name Bereinigung
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]

        log.info(f"Initialisiere GUI-Build für '{app_name}'...")
        
        # Basis-Argumente
        args = [str(script_path), f"--name={app_name}"]
        args.append("--onefile" if one_file else "--onedir")
        args.append("--console" if console else "--noconsole")
        
        if clean:
            args.extend(["--clean", "--noconfirm"])
            
        # SAFETY NET: Kritische Imports für GUI-User immer erzwingen
        # Dies verhindert "ModuleNotFoundError: yaml" bei Standard-Builds
        safety_imports = [
            "yaml", "yaml.loader", 
            "win32api", "win32con", "win32timezone",
            "shutil", "pkg_resources"
        ]
        for imp in safety_imports:
            args.append(f"--hidden-import={imp}")

        # Icon
        if icon_path and icon_path.exists():
            args.append(f"--icon={str(icon_path)}")
            
        # Assets
        if add_data:
            for item in add_data:
                args.append(f"--add-data={item}")

        # Kommando
        cmd = [sys.executable, "-m", "PyInstaller"] + self._get_framework_paths() + args
        
        # CWD ist hier das Framework selbst (None), da wir absolute Pfade vom GUI bekommen
        return self._run_process(cmd, cwd=None, app_name_hint=app_name)

    def cleanup(self):
        """Löscht temporäre Build-Verzeichnisse."""
        try:
            # Wir behalten dist (Output), löschen aber work und spec
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            # Spec file optional löschen, oder behalten für Debugging? 
            # Enterprise Standard: Clean Environment -> Löschen.
            if self.spec_dir.exists():
                shutil.rmtree(self.spec_dir)
        except Exception as e:
            log.warning(f"Cleanup warnung: {e}")
