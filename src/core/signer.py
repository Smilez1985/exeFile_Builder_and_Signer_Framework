import subprocess
import shutil
import os
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """
    Signiert Executables mit osslsigncode (Binary).
    """

    def __init__(self):
        # Wir suchen das Tool im 'tools' Ordner
        self.root_dir = Path(__file__).parent.parent.parent
        self.tool_path = self.root_dir / "tools" / "osslsigncode.exe"

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name} via osslsigncode...")
        
        if not self.tool_path.exists():
            log.error(f"Signier-Tool nicht gefunden: {self.tool_path}")
            return False

        timestamp_server = "http://timestamp.digicert.com"
        
        # WICHTIG: Absolute Pfade nutzen, da wir das CWD (Arbeitsverzeichnis) ändern!
        abs_exe_path = exe_path.resolve()
        abs_pfx_path = pfx_path.resolve()
        abs_signed_path = abs_exe_path.parent / f"{abs_exe_path.stem}_signed.exe"

        # Befehl aufbauen
        cmd = [
            str(self.tool_path.resolve()), "sign",
            "-pkcs12", str(abs_pfx_path),
            "-pass", password,
            "-n", exe_path.stem,
            "-t", timestamp_server,
            "-in", str(abs_exe_path),
            "-out", str(abs_signed_path)
        ]
        
        # FIX: Environment vorbereiten
        # Wir müssen OpenSSL sagen, wo die Module (legacy.dll) liegen.
        # Unser environment.py hat sie alle flach in den 'tools' Ordner entpackt.
        env = os.environ.copy()
        tools_dir_str = str(self.tool_path.parent.resolve())
        env["OPENSSL_MODULES"] = tools_dir_str

        try:
            # Ausführen
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=tools_dir_str, # CWD ändern, damit Haupt-DLLs (libcrypto) gefunden werden
                env=env            # ENV setzen, damit Module (legacy.dll) gefunden werden
            )

            if result.returncode == 0 and abs_signed_path.exists():
                log.success("Signatur erfolgreich erstellt.")
                
                # Original überschreiben
                if abs_exe_path.exists():
                    os.remove(abs_exe_path)
                shutil.move(abs_signed_path, abs_exe_path)
                
                log.success(f"Datei signiert: {exe_path.name}")
                return True
            else:
                log.error("Signierung fehlgeschlagen.")
                log.error(f"Exit Code: {result.returncode}")
                if result.stdout:
                    log.error(f"Output: {result.stdout.strip()}")
                if result.stderr:
                    log.error(f"Error: {result.stderr.strip()}")
                return False

        except Exception as e:
            log.error(f"Fehler beim Ausführen von osslsigncode: {e}")
            return False
