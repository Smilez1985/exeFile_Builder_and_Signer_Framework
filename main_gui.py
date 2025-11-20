import sys
import tkinter as tk
from pathlib import Path
from src.utils.helpers import log

# Pfad-Fix
sys.path.append(str(Path(__file__).parent))

from src.ui.gui import AppGUI

# Versuche Drag & Drop Support zu laden
try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    log.warning("Drag & Drop Lib (tkinterdnd2) nicht gefunden. Feature deaktiviert.")

if __name__ == "__main__":
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    app = AppGUI(root, dnd_enabled=DND_AVAILABLE)
    root.mainloop()
