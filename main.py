import sys
import os
from pathlib import Path
from colorama import Fore, Style, init

# Pfad-Fix, damit Imports funktionieren, wenn man python main.py ausführt
sys.path.append(str(Path(__file__).parent))

from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

# Init Colorama
init(autoreset=True)

def print_banner():
    print(f"{Fore.CYAN}")
    print("################################################")
    print("#    EXE BUILDER & SIGNER FRAMEWORK v1.0       #")
    print("#    Powered by Smilez1985 & Gemini Wrapper    #")
    print("################################################")
    print(f"{Style.RESET_ALL}")

def get_input(prompt: str, default=None):
    """Hilfsfunktion für Benutzereingaben mit Default-Wert."""
    if default:
        user_in = input(f"{Fore.GREEN}{prompt} {Fore.RESET}[{default}]: ").strip()
        return user_in if user_in else default
    else:
        user_in = ""
        while not user_in:
            user_in = input(f"{Fore.GREEN}{prompt}: {Fore.RESET}").strip()
        return user_in

def main():
    print_banner()
    orchestrator = BuildOrchestrator()
    
    while True:
        print("\nBitte wählen Sie eine Aktion:")
        print("1. EXE bauen & signieren")
        print("2. Nur Zertifikat erstellen")
        print("3. Umgebung prüfen (Dependencies)")
        print("4. Beenden")
        
        choice = input(f"\n{Fore.YELLOW}Auswahl: {Style.RESET_ALL}").strip()

        if choice == "1":
            print(f"\n{Fore.CYAN}--- Konfiguration ---{Style.RESET_ALL}")
            
            script_file = get_input("Pfad zum Python-Script (.py)", "main.py")
            app_name = get_input("Name der Anwendung", "MeinTool")
            icon_path = get_input("Pfad zum Icon (.ico) [Enter für keins]", "NONE")
            if icon_path == "NONE": icon_path = None
            
            console_choice = get_input("Konsolenfenster anzeigen? (j/n)", "j").lower()
            console = True if console_choice == 'j' else False
            
            cert_name = get_input("Zertifikats-Name (Common Name)", app_name + "_Cert")
            cert_pass = get_input("Zertifikats-Passwort", "123456")
            
            config = {
                "script_file": script_file,
                "app_name": app_name,
                "icon_path": icon_path,
                "console": console,
                "one_file": True,
                "cert_name": cert_name,
                "cert_password": cert_pass
            }
            
            orchestrator.run_full_pipeline(config)
            
        elif choice == "2":
            name = get_input("Zertifikats-Name", "MyCert")
            pwd = get_input("Passwort", "123456")
            try:
                orchestrator.create_or_get_cert(name, pwd)
                log.success("Zertifikat erstellt.")
            except Exception as e:
                log.error(f"Fehler: {e}")

        elif choice == "3":
            orchestrator.setup_environment(Path("."))
            log.success("Umgebungsprüfung abgeschlossen.")

        elif choice == "4":
            print("Beende...")
            sys.exit(0)
            
        else:
            print(f"{Fore.RED}Ungültige Auswahl.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Abbruch durch Benutzer.{Style.RESET_ALL}")
        sys.exit(1)
