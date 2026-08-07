"""
GranTED Graphical User Interface
Tkinter-based front-end for the GranTED titration analysis tool.
"""

import sys
import json
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Make the package importable when running the file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from granted import __version__
except ImportError:
    __version__ = "0.0.666"


class GranTEDApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"GranTED  v{__version__}")
        self.geometry("780x720")
        self.minsize(700, 650)

        # ------------------ Variables ------------------
        self.data_file = tk.StringVar()
        self.mode = tk.StringVar(value="method_development")
        self.titration_type = tk.StringVar(value="acid_base")
        self.v0 = tk.DoubleVar(value=25.0)
        self.c_titrant = tk.DoubleVar(value=0.1)
        self.vopt = tk.DoubleVar(value=0.0)
        self.output_dir = tk.StringVar(value="./output")

        # Advanced
        self.r2_min = tk.DoubleVar(value=0.99)
        self.unc_max = tk.DoubleVar(value=0.05)
        self.veq_tolerance = tk.DoubleVar(value=0.1)
        self.stability_window = tk.IntVar(value=3)
        self.verbose = tk.BooleanVar(value=True)
        self.trim_forward = tk.BooleanVar(value=False)

        self._create_widgets()
        self._load_settings()
        self._on_mode_change()

    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ====================== TAB 1: Analysis ======================
        tab_analysis = ttk.Frame(notebook, padding=12)
        notebook.add(tab_analysis, text="Analysis")

        # --- Input ---
        input_frame = ttk.LabelFrame(tab_analysis, text="Input", padding=10)
        input_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(input_frame, text="Data file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.data_file, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._browse_data).grid(row=0, column=2)

        self.preview_label = ttk.Label(input_frame, text="No file loaded", foreground="gray")
        self.preview_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # --- Mode ---
        mode_frame = ttk.LabelFrame(tab_analysis, text="Analysis Mode", padding=10)
        mode_frame.pack(fill="x", pady=(0, 10))

        modes = [
            ("method_development", "method_development"),
            ("method_validation", "method_validation"),
            ("method_application", "method_application"),
            ("method_debug", "method_debug"),
        ]
        for i, (text, value) in enumerate(modes):
            ttk.Radiobutton(
                mode_frame, text=text, variable=self.mode, value=value,
                command=self._on_mode_change
            ).grid(row=0, column=i, padx=8, sticky="w")

        # --- Titration Type ---
        type_frame = ttk.LabelFrame(tab_analysis, text="Titration Type", padding=10)
        type_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(type_frame, text="Type:").grid(row=0, column=0, sticky="w")
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.titration_type,
            values=["acid_base", "base_acid", "redox", "complexometric", "precipitation"],
            state="readonly",
            width=22
        )
        type_combo.grid(row=0, column=1, sticky="w", padx=5)

        # --- Basic Parameters ---
        param_frame = ttk.LabelFrame(tab_analysis, text="Basic Parameters", padding=10)
        param_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(param_frame, text="V₀ (mL):").grid(row=0, column=0, sticky="w")
        ttk.Entry(param_frame, textvariable=self.v0, width=12).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(param_frame, text="C_titrant (M):").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Entry(param_frame, textvariable=self.c_titrant, width=12).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(param_frame, text="V_opt (mL):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.vopt_entry = ttk.Entry(param_frame, textvariable=self.vopt, width=12, state="disabled")
        self.vopt_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(8, 0))
        ttk.Label(param_frame, text="(only for method_validation)", foreground="gray").grid(
            row=1, column=2, columnspan=2, sticky="w", padx=5, pady=(8, 0)
        )

        # --- Output ---
        output_frame = ttk.LabelFrame(tab_analysis, text="Output", padding=10)
        output_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(output_frame, text="Output folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(row=0, column=2)

        # --- Action buttons ---
        btn_frame = ttk.Frame(tab_analysis)
        btn_frame.pack(fill="x", pady=(5, 10))

        ttk.Button(btn_frame, text="▶  Run Analysis", command=self._run_analysis).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Open Output Folder", command=self._open_output).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Load Settings", command=self._load_settings_dialog).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Save Settings", command=self._save_settings_dialog).pack(side="right")

        # --- Log ---
        log_frame = ttk.LabelFrame(tab_analysis, text="Status / Log", padding=8)
        log_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

        # ====================== TAB 2: Advanced ======================
        tab_advanced = ttk.Frame(notebook, padding=12)
        notebook.add(tab_advanced, text="Advanced")

        thresh_frame = ttk.LabelFrame(tab_advanced, text="Thresholds", padding=12)
        thresh_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(thresh_frame, text="R² minimum:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(thresh_frame, textvariable=self.r2_min, width=12).grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(thresh_frame, text="Uncertainty max (mL):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(thresh_frame, textvariable=self.unc_max, width=12).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(thresh_frame, text="V_eq tolerance (mL):").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(thresh_frame, textvariable=self.veq_tolerance, width=12).grid(row=2, column=1, sticky="w", padx=8)

        ttk.Label(thresh_frame, text="Stability window:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(thresh_frame, textvariable=self.stability_window, width=12).grid(row=3, column=1, sticky="w", padx=8)

        options_frame = ttk.LabelFrame(tab_advanced, text="Options", padding=12)
        options_frame.pack(fill="x")

        ttk.Checkbutton(options_frame, text="Verbose output", variable=self.verbose).pack(anchor="w", pady=3)
        ttk.Checkbutton(options_frame, text="Trim forward (instead of backward)", variable=self.trim_forward).pack(anchor="w", pady=3)

        ttk.Label(options_frame, text="\n(Additional experimental options can be added here)", foreground="gray").pack(anchor="w")

        # ====================== TAB 3: About ======================
        tab_about = ttk.Frame(notebook, padding=20)
        notebook.add(tab_about, text="About")

        about_text = f"""GranTED – Gran/Schwartz Titration Equivalence-point Determination

Version: {__version__}
Author: Samuele Giani
License: Apache-2.0

An open-source tool for automated potentiometric titration analysis
using the Gran and Schwartz methods, with special support for
method development and green chemistry applications.

Repository:
https://github.com/sgiani95/GranTED

This graphical interface is a convenience front-end for the
command-line tool. All calculations are performed by the same
core engine.
"""
        ttk.Label(tab_about, text=about_text, justify="left").pack(anchor="w")
        ttk.Button(tab_about, text="Open GitHub Repository", command=self._open_github).pack(anchor="w", pady=15)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    def _browse_data(self):
        path = filedialog.askopenfilename(
            title="Select titration data file",
            filetypes=[("Data files", "*.dat *.csv *.txt"), ("All files", "*.*")]
        )
        if path:
            self.data_file.set(path)
            self.preview_label.configure(text=f"Loaded: {Path(path).name}", foreground="black")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_dir.set(path)

    def _on_mode_change(self):
        if self.mode.get() == "method_validation":
            self.vopt_entry.configure(state="normal")
        else:
            self.vopt_entry.configure(state="disabled")

    def _run_analysis(self):
        if not self.data_file.get():
            messagebox.showwarning("Missing data", "Please select a data file first.")
            return

        self._log("=" * 50)
        self._log("Starting analysis...")
        self._log(f"Mode           : {self.mode.get()}")
        self._log(f"Data file      : {self.data_file.get()}")
        self._log(f"Titration type : {self.titration_type.get()}")
        self._log(f"V₀             : {self.v0.get()} mL")
        self._log(f"C_titrant      : {self.c_titrant.get()} M")
        if self.mode.get() == "method_validation":
            self._log(f"V_opt          : {self.vopt.get()} mL")
        self._log(f"Output folder  : {self.output_dir.get()}")
        self._log("→ Analysis logic will be connected in the next step.")
        self._log("Done (placeholder).")

    def _open_output(self):
        path = Path(self.output_dir.get())
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            import os
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _open_github(self):
        webbrowser.open("https://github.com/sgiani95/GranTED")

    def _get_config_path(self) -> Path:
        config_dir = Path.home() / ".config" / "granted"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    def _save_settings(self):
        config = {
            "mode": self.mode.get(),
            "titration_type": self.titration_type.get(),
            "v0": self.v0.get(),
            "c_titrant": self.c_titrant.get(),
            "vopt": self.vopt.get(),
            "output_dir": self.output_dir.get(),
            "r2_min": self.r2_min.get(),
            "unc_max": self.unc_max.get(),
            "veq_tolerance": self.veq_tolerance.get(),
            "stability_window": self.stability_window.get(),
            "verbose": self.verbose.get(),
            "trim_forward": self.trim_forward.get(),
        }
        try:
            with open(self._get_config_path(), "w") as f:
                json.dump(config, f, indent=2)
            self._log("Settings saved automatically.")
        except Exception as e:
            self._log(f"Could not save settings: {e}")

    def _load_settings(self):
        config_path = self._get_config_path()
        if not config_path.exists():
            return
        try:
            with open(config_path) as f:
                config = json.load(f)
            self.mode.set(config.get("mode", "method_development"))
            self.titration_type.set(config.get("titration_type", "acid_base"))
            self.v0.set(config.get("v0", 25.0))
            self.c_titrant.set(config.get("c_titrant", 0.1))
            self.vopt.set(config.get("vopt", 0.0))
            self.output_dir.set(config.get("output_dir", "./output"))
            self.r2_min.set(config.get("r2_min", 0.99))
            self.unc_max.set(config.get("unc_max", 0.05))
            self.veq_tolerance.set(config.get("veq_tolerance", 0.1))
            self.stability_window.set(config.get("stability_window", 3))
            self.verbose.set(config.get("verbose", True))
            self.trim_forward.set(config.get("trim_forward", False))
            self._on_mode_change()
        except Exception:
            pass

    def _save_settings_dialog(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save settings as"
        )
        if path:
            self._save_settings()
            messagebox.showinfo("Saved", f"Settings saved.\n(Auto-config also updated)")

    def _load_settings_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Load settings"
        )
        if path:
            messagebox.showinfo("Info", "Manual load from custom file will be implemented next.")


def main():
    app = GranTEDApp()

    # Force window to the front (important on some Linux systems)
    app.lift()
    app.attributes("-topmost", True)
    app.after(100, lambda: app.attributes("-topmost", False))

    app.mainloop()


if __name__ == "__main__":
    main()
