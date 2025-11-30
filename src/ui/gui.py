import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import threading
import json
import os
from pathlib import Path

# Framework Imports
from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

try:
    from tkinterdnd2 import DND_FILES
except ImportError:
    pass

class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str_val):
        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', str_val)
            self.text_widget.see('end')
            self.text_widget.configure(state='disabled')
        except:
            pass
        sys.__stdout__.write(str_val)

    def flush(self):
        sys.__stdout__.flush()

class AppGUI:
    SETTINGS_FILE = Path("settings.json")

    def __init__(self, root, dnd_enabled=False):
        self.root = root
        self.dnd_enabled = dnd_enabled
        self.root.title("ExeFile Builder - Enterprise Edition")
        self.root.geometry("1000x950")
        self.root.configure(bg="#2b2b2b")
        
        # Protokoll für das Schließen des Fensters binden (Auto-Save)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.orchestrator = BuildOrchestrator()
        self._setup_styles()
        self._create_widgets()
        
        if self.dnd_enabled: 
            self._setup_dnd()

        # Historie laden
        self.load_settings()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TButton", background=accent_color, foreground=fg_color, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[('active', '#005f9e')])
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', bg_color)], indicatorcolor=[('selected', accent_color)])
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#555555")
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Segoe UI", 9, "bold"))
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background="#3c3c3c", foreground="#aaaaaa", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", accent_color)], foreground=[("selected", "#ffffff")])

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)
        ttk.Label(main_frame, text="EXE BUILDER & SIGNER", font=("Segoe UI", 18, "bold"), foreground="#007acc").pack(pady=(0, 20))

        # 1. SOURCE
        file_frame = ttk.LabelFrame(main_frame, text=" 1. Quellcode ", padding=15)
        file_frame.pack(fill='x', pady=(0, 15))
        self._create_file_entry(file_frame, "Start Script (.py):", "script_path", 0, "*.py")
        self._create_file_entry(file_frame, "Icon (.ico):", "icon_path", 1, "*.ico")

        # 2. ASSETS
        asset_frame = ttk.LabelFrame(main_frame, text=" 2. Zusatz-Dateien (Configs, Assets) ", padding=15)
        asset_frame.pack(fill='x', pady=(0, 15))
        
        list_frame = ttk.Frame(asset_frame)
        list_frame.pack(fill='x', expand=True)
        
        self.list_assets = tk.Listbox(list_frame, height=5, bg="#3c3c3c", fg="#ffffff", selectbackground="#007acc", borderwidth=0)
        self.list_assets.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        btn_box = ttk.Frame(list_frame)
        btn_box.pack(side='right', fill='y')
        ttk.Button(btn_box, text="➕ Ordner", command=self._add_folder, width=12).pack(pady=2)
        ttk.Button(btn_box, text="➕ Datei", command=self._add_file, width=12).pack(pady=2)
        ttk.Button(btn_box, text="➖ Löschen", command=self._remove_asset, width=12).pack(pady=2)

        # 3. OPTIONS
        config_frame = ttk.LabelFrame(main_frame, text=" 3. Build Optionen ", padding=15)
        config_frame.pack(fill='x', pady=(0, 15))
        
        # Grid Layout für Optionen
        ttk.Label(config_frame, text="App Name:").grid(row=0, column=0, sticky='w')
        self.entry_app_name = ttk.Entry(config_frame, width=30)
        self.entry_app_name.insert(0, "MyTool")
        self.entry_app_name.grid(row=0, column=1, padx=10, sticky='w')
        
        self.var_onefile = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="OneFile", variable=self.var_onefile).grid(row=0, column=2, padx=10)
        
        self.var_console = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Konsole anzeigen", variable=self.var_console).grid(row=0, column=3, padx=10)

        # 4. SIGNING
        cert_group = ttk.LabelFrame(main_frame, text=" 4. Signatur ", padding=15)
        cert_group.pack(fill='x', pady=(0, 15))
        self.notebook = ttk.Notebook(cert_group)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Auto
        tab_auto = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab_auto, text="Automatisch / Cache")
        ttk.Label(tab_auto, text="Zertifikats-Name:").grid(row=0, column=0)
        self.entry_cert_name = ttk.Entry(tab_auto, width=40)
        self.entry_cert_name.insert(0, "MyCert")
        self.entry_cert_name.grid(row=0, column=1, padx=10)
        
        # Tab 2: File (mit Smart Default Path)
        tab_file = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab_file, text="PFX Datei")
        # Hier übergeben wir ein Flag 'is_cert=True' für die intelligente Pfadwahl
        self._create_file_entry(tab_file, "PFX Pfad:", "pfx_path", 0, "*.pfx", is_cert=True)

        pass_frame = ttk.Frame(cert_group, padding=(15,5))
        pass_frame.pack(fill='x')
        ttk.Label(pass_frame, text="Passwort:").pack(side='left')
        self.entry_cert_pass = ttk.Entry(pass_frame, width=20, show="*")
        self.entry_cert_pass.pack(side='left', padx=10)
        self.var_openssl = tk.BooleanVar(value=False)
        ttk.Checkbutton(pass_frame, text="OpenSSL nutzen", variable=self.var_openssl).pack(side='right')

        # ACTION
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="🚀 SPEICHERN & STARTEN", command=self.start_build, width=30).pack(side='left')
        ttk.Button(btn_frame, text="EXIT", command=self.on_close).pack(side='right')

        self.txt_console = tk.Text(main_frame, bg="#1e1e1e", fg="#00ff00", height=8, font=("Consolas", 9), state='disabled')
        self.txt_console.pack(fill='both', expand=True)
        sys.stdout = ConsoleRedirector(self.txt_console)
        sys.stderr = ConsoleRedirector(self.txt_console)

    def _create_file_entry(self, parent, label, attr, row, ftype, is_cert=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=5)
        e = ttk.Entry(parent, width=50)
        e.grid(row=row, column=1, padx=10)
        setattr(self, f"entry_{attr}", e)
        # Lambda bindet is_cert Parameter
        ttk.Button(parent, text="📂", width=4, command=lambda: self._browse_file(e, ftype, is_cert)).grid(row=row, column=2)

    def _browse_file(self, entry, ftype, is_cert=False):
        # Smarte Pfad-Wahl
        initial_dir = None
        
        # 1. Wenn schon was drin steht, nimm dessen Ordner
        current_val = entry.get()
        if current_val and Path(current_val).parent.exists():
            initial_dir = Path(current_val).parent
        # 2. Wenn es ein Zertifikat ist, geh in den certs_store
        elif is_cert:
            store_path = Path("certs_store")
            if store_path.exists():
                initial_dir = store_path.absolute()
        
        f = filedialog.askopenfilename(
            filetypes=[("File", ftype),("All","*.*")],
            initialdir=initial_dir
        )
        if f:
            entry.delete(0, 'end')
            entry.insert(0, f)

    def _add_folder(self):
        d = filedialog.askdirectory()
        if d: self.list_assets.insert('end', d)

    def _add_file(self):
        f = filedialog.askopenfilename()
        if f: self.list_assets.insert('end', f)

    def _remove_asset(self):
        sel = self.list_assets.curselection()
        for index in sel[::-1]: self.list_assets.delete(index)

    def _setup_dnd(self):
        def drop_generic(event, entry):
            path = event.data.strip("{}"); entry.delete(0,'end'); entry.insert(0, path)
        
        def drop_list(event):
            files = self.root.tk.splitlist(event.data)
            for f in files: self.list_assets.insert('end', f)

        self.entry_script_path.drop_target_register(DND_FILES)
        self.entry_script_path.dnd_bind('<<Drop>>', lambda e: drop_generic(e, self.entry_script_path))
        
        self.list_assets.drop_target_register(DND_FILES)
        self.list_assets.dnd_bind('<<Drop>>', drop_list)

    # --- PERSISTENCE LOGIK (SAVE/LOAD) ---
    
    def load_settings(self):
        """Lädt Einstellungen aus JSON und füllt die GUI."""
        if not self.SETTINGS_FILE.exists():
            return

        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Text Felder
            self._set_entry(self.entry_script_path, data.get("script_path"))
            self._set_entry(self.entry_icon_path, data.get("icon_path"))
            self._set_entry(self.entry_app_name, data.get("app_name"))
            self._set_entry(self.entry_cert_name, data.get("cert_name"))
            self._set_entry(self.entry_pfx_path, data.get("pfx_path"))
            
            # Passwort (Optional, falls gewünscht)
            if data.get("cert_password"):
                self._set_entry(self.entry_cert_pass, data.get("cert_password"))

            # Checkboxen
            self.var_onefile.set(data.get("onefile", True))
            self.var_console.set(data.get("console", True))
            self.var_openssl.set(data.get("openssl", False))
            
            # Assets Listbox
            self.list_assets.delete(0, 'end')
            for asset in data.get("assets", []):
                self.list_assets.insert('end', asset)
                
            # Tab Auswahl
            tab_index = data.get("selected_tab", 0)
            if tab_index < self.notebook.index("end"):
                self.notebook.select(tab_index)
                
            log.info("Einstellungen wiederhergestellt.")

        except Exception as e:
            log.warning(f"Konnte Einstellungen nicht laden: {e}")

    def save_settings(self):
        """Speichert den aktuellen GUI Zustand."""
        data = {
            "script_path": self.entry_script_path.get(),
            "icon_path": self.entry_icon_path.get(),
            "app_name": self.entry_app_name.get(),
            "onefile": self.var_onefile.get(),
            "console": self.var_console.get(),
            "cert_name": self.entry_cert_name.get(),
            "pfx_path": self.entry_pfx_path.get(),
            "cert_password": self.entry_cert_pass.get(),
            "openssl": self.var_openssl.get(),
            "assets": self.list_assets.get(0, 'end'),
            "selected_tab": self.notebook.index(self.notebook.select())
        }
        
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            # log.info("Einstellungen gespeichert.")
        except Exception as e:
            log.error(f"Fehler beim Speichern der Settings: {e}")

    def _set_entry(self, entry, value):
        if value:
            entry.delete(0, 'end')
            entry.insert(0, value)

    def on_close(self):
        """Wird beim Beenden aufgerufen."""
        self.save_settings()
        self.root.destroy()

    def start_build(self):
        # Erst speichern, dann bauen!
        self.save_settings()
        
        tab = self.notebook.index(self.notebook.select())
        mode = "auto" if tab == 0 else "file"
        
        assets = self.list_assets.get(0, 'end')

        config = {
            "script_file": self.entry_script_path.get(),
            "app_name": self.entry_app_name.get(),
            "icon_path": self.entry_icon_path.get(),
            "assets": list(assets),
            "console": self.var_console.get(),
            "one_file": self.var_onefile.get(),
            "cert_mode": mode,
            "cert_name": self.entry_cert_name.get(),
            "pfx_path": self.entry_pfx_path.get(),
            "cert_password": self.entry_cert_pass.get(),
            "use_openssl": self.var_openssl.get()
        }
        if not config["script_file"]:
            messagebox.showerror("Fehler", "Kein Script gewählt!"); return
        
        t = threading.Thread(target=self._run, args=(config,))
        t.start()

    def _run(self, conf):
        self.txt_console.configure(state='normal'); self.txt_console.delete(1.0,'end'); self.txt_console.configure(state='disabled')
        try: self.orchestrator.run_full_pipeline(conf)
        except Exception as e: log.error(f"CRASH: {e}")
