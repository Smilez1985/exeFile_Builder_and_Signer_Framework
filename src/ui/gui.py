import sys
import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# Pfad-Fix für Importe
sys.path.append(str(Path(__file__).parent))

from src.core.environment import EnvironmentManager
from src.utils.helpers import log

def restart_script():
    """Startet das Script neu, damit frisch installierte Module geladen werden können."""
    log.info("Starte Anwendung neu, um Änderungen zu übernehmen...")
    python = sys.executable
    os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    # 1. ZWINGENDER Environment Check vor dem GUI Start
    # Das hier läuft jetzt immer als erstes.
    try:
        env = EnvironmentManager()
        project_root = Path(__file__).parent
        
        # Prüft requirements.txt und installiert fehlendes (inkl. Ping Loop)
        # Wenn hier etwas installiert wird, ist ein Neustart oft sicherer
        env.prepare_environment(project_root)
        
    except Exception as e:
        log.error(f"Kritischer Fehler beim Environment-Setup: {e}")
        print("Drücken Sie Enter zum Beenden...")
        input()
        sys.exit(1)

    # 2. Import der Drag & Drop Lib (jetzt sicher vorhanden)
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        log.warning("Modul 'tkinterdnd2' wurde installiert, konnte aber nicht sofort geladen werden.")
        restart_script()

    # 3. GUI Start
    # Wir importieren die GUI erst jetzt, damit alle Libs sicher da sind
    try:
        from src.ui.gui import AppGUI
        
        # Wir nutzen jetzt direkt TkinterDnD.Tk als Root
        root = TkinterDnD.Tk()
        
        # Übergeben dnd_enabled=True hart, da wir es jetzt erzwingen
        app = AppGUI(root, dnd_enabled=True)
        
        root.mainloop()
        
    except Exception as e:
        log.error(f"Fehler beim Starten der GUI: {e}")
        print("Drücken Sie Enter zum Beenden...")
        input()
        sys.exit(1)
