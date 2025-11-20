import sys
import os
from pathlib import Path
from colorama import Fore, Style, init

# Pfad-Fix
sys.path.append(str(Path(__file__).parent))

from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

init(autoreset=True)

def get_input(prompt: str, default=None):
    if default:
        user_in = input(f"{Fore.GREEN}{prompt} {Fore.RESET}[{default}]: ").strip()
        return user_in if user_in else default
    else:
        return input(f"{Fore.GREEN}{prompt}: {Fore.RESET}").strip()

def main():
    orchestrator = BuildOrchestrator()
    
    print(f"{Fore.CYAN}### EXE BUILDER CLI - PROFESSIONAL ###{Style.RESET_ALL}")
    print("1. Build & Sign")
    print("2. Exit")
    
    if get_input("Auswahl", "1") == "1":
        script = get_input("Python Script", "main.py")
        app_name = get_input("App Name", "MyTool")
        
        # Cert Mode Auswahl
        print("\n[Zertifikat Modus]")
        print("1 = Neu erstellen oder Cache nutzen (nach Name)")
        print("2 = Vorhandene .pfx Datei nutzen")
        mode_sel = get_input("Wähle", "1")
        
        cert_mode = "auto" if mode_sel == "1" else "file"
        pfx_path = ""
        cert_name = ""
        
        if cert_mode == "file":
            pfx_path = get_input("Pfad zur .pfx Datei")
        else:
            cert_name = get_input("Zertifikats-Name (ID)", "MyCert")

        pwd = get_input("Passwort", "123456")
        
        config = {
            "script_file": script,
            "app_name": app_name,
            "cert_mode": cert_mode,
            "cert_name": cert_name,
            "pfx_path": pfx_path,
            "cert_password": pwd,
            "use_openssl": False, # Im CLI standardmäßig aus für Einfachheit
            "console": True,
            "one_file": True
        }
        
        orchestrator.run_full_pipeline(config)

if __name__ == "__main__":
    main()
