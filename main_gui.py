import sys
from pathlib import Path
import tkinter as tk

# Pfad-Fix
sys.path.append(str(Path(__file__).parent))

from src.ui.gui import AppGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()
