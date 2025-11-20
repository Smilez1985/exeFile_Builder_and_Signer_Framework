import subprocess
import shutil
import os
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """
    Signiert Executables mit osslsigncode (Binary).
    Vermeidet PowerShell-Probleme komplett.
    """

    def __init__(self):
        # Wir suchen das Tool im 'tools' Ordner relativ zum Framework Root
        # Root ist src/core/../../ -> 
        self.root_dir = Path(__file__).parent.parent.parent
        self.tool_path = self.root_dir / "tools" / "osslsigncode.exe"

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name} via osslsigncode...")
        
        if not self.tool_path.exists():
            log.error(f"Signier-Tool nicht gefunden: {self.tool_path}")
            log.info("Bitte Neustart versuchen (Environment Check lädt es nach).")
            return False

        timestamp_server = "http://timestamp.digicert.com"
        signed_exe_path = exe_path.parent / f"{exe_path.stem}_signed.exe"

        # Befehl aufbauen:
        # osslsigncode sign -pkcs12 <pfx> -pass <pwd> -n <name> -t <ts> -in <in> -out <out>
        cmd = [
            str(self.tool_path), "sign",
            "-pkcs12", str(pfx_path),
            "-pass", password,
            "-n", exe_path.stem,
            "-t", timestamp_server,
            "-in", str(exe_path),
            "-out", str(signed_exe_path)
        ]

        try:
            # Ausführen ohne Shell (sicherer, kein Encoding Problem)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0 and signed_exe_path.exists():
                # Erfolg! Wir ersetzen das Original mit der signierten Version
                log.success("Signatur erfolgreich erstellt.")
                
                # Original löschen / Backup machen? Wir überschreiben hart für "OneFile" Feeling
                os.remove(exe_path)
                shutil.move(signed_exe_path, exe_path)
                
                log.success(f"Datei signiert und bereit: {exe_path.name}")
                return True
            else:
                log.error("Signierung fehlgeschlagen.")
                log.debug(f"Tool Output: {result.stdout}")
                log.debug(f"Tool Error: {result.stderr}")
                return False

        except Exception as e:
            log.error(f"Fehler beim Ausführen von osslsigncode: {e}")
            return False
