"""
Tkinter GUI for EpiTop1 --- B Linear Epitope Predictor.

A professional scientific interface for B-cell linear epitope prediction
from protein sequences and optional PDB structures.

Features:
    - Protein sequence input (text / FASTA / PDB)
    - Dual prediction pipeline (Core + advanced Bio module)
    - Interactive results with sortable tables
    - Embedded matplotlib score-profile charts
    - CSV / JSON export for both pipelines
    - Summary statistics dashboard
    - Copy-to-clipboard and right-click menus

Design: Modern scientific look with colour-coded score indicators,
clear typography, and responsive layout.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Optional, List
from datetime import datetime

import numpy as np

# Attempt to load matplotlib for embedded charts
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GUI_SETTINGS, SCORING_WEIGHTS, WINDOW_SIZES, EPITOPE_CRITERIA
from core.scoring import GlobalScorer, ResidueScore
from core.epitope_selector import EpitopeSelector, EpitopeCandidate
from core.hydrophobicity import KyteDoolittlePredictor
from structure.pdb_parser import PDBParser
from io_utils import parse_sequence_input
from io_utils import export_csv, export_json, export_residue_table

# -- Version information ------------------------------------------------------
__version__ = "2.0.0"
_APP_TITLE = "EpiTop1 --- B Linear Epitope Predictor"
_ABOUT_TEXT = (
    "EpiTop1 v{version}\n"
    "B-cell Linear Epitope Predictor\n\n"
    "A bioinformatics tool combining multiple physicochemical\n"
    "scales for sequence-based B-cell epitope prediction.\n\n"
    "Methods (Core):\n"
    "  - Hopp & Woods (1981) --- Hydrophilicity\n"
    "  - Kyte & Doolittle (1982) --- Hydrophobicity\n"
    "  - Karplus & Schulz (1985) --- Flexibility\n"
    "  - Emini et al. (1985) --- Surface Accessibility\n"
    "  - Kolaskar & Tongaonkar (1990) --- Antigenicity\n\n"
    "Methods (Bio module):\n"
    "  + Parker (1986) --- Hydrophilicity\n"
    "  + Chou & Fasman (1978) --- Beta-turn\n"
    "  + BepiPred-1.0 (Larsen 2006) --- Propensity\n"
    "  + Levitt (1978) --- Coil/Disorder\n"
    "  + Welling et al. (1985) --- Antigenicity\n\n"
    "License: Academic / Research Use"
)


# -- Colour palette -----------------------------------------------------------
_PAL = {
    "bg":             "#F5F7FA",
    "panel":          "#FFFFFF",
    "accent":         "#2E86AB",
    "accent_dark":    "#1B5E7B",
    "success":        "#28A745",
    "warning":        "#E8A317",
    "danger":         "#DC3545",
    "text":           "#212529",
    "text_secondary": "#6C757D",
    "border":         "#DEE2E6",
    "highlight":      "#E3F2FD",
    "header_bg":      "#2E86AB",
    "header_fg":      "#FFFFFF",
    "score_high":     "#28A745",
    "score_mid":      "#E8A317",
    "score_low":      "#DC3545",
}

# -- Chart colours ------------------------------------------------------------
_CHART_COLOURS = {
    "combined":       "#2E86AB",
    "hydrophilicity": "#28A745",
    "accessibility":  "#FFC107",
    "flexibility":    "#DC3545",
    "beta_turn":      "#6F42C1",
    "antigenicity":   "#FD7E14",
    "bepipred":       "#20C997",
    "coil":           "#E83E8C",
    "welling":        "#6610F2",
    "epitope_fill":   "#2E86AB",
}


class EpiTopApp:
    """Main GUI application for EpiTop1 B Linear Epitope Predictor."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(_APP_TITLE)
        self.root.geometry(
            f"{GUI_SETTINGS['window_width']}x{GUI_SETTINGS['window_height']}"
        )
        self.root.configure(bg=_PAL["bg"])
        self.root.minsize(1000, 700)

        # Try to set icon (fail silently if not available)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # -- State ------------------------------------------------------------
        self.pdb_path: Optional[str] = None
        self.sequence: str = ""
        self.sequence_header: str = ""
        self.residue_scores: List[ResidueScore] = []
        self.epitopes: List[EpitopeCandidate] = []
        self.has_pdb: bool = False
        self.is_analyzing: bool = False
        self.analysis_start_time: Optional[float] = None

        # Bio-module state
        self.bio_residue_results: list = []
        self.bio_hits: list = []

        # -- Style ------------------------------------------------------------
        self._setup_styles()

        # -- Menu bar ---------------------------------------------------------
        self._build_menubar()

        # -- Build UI ---------------------------------------------------------
        self._build_ui()

    # =================================================================
    # STYLES
    # =================================================================
    def _setup_styles(self):
        """Configure ttk styles for a clean, modern scientific look."""
        style = ttk.Style()
        style.theme_use("clam")

        bg = _PAL["bg"]
        accent = _PAL["accent"]
        font_family = GUI_SETTINGS.get("font_family", "Segoe UI")
        font_size = GUI_SETTINGS.get("font_size", 10)

        style.configure(".", background=bg, font=(font_family, font_size))
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, font=(font_family, font_size))

        style.configure(
            "Title.TLabel", background=bg,
            font=(font_family, 18, "bold"), foreground=accent,
        )
        style.configure(
            "Subtitle.TLabel", background=bg,
            font=(font_family, 11, "bold"), foreground="#333333",
        )
        style.configure(
            "Info.TLabel", background=bg,
            font=(font_family, 9), foreground=_PAL["text_secondary"],
        )
        style.configure(
            "Success.TLabel", background=bg,
            font=(font_family, 10, "bold"), foreground=_PAL["success"],
        )
        style.configure(
            "Panel.TFrame", background=_PAL["panel"], relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TButton", font=(font_family, font_size, "bold"), padding=(12, 6),
        )
        style.configure(
            "Accent.TButton", font=(font_family, 12, "bold"),
            padding=(20, 10), background=accent, foreground="white",
        )
        style.map(
            "Accent.TButton",
            background=[("active", _PAL["accent_dark"])],
        )
        style.configure(
            "Export.TButton", font=(font_family, 9), padding=(8, 4),
        )
        style.configure("TNotebook", background=bg)
        style.configure(
            "TNotebook.Tab", font=(font_family, font_size), padding=(12, 6),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", _PAL["panel"]), ("!selected", bg)],
            foreground=[("selected", accent), ("!selected", _PAL["text"])],
        )

        # Treeview
        style.configure(
            "Treeview", font=(font_family, 9), rowheight=26,
            background="white", fieldbackground="white",
        )
        style.configure(
            "Treeview.Heading",
            font=(font_family, 9, "bold"),
            background=_PAL["header_bg"], foreground=_PAL["header_fg"],
            relief="flat", padding=(4, 4),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", _PAL["accent_dark"])],
        )
        style.map(
            "Treeview",
            background=[("selected", _PAL["highlight"])],
            foreground=[("selected", _PAL["text"])],
        )

        # Progress bar
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=_PAL["border"], background=accent,
        )

        # Separator
        style.configure("TSeparator", background=_PAL["border"])

        # LabelFrame
        style.configure(
            "TLabelframe", background=bg,
            font=(font_family, 10, "bold"),
        )
        style.configure("TLabelframe.Label", background=bg, foreground=accent)

    # =================================================================
    # MENU BAR
    # =================================================================
    def _build_menubar(self):
        """Build the application menu bar."""
        menubar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open FASTA...", command=self._load_fasta,
            accelerator="Ctrl+O",
        )
        file_menu.add_command(label="Load PDB...", command=self._load_pdb)
        file_menu.add_separator()
        file_menu.add_command(label="Export CSV...", command=self._export_csv)
        file_menu.add_command(label="Export JSON...", command=self._export_json)
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit", command=self.root.quit, accelerator="Alt+F4",
        )

        # Analysis menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(
            label="Run Analysis", command=self._run_analysis,
            accelerator="Ctrl+Enter",
        )
        analysis_menu.add_separator()
        analysis_menu.add_command(
            label="Clear Results", command=self._clear_results,
        )

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About EpiTop1", command=self._show_about)
        help_menu.add_command(
            label="Method References", command=self._show_references,
        )

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self._load_fasta())
        self.root.bind("<Control-Return>", lambda e: self._run_analysis())

    # =================================================================
    # UI LAYOUT
    # =================================================================
    def _build_ui(self):
        """Build the main application UI."""
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        self._build_header(main)

        # Content: PanedWindow (Input | Results)
        pane = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Left panel -- Input
        left = ttk.Frame(pane, padding=5)
        pane.add(left, weight=1)
        self._build_input_panel(left)

        # Right panel -- Results
        right = ttk.Frame(pane, padding=5)
        pane.add(right, weight=3)
        self._build_results_panel(right)

        # Bottom status bar
        self._build_status_bar(main)

    def _build_header(self, parent):
        """Build the application header bar."""
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(
            header, text="EpiTop1", style="Title.TLabel",
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            text=f"B-cell Linear Epitope Predictor  v{__version__}",
            style="Info.TLabel",
        ).pack(side=tk.LEFT, padx=(8, 0), pady=(6, 0))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X)

    def _build_status_bar(self, parent):
        """Build the bottom status bar."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(
            fill=tk.X, before=status_frame,
        )

        self.status_var = tk.StringVar(
            value="Ready -- Enter a protein sequence or load a FASTA file",
        )
        ttk.Label(
            status_frame, textvariable=self.status_var,
            style="Info.TLabel", anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.seq_length_var = tk.StringVar(value="")
        ttk.Label(
            status_frame, textvariable=self.seq_length_var,
            style="Info.TLabel", anchor=tk.E,
        ).pack(side=tk.RIGHT, padx=(8, 0))

    # =================================================================
    # INPUT PANEL
    # =================================================================
    def _build_input_panel(self, parent):
        """Build the input panel (left side)."""
        # Sequence Input
        seq_lf = ttk.LabelFrame(parent, text=" Sequence Input ", padding=8)
        seq_lf.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.seq_text = scrolledtext.ScrolledText(
            seq_lf, height=10, width=40,
            font=("Consolas", 10), wrap=tk.WORD,
            relief=tk.SOLID, borderwidth=1, bg="white",
        )
        self.seq_text.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.seq_text.insert("1.0", "Paste protein sequence or FASTA here...")
        self.seq_text.configure(fg="grey")
        self.seq_text.bind("<FocusIn>", self._on_seq_focus_in)
        self.seq_text.bind("<FocusOut>", self._on_seq_focus_out)

        # Load buttons row
        btn_row = ttk.Frame(seq_lf)
        btn_row.pack(fill=tk.X)

        ttk.Button(
            btn_row, text="Load FASTA", command=self._load_fasta,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))

        ttk.Button(
            btn_row, text="Load PDB", command=self._load_pdb,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        # PDB status
        self.pdb_var = tk.StringVar(value="No PDB loaded")
        ttk.Label(
            seq_lf, textvariable=self.pdb_var, style="Info.TLabel",
        ).pack(fill=tk.X, pady=(4, 0))

        # -- Parameters -------------------------------------------------------
        params_lf = ttk.LabelFrame(parent, text=" Parameters ", padding=8)
        params_lf.pack(fill=tk.X, pady=(0, 6))

        grid = ttk.Frame(params_lf)
        grid.pack(fill=tk.X)

        # Min length
        ttk.Label(grid, text="Min length:").grid(
            row=0, column=0, sticky=tk.W, pady=2,
        )
        self.min_len_var = tk.IntVar(value=EPITOPE_CRITERIA["min_length"])
        ttk.Spinbox(
            grid, from_=5, to=30, textvariable=self.min_len_var, width=5,
        ).grid(row=0, column=1, sticky=tk.W, padx=(4, 12), pady=2)

        # Max length
        ttk.Label(grid, text="Max length:").grid(
            row=0, column=2, sticky=tk.W, pady=2,
        )
        self.max_len_var = tk.IntVar(value=EPITOPE_CRITERIA["max_length"])
        ttk.Spinbox(
            grid, from_=10, to=50, textvariable=self.max_len_var, width=5,
        ).grid(row=0, column=3, sticky=tk.W, padx=(4, 0), pady=2)

        # Min score
        ttk.Label(grid, text="Min score:").grid(
            row=1, column=0, sticky=tk.W, pady=2,
        )
        self.min_score_var = tk.DoubleVar(
            value=EPITOPE_CRITERIA["min_global_score"],
        )
        ttk.Spinbox(
            grid, from_=0.0, to=1.0, increment=0.05,
            textvariable=self.min_score_var, width=5, format="%.2f",
        ).grid(row=1, column=1, sticky=tk.W, padx=(4, 12), pady=2)

        # Top N
        ttk.Label(grid, text="Top N:").grid(
            row=1, column=2, sticky=tk.W, pady=2,
        )
        self.top_n_var = tk.IntVar(value=EPITOPE_CRITERIA["top_n_epitopes"])
        ttk.Spinbox(
            grid, from_=1, to=100, textvariable=self.top_n_var, width=5,
        ).grid(row=1, column=3, sticky=tk.W, padx=(4, 0), pady=2)

        # Bio module toggle
        self.use_bio_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            params_lf,
            text="Enable Advanced Bio Module (8-channel consensus)",
            variable=self.use_bio_var,
        ).pack(fill=tk.X, pady=(6, 0))

        # -- Analyze Button ----------------------------------------------------
        self.analyze_btn = ttk.Button(
            parent, text="Analyze Sequence", style="Accent.TButton",
            command=self._run_analysis,
        )
        self.analyze_btn.pack(fill=tk.X, pady=(0, 6))

        # Progress bar (hidden by default)
        self.progress = ttk.Progressbar(
            parent, mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress_label = ttk.Label(parent, text="", style="Info.TLabel")

        # -- Export Buttons ----------------------------------------------------
        export_lf = ttk.LabelFrame(parent, text=" Export ", padding=8)
        export_lf.pack(fill=tk.X)

        export_row1 = ttk.Frame(export_lf)
        export_row1.pack(fill=tk.X, pady=(0, 4))

        self.export_csv_btn = ttk.Button(
            export_row1, text="Export CSV", style="Export.TButton",
            command=self._export_csv, state=tk.DISABLED,
        )
        self.export_csv_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.export_json_btn = ttk.Button(
            export_row1, text="Export JSON", style="Export.TButton",
            command=self._export_json, state=tk.DISABLED,
        )
        self.export_json_btn.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2,
        )

        export_row2 = ttk.Frame(export_lf)
        export_row2.pack(fill=tk.X)

        self.export_bio_csv_btn = ttk.Button(
            export_row2, text="Export Bio CSV", style="Export.TButton",
            command=self._export_bio_csv, state=tk.DISABLED,
        )
        self.export_bio_csv_btn.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2,
        )

        self.export_bio_json_btn = ttk.Button(
            export_row2, text="Export Bio JSON", style="Export.TButton",
            command=self._export_bio_json, state=tk.DISABLED,
        )
        self.export_bio_json_btn.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2,
        )

    # =================================================================
    # RESULTS PANEL
    # =================================================================
    def _build_results_panel(self, parent):
        """Build the results panel (right side)."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Summary Dashboard
        summary_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(summary_frame, text="  Summary  ")
        self._build_summary_tab(summary_frame)

        # Tab 2: Epitope Candidates
        epitope_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(epitope_frame, text="  Core Epitopes  ")
        self._build_epitope_table(epitope_frame)

        # Tab 3: Bio Module Epitopes
        bio_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(bio_frame, text="  Bio Epitopes  ")
        self._build_bio_table(bio_frame)

        # Tab 4: Residue Scores
        residue_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(residue_frame, text="  Residue Scores  ")
        self._build_residue_table(residue_frame)

        # Tab 5: Score Profile Chart (matplotlib or text fallback)
        chart_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(chart_frame, text="  Score Chart  ")
        self._build_chart_tab(chart_frame)

        # Tab 6: Text Profile
        profile_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(profile_frame, text="  Text Profile  ")
        self._build_profile_view(profile_frame)

    # -- Summary Dashboard ---------------------------------------------------
    def _build_summary_tab(self, parent):
        """Build a summary statistics dashboard."""
        self.summary_text = scrolledtext.ScrolledText(
            parent, font=("Consolas", 10), wrap=tk.WORD,
            bg="white", relief=tk.SOLID, borderwidth=1,
            state=tk.DISABLED, padx=16, pady=12,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for coloured output
        self.summary_text.tag_configure(
            "title", font=("Segoe UI", 16, "bold"),
            foreground=_PAL["accent"],
        )
        self.summary_text.tag_configure(
            "heading", font=("Segoe UI", 12, "bold"),
            foreground="#333333", spacing1=12,
        )
        self.summary_text.tag_configure(
            "subheading", font=("Segoe UI", 10, "bold"),
            foreground=_PAL["text_secondary"], spacing1=6,
        )
        self.summary_text.tag_configure(
            "score_high", foreground=_PAL["score_high"],
            font=("Consolas", 10, "bold"),
        )
        self.summary_text.tag_configure(
            "score_mid", foreground=_PAL["score_mid"],
            font=("Consolas", 10, "bold"),
        )
        self.summary_text.tag_configure(
            "score_low", foreground=_PAL["score_low"],
            font=("Consolas", 10, "bold"),
        )
        self.summary_text.tag_configure(
            "normal", font=("Consolas", 10), foreground=_PAL["text"],
        )
        self.summary_text.tag_configure(
            "mono", font=("Consolas", 9), foreground=_PAL["text_secondary"],
        )
        self.summary_text.tag_configure(
            "separator", font=("Consolas", 9),
            foreground=_PAL["border"], spacing1=4,
        )

    # -- Epitope Tables -------------------------------------------------------
    def _build_epitope_table(self, parent):
        """Build the core epitope candidates table."""
        ttk.Label(
            parent,
            text="Core module: Hopp-Woods, Kyte-Doolittle, Karplus-Schulz, "
                 "Emini, Kolaskar-Tongaonkar",
            style="Info.TLabel",
        ).pack(fill=tk.X, pady=(0, 4))

        columns = (
            "rank", "start", "end", "length", "sequence",
            "global_score", "hydrophilicity", "accessibility",
            "flexibility", "antigenicity",
        )

        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        self.epitope_tree = ttk.Treeview(
            container, columns=columns, show="headings",
            selectmode="browse",
        )

        headers = {
            "rank": ("Rank", 50),
            "start": ("Start", 60),
            "end": ("End", 60),
            "length": ("Len", 50),
            "sequence": ("Peptide Sequence", 260),
            "global_score": ("Score", 70),
            "hydrophilicity": ("Hydrophil.", 80),
            "accessibility": ("Access.", 75),
            "flexibility": ("Flex.", 65),
            "antigenicity": ("Antig.", 70),
        }

        for col, (text, width) in headers.items():
            self.epitope_tree.heading(
                col, text=text,
                command=lambda c=col: self._sort_treeview(
                    self.epitope_tree, c,
                ),
            )
            anchor = tk.W if col == "sequence" else tk.CENTER
            self.epitope_tree.column(
                col, width=width, minwidth=40, anchor=anchor,
            )

        yscroll = ttk.Scrollbar(
            container, orient=tk.VERTICAL,
            command=self.epitope_tree.yview,
        )
        xscroll = ttk.Scrollbar(
            container, orient=tk.HORIZONTAL,
            command=self.epitope_tree.xview,
        )
        self.epitope_tree.configure(
            yscrollcommand=yscroll.set, xscrollcommand=xscroll.set,
        )

        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.epitope_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right-click context menu
        self._add_tree_context_menu(self.epitope_tree, "sequence")

    def _build_bio_table(self, parent):
        """Build the bio-module epitope candidates table."""
        ttk.Label(
            parent,
            text="Bio module: 8-channel consensus scoring "
                 "(Parker, Emini, K-S, Chou-Fasman, K-T, BepiPred, Levitt, Welling)",
            style="Info.TLabel",
        ).pack(fill=tk.X, pady=(0, 4))

        columns = (
            "rank", "start", "end", "length", "sequence",
            "combined_score", "hydrophilicity", "accessibility",
            "flexibility", "beta_turn", "antigenicity",
            "bepipred", "welling", "consensus",
        )

        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        self.bio_tree = ttk.Treeview(
            container, columns=columns, show="headings",
            selectmode="browse",
        )

        headers = {
            "rank": ("Rank", 50),
            "start": ("Start", 60),
            "end": ("End", 60),
            "length": ("Len", 50),
            "sequence": ("Peptide Sequence", 220),
            "combined_score": ("Score", 70),
            "hydrophilicity": ("Hydrophil.", 80),
            "accessibility": ("Access.", 75),
            "flexibility": ("Flex.", 65),
            "beta_turn": ("B-Turn", 65),
            "antigenicity": ("Antig.", 70),
            "bepipred": ("BepiPred", 75),
            "welling": ("Welling", 70),
            "consensus": ("Cons.", 60),
        }

        for col, (text, width) in headers.items():
            self.bio_tree.heading(
                col, text=text,
                command=lambda c=col: self._sort_treeview(self.bio_tree, c),
            )
            anchor = tk.W if col == "sequence" else tk.CENTER
            self.bio_tree.column(
                col, width=width, minwidth=40, anchor=anchor,
            )

        yscroll = ttk.Scrollbar(
            container, orient=tk.VERTICAL, command=self.bio_tree.yview,
        )
        xscroll = ttk.Scrollbar(
            container, orient=tk.HORIZONTAL, command=self.bio_tree.xview,
        )
        self.bio_tree.configure(
            yscrollcommand=yscroll.set, xscrollcommand=xscroll.set,
        )

        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.bio_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._add_tree_context_menu(self.bio_tree, "sequence")

    def _build_residue_table(self, parent):
        """Build the per-residue scores table."""
        columns = (
            "pos", "aa", "hydrophilicity", "hydrophobicity",
            "flexibility", "accessibility", "antigenicity",
            "sasa", "global_score", "exposed",
        )

        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        self.residue_tree = ttk.Treeview(
            container, columns=columns, show="headings",
            selectmode="browse",
        )

        headers = {
            "pos": ("Pos", 50),
            "aa": ("AA", 40),
            "hydrophilicity": ("Hydrophil.", 80),
            "hydrophobicity": ("Hydrophob.", 80),
            "flexibility": ("Flex.", 65),
            "accessibility": ("Access.", 75),
            "antigenicity": ("Antig.", 70),
            "sasa": ("SASA", 65),
            "global_score": ("Score", 70),
            "exposed": ("Exposed", 60),
        }

        for col, (text, width) in headers.items():
            self.residue_tree.heading(
                col, text=text,
                command=lambda c=col: self._sort_treeview(
                    self.residue_tree, c,
                ),
            )
            self.residue_tree.column(
                col, width=width, minwidth=35, anchor=tk.CENTER,
            )

        yscroll = ttk.Scrollbar(
            container, orient=tk.VERTICAL,
            command=self.residue_tree.yview,
        )
        self.residue_tree.configure(yscrollcommand=yscroll.set)

        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.residue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # -- Chart Tab (matplotlib) -----------------------------------------------
    def _build_chart_tab(self, parent):
        """Build the embedded matplotlib chart tab."""
        self.chart_frame = parent
        self.chart_canvas = None

        if not HAS_MPL:
            ttk.Label(
                parent,
                text="Install matplotlib for interactive score charts:\n"
                     "  pip install matplotlib",
                style="Info.TLabel", justify=tk.CENTER,
            ).pack(expand=True)

    # -- Text Profile Tab -----------------------------------------------------
    def _build_profile_view(self, parent):
        """Build the score profile text visualization."""
        self.profile_text = scrolledtext.ScrolledText(
            parent, font=("Consolas", 9), wrap=tk.NONE,
            bg="white", relief=tk.SOLID, borderwidth=1,
            state=tk.DISABLED,
        )
        self.profile_text.pack(fill=tk.BOTH, expand=True)

    # =================================================================
    # CONTEXT MENUS & HELPERS
    # =================================================================
    def _add_tree_context_menu(self, tree: ttk.Treeview, seq_col: str):
        """Add a right-click context menu to a Treeview."""
        menu = tk.Menu(tree, tearoff=0)
        menu.add_command(
            label="Copy Sequence",
            command=lambda: self._copy_tree_cell(tree, seq_col),
        )
        menu.add_command(
            label="Copy Row",
            command=lambda: self._copy_tree_row(tree),
        )
        menu.add_separator()
        menu.add_command(
            label="Select All Rows",
            command=lambda: self._select_all_tree(tree),
        )

        def _popup(event):
            try:
                tree.selection_set(tree.identify_row(event.y))
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        tree.bind("<Button-3>", _popup)

    def _copy_tree_cell(self, tree: ttk.Treeview, col: str):
        """Copy a specific cell value from the selected Treeview row."""
        sel = tree.selection()
        if sel:
            cols = tree["columns"]
            idx = list(cols).index(col) if col in cols else 0
            value = tree.item(sel[0], "values")[idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(value))

    def _copy_tree_row(self, tree: ttk.Treeview):
        """Copy entire selected row as tab-separated text."""
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0], "values")
            self.root.clipboard_clear()
            self.root.clipboard_append("\t".join(str(v) for v in values))

    def _select_all_tree(self, tree: ttk.Treeview):
        """Select all items in a Treeview."""
        items = tree.get_children()
        tree.selection_set(items)

    def _sort_treeview(self, tree: ttk.Treeview, col: str):
        """Sort Treeview by column (toggle ascending/descending)."""
        data = [
            (tree.set(child, col), child)
            for child in tree.get_children("")
        ]
        # Try numeric sort
        try:
            data.sort(key=lambda t: float(t[0]), reverse=True)
        except ValueError:
            data.sort(key=lambda t: t[0])

        for idx, (_, child) in enumerate(data):
            tree.move(child, "", idx)

    def _on_seq_focus_in(self, event):
        """Clear placeholder text on focus."""
        content = self.seq_text.get("1.0", tk.END).strip()
        if content == "Paste protein sequence or FASTA here...":
            self.seq_text.delete("1.0", tk.END)
            self.seq_text.configure(fg="black")

    def _on_seq_focus_out(self, event):
        """Show placeholder text if empty."""
        content = self.seq_text.get("1.0", tk.END).strip()
        if not content:
            self.seq_text.insert(
                "1.0", "Paste protein sequence or FASTA here...",
            )
            self.seq_text.configure(fg="grey")

    # =================================================================
    # FILE LOADING
    # =================================================================
    def _load_fasta(self):
        """Load a FASTA file."""
        filepath = filedialog.askopenfilename(
            title="Select FASTA File",
            filetypes=[
                ("FASTA files", "*.fasta *.fa *.faa *.fas *.txt"),
                ("All files", "*.*"),
            ],
        )
        if filepath:
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                self.seq_text.configure(fg="black")
                self.seq_text.delete("1.0", tk.END)
                self.seq_text.insert("1.0", content)
                basename = os.path.basename(filepath)
                self.status_var.set(f"FASTA loaded: {basename}")
                # Update sequence length
                lines = content.strip().splitlines()
                seq_lines = [
                    ln for ln in lines
                    if not ln.startswith(">") and ln.strip()
                ]
                approx_len = sum(len(ln.strip()) for ln in seq_lines)
                self.seq_length_var.set(f"~{approx_len} residues")
            except Exception as e:
                messagebox.showerror("Error", f"Could not read file:\n{e}")

    def _load_pdb(self):
        """Load a PDB file."""
        filepath = filedialog.askopenfilename(
            title="Select PDB File",
            filetypes=[
                ("PDB files", "*.pdb *.ent"),
                ("All files", "*.*"),
            ],
        )
        if filepath:
            self.pdb_path = filepath
            basename = os.path.basename(filepath)
            self.pdb_var.set(f"PDB: {basename}")
            self.status_var.set(f"PDB loaded: {basename}")

    # =================================================================
    # ANALYSIS
    # =================================================================
    def _run_analysis(self):
        """Run the epitope prediction analysis."""
        if self.is_analyzing:
            return

        # Get sequence
        seq_input = self.seq_text.get("1.0", tk.END).strip()
        if (
            not seq_input
            or seq_input == "Paste protein sequence or FASTA here..."
        ):
            messagebox.showwarning(
                "Input Required",
                "Please enter a protein sequence or load a FASTA file.",
            )
            return

        try:
            self.sequence_header, self.sequence = parse_sequence_input(
                seq_input,
            )
        except ValueError as e:
            messagebox.showerror("Sequence Error", str(e))
            return

        # Update UI
        self.is_analyzing = True
        self.analysis_start_time = datetime.now().timestamp()
        self.analyze_btn.configure(state=tk.DISABLED)
        self.progress_label.pack(fill=tk.X, pady=(2, 0))
        self.progress.pack(fill=tk.X, pady=(2, 4))
        self.progress.start(20)
        self._update_progress("Validating sequence...")
        self.seq_length_var.set(f"{len(self.sequence)} residues")

        # Run in background thread
        thread = threading.Thread(target=self._analysis_worker, daemon=True)
        thread.start()

    def _update_progress(self, msg: str):
        """Update the progress label (thread-safe)."""
        self.progress_label.configure(text=f"  {msg}")
        self.status_var.set(msg)

    def _analysis_worker(self):
        """Background analysis worker thread."""
        try:
            structural_sasa = None
            excluded_regions = []

            # Parse PDB if provided
            if self.pdb_path and os.path.exists(self.pdb_path):
                self.root.after(
                    0, lambda: self._update_progress(
                        "Parsing PDB structure...",
                    ),
                )
                pdb_parser = PDBParser(probe_radius=1.4, n_sasa_points=92)
                pdb_parser.parse(self.pdb_path)

                self.root.after(
                    0, lambda: self._update_progress(
                        "Computing SASA from structure...",
                    ),
                )
                relative_sasa = pdb_parser.compute_sasa()

                pdb_seq = pdb_parser.get_sequence()
                if pdb_seq:
                    alignment = pdb_parser.align_to_sequence(self.sequence)
                    structural_sasa = np.zeros(len(self.sequence))
                    for seq_pos, pdb_idx in alignment.items():
                        if pdb_idx < len(pdb_parser.residues):
                            structural_sasa[seq_pos] = (
                                pdb_parser.residues[pdb_idx].relative_sasa
                            )
                    self.has_pdb = True

            # Compute core scores
            self.root.after(
                0, lambda: self._update_progress(
                    "Computing bioinformatics scores (5 methods)...",
                ),
            )

            criteria = dict(EPITOPE_CRITERIA)
            criteria["min_length"] = self.min_len_var.get()
            criteria["max_length"] = self.max_len_var.get()
            criteria["min_global_score"] = self.min_score_var.get()
            criteria["top_n_epitopes"] = self.top_n_var.get()

            scorer = GlobalScorer()
            self.residue_scores = scorer.get_residue_scores(
                self.sequence, structural_sasa,
            )

            # Detect transmembrane regions
            self.root.after(
                0, lambda: self._update_progress(
                    "Detecting transmembrane regions...",
                ),
            )
            kd_predictor = KyteDoolittlePredictor(window_size=11)
            tm_regions = kd_predictor.detect_transmembrane_regions(
                self.sequence,
            )
            for tm in tm_regions:
                excluded_regions.append((tm["start"], tm["end"]))

            # Select epitopes (core)
            self.root.after(
                0, lambda: self._update_progress(
                    "Selecting core epitope candidates...",
                ),
            )
            selector = EpitopeSelector(criteria=criteria)
            self.epitopes = selector.find_epitopes(
                self.sequence, self.residue_scores, excluded_regions,
            )

            # -- Bio module (optional) ----------------------------------------
            self.bio_residue_results = []
            self.bio_hits = []
            if self.use_bio_var.get():
                self.root.after(
                    0, lambda: self._update_progress(
                        "Running Bio module (7-channel consensus)...",
                    ),
                )
                from bio.scoring import CombinedScorer
                from bio.epitope_detector import EpitopeDetector
                from config import (
                    BIO_SCORING_WEIGHTS, BIO_WINDOW_SIZES,
                    BIO_DETECTION_PARAMS,
                )

                bio_scorer = CombinedScorer(
                    weights=dict(BIO_SCORING_WEIGHTS),
                    window_sizes=dict(BIO_WINDOW_SIZES),
                )
                self.bio_residue_results = bio_scorer.get_residue_results(
                    self.sequence, structural_sasa,
                )

                bio_params = dict(BIO_DETECTION_PARAMS)
                bio_params["min_length"] = self.min_len_var.get()
                bio_params["max_length"] = self.max_len_var.get()
                bio_params["min_score"] = self.min_score_var.get()
                bio_params["top_n"] = self.top_n_var.get()

                bio_detector = EpitopeDetector(bio_params)
                self.bio_hits = bio_detector.detect(
                    self.sequence, self.bio_residue_results,
                )

            # Update UI on main thread
            self.root.after(0, self._display_results)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Analysis Error",
                    f"An error occurred during analysis:\n\n{e}\n\n"
                    f"Details:\n{tb[-500:]}",
                ),
            )
            self.root.after(0, self._analysis_done)

    # =================================================================
    # DISPLAY RESULTS
    # =================================================================
    def _display_results(self):
        """Display analysis results in the GUI."""
        # Clear previous results
        self.epitope_tree.delete(*self.epitope_tree.get_children())
        self.residue_tree.delete(*self.residue_tree.get_children())
        self.bio_tree.delete(*self.bio_tree.get_children())

        # -- Core epitope table -----------------------------------------------
        for ep in self.epitopes:
            self.epitope_tree.insert("", tk.END, values=(
                ep.rank,
                ep.start,
                ep.end,
                ep.length,
                ep.sequence,
                f"{ep.global_score:.4f}",
                f"{ep.hydrophilicity:.3f}",
                f"{ep.accessibility:.3f}",
                f"{ep.flexibility:.3f}",
                f"{ep.antigenicity:.3f}",
            ))

        # -- Residue table ----------------------------------------------------
        for s in self.residue_scores:
            self.residue_tree.insert("", tk.END, values=(
                s.position,
                s.amino_acid,
                f"{s.hydrophilicity:.3f}",
                f"{s.hydrophobicity:.3f}",
                f"{s.flexibility:.3f}",
                f"{s.accessibility:.3f}",
                f"{s.antigenicity:.3f}",
                f"{s.structural_sasa:.3f}",
                f"{s.global_score:.4f}",
                "Yes" if s.is_exposed else "No",
            ))

        # -- Bio-module table -------------------------------------------------
        for h in self.bio_hits:
            self.bio_tree.insert("", tk.END, values=(
                h.rank,
                h.start,
                h.end,
                h.length,
                h.sequence,
                f"{h.combined_score:.4f}",
                f"{h.hydrophilicity:.3f}",
                f"{h.accessibility:.3f}",
                f"{h.flexibility:.3f}",
                f"{h.beta_turn:.3f}",
                f"{h.antigenicity:.3f}",
                f"{h.bepipred:.3f}",
                f"{h.welling:.3f}",
                f"{h.consensus_score:.2f}",
            ))

        # -- Generate summary -------------------------------------------------
        self._generate_summary()

        # -- Generate text profile --------------------------------------------
        self._generate_profile_text()

        # -- Generate matplotlib chart ----------------------------------------
        if HAS_MPL:
            self._generate_chart()

        # -- Enable exports ---------------------------------------------------
        self.export_csv_btn.configure(state=tk.NORMAL)
        self.export_json_btn.configure(state=tk.NORMAL)
        if self.bio_hits:
            self.export_bio_csv_btn.configure(state=tk.NORMAL)
            self.export_bio_json_btn.configure(state=tk.NORMAL)

        # Switch to summary tab
        self.notebook.select(0)

        # Status
        elapsed = ""
        if self.analysis_start_time:
            dt = datetime.now().timestamp() - self.analysis_start_time
            elapsed = f" in {dt:.1f}s"

        n_core = len(self.epitopes)
        n_bio = len(self.bio_hits)
        bio_msg = f" | Bio: {n_bio}" if n_bio else ""
        self.status_var.set(
            f"Analysis complete{elapsed} -- "
            f"Core: {n_core} epitope(s){bio_msg} "
            f"({len(self.sequence)} residues)"
        )

        self._analysis_done()

    def _analysis_done(self):
        """Clean up after analysis."""
        self.is_analyzing = False
        self.analyze_btn.configure(state=tk.NORMAL)
        self.progress.stop()
        self.progress.pack_forget()
        self.progress_label.pack_forget()

    # =================================================================
    # SUMMARY DASHBOARD
    # =================================================================
    def _generate_summary(self):
        """Generate a formatted summary dashboard."""
        w = self.summary_text
        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)

        def _insert(text, tag="normal"):
            w.insert(tk.END, text, tag)

        # Header
        _insert("Analysis Report\n", "title")
        _insert("=" * 70 + "\n\n", "separator")

        # Sequence info
        _insert("SEQUENCE INFORMATION\n", "heading")
        _insert(f"  Header:    {self.sequence_header}\n", "normal")
        _insert(f"  Length:    {len(self.sequence)} residues\n", "normal")
        _insert(
            f"  PDB:       {'Loaded' if self.has_pdb else 'Not provided'}\n",
            "normal",
        )
        _insert(
            f"  Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "normal",
        )
        _insert("\n", "normal")

        # Core module results
        _insert("CORE MODULE RESULTS\n", "heading")
        _insert(
            "  Methods: Hopp-Woods, Kyte-Doolittle, Karplus-Schulz, "
            "Emini, Kolaskar-Tongaonkar\n",
            "mono",
        )
        _insert(f"  Epitopes found: ", "normal")
        n_core = len(self.epitopes)
        tag = "score_high" if n_core > 0 else "score_low"
        _insert(f"{n_core}\n", tag)

        if self.epitopes:
            _insert("\n  Top candidates:\n", "subheading")
            _insert(
                f"  {'Rank':<5} {'Pos':>10} {'Len':>5} "
                f"{'Score':>7} {'Sequence'}\n",
                "mono",
            )
            _insert("  " + "-" * 60 + "\n", "separator")
            for ep in self.epitopes[:10]:
                score_tag = self._score_tag(ep.global_score)
                _insert(f"  {ep.rank:<5} ", "mono")
                _insert(f"{ep.start:>4}-{ep.end:<4}  ", "mono")
                _insert(f"{ep.length:>3}   ", "mono")
                _insert(f"{ep.global_score:.4f}", score_tag)
                _insert(f"  {ep.sequence}\n", "mono")

        if self.epitopes:
            scores = [ep.global_score for ep in self.epitopes]
            _insert(
                f"\n  Score range: {min(scores):.4f} - {max(scores):.4f}  "
                f"(Mean: {np.mean(scores):.4f})\n",
                "normal",
            )

        _insert("\n", "normal")

        # Bio module results
        if self.bio_hits:
            _insert("BIO MODULE RESULTS\n", "heading")
            _insert(
                "  Methods: Parker, Emini, K-S, Chou-Fasman, K-T, "
                "BepiPred-1.0, Levitt, Welling\n",
                "mono",
            )
            _insert(f"  Epitopes found: ", "normal")
            n_bio = len(self.bio_hits)
            tag = "score_high" if n_bio > 0 else "score_low"
            _insert(f"{n_bio}\n", tag)

            _insert("\n  Top candidates:\n", "subheading")
            _insert(
                f"  {'Rank':<5} {'Pos':>10} {'Len':>5} "
                f"{'Score':>7} {'Cons':>6} {'Sequence'}\n",
                "mono",
            )
            _insert("  " + "-" * 65 + "\n", "separator")
            for h in self.bio_hits[:10]:
                score_tag = self._score_tag(h.combined_score)
                _insert(f"  {h.rank:<5} ", "mono")
                _insert(f"{h.start:>4}-{h.end:<4}  ", "mono")
                _insert(f"{h.length:>3}   ", "mono")
                _insert(f"{h.combined_score:.4f}", score_tag)
                _insert(f"  {h.consensus_score:.2f}", "mono")
                _insert(f"  {h.sequence}\n", "mono")

            bio_scores = [h.combined_score for h in self.bio_hits]
            _insert(
                f"\n  Score range: {min(bio_scores):.4f} - "
                f"{max(bio_scores):.4f}  "
                f"(Mean: {np.mean(bio_scores):.4f})\n",
                "normal",
            )

            cons_scores = [h.consensus_score for h in self.bio_hits]
            _insert(
                f"  Consensus range: {min(cons_scores):.2f} - "
                f"{max(cons_scores):.2f}\n",
                "normal",
            )
            _insert("\n", "normal")

        # Residue score statistics
        if self.residue_scores:
            _insert("RESIDUE SCORE STATISTICS\n", "heading")
            gs = [s.global_score for s in self.residue_scores]
            _insert(
                f"  Mean global score:   {np.mean(gs):.4f}\n"
                f"  Median:              {np.median(gs):.4f}\n"
                f"  Std deviation:       {np.std(gs):.4f}\n"
                f"  Min / Max:           {min(gs):.4f} / {max(gs):.4f}\n",
                "normal",
            )

            n_exposed = sum(1 for s in self.residue_scores if s.is_exposed)
            pct = 100 * n_exposed / len(self.residue_scores)
            _insert(
                f"  Exposed residues:    {n_exposed}/{len(self.residue_scores)}"
                f" ({pct:.1f}%)\n",
                "normal",
            )
            _insert("\n", "normal")

        # Amino acid composition
        if self.sequence:
            _insert("AMINO ACID COMPOSITION\n", "heading")
            from collections import Counter
            counts = Counter(self.sequence)
            total = len(self.sequence)
            hydrophilic = set("EDKRQNS")
            hydrophobic = set("LIVFW")
            n_phil = sum(counts.get(aa, 0) for aa in hydrophilic)
            n_phob = sum(counts.get(aa, 0) for aa in hydrophobic)
            _insert(
                f"  Hydrophilic (EDKRQNS): {n_phil}/{total} "
                f"({100*n_phil/total:.1f}%)\n",
                "normal",
            )
            _insert(
                f"  Hydrophobic (LIVFW):   {n_phob}/{total} "
                f"({100*n_phob/total:.1f}%)\n",
                "normal",
            )
            charged = sum(counts.get(aa, 0) for aa in "DEKRH")
            _insert(
                f"  Charged (DEKRH):       "
                f"{charged}/{total} "
                f"({100*charged/total:.1f}%)\n",
                "normal",
            )
            _insert("\n", "normal")

        _insert("=" * 70 + "\n", "separator")
        _insert(
            f"  EpiTop1 v{__version__} -- Analysis complete\n", "mono",
        )

        w.configure(state=tk.DISABLED)

    def _score_tag(self, score: float) -> str:
        """Return a colour tag based on score value."""
        if score >= 0.6:
            return "score_high"
        elif score >= 0.4:
            return "score_mid"
        else:
            return "score_low"

    # =================================================================
    # MATPLOTLIB CHART
    # =================================================================
    def _generate_chart(self):
        """Generate an embedded matplotlib score profile chart."""
        if not HAS_MPL or not self.residue_scores:
            return

        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        n = len(self.residue_scores)
        positions = np.arange(1, n + 1)
        global_scores = np.array(
            [s.global_score for s in self.residue_scores],
        )

        has_bio = bool(self.bio_residue_results)
        n_panels = 3 if has_bio else 2
        height_ratios = [2, 1, 1.5] if has_bio else [2, 1]

        fig = Figure(
            figsize=(12, 2.5 * n_panels), dpi=96, facecolor="white",
        )
        axes = fig.subplots(
            n_panels, 1, sharex=True,
            gridspec_kw={"height_ratios": height_ratios},
        )
        if n_panels == 1:
            axes = [axes]

        # -- Panel 1: Core global score + epitope regions ---------------------
        ax = axes[0]
        ax.plot(
            positions, global_scores,
            color=_CHART_COLOURS["combined"], linewidth=1.2,
            label="Global Score (Core)",
        )
        ax.fill_between(
            positions, 0, global_scores,
            color=_CHART_COLOURS["combined"], alpha=0.10,
        )

        for ep in self.epitopes:
            ax.axvspan(
                ep.start - 0.5, ep.end + 0.5,
                color=_CHART_COLOURS["epitope_fill"], alpha=0.15,
            )
            mid = (ep.start + ep.end) / 2
            ymax = global_scores[ep.start - 1:ep.end].max()
            ax.text(
                mid, ymax + 0.03, f"#{ep.rank}",
                ha="center", va="bottom", fontsize=7, fontweight="bold",
                color=_CHART_COLOURS["epitope_fill"],
            )

        ax.set_ylabel("Core Score", fontsize=9, fontweight="bold")
        ax.set_ylim(-0.02, 1.08)
        ax.set_title(
            f"EpiTop1 Score Profile -- {self.sequence_header}",
            fontsize=11, fontweight="bold", pad=8,
        )
        ax.legend(loc="upper right", fontsize=7)
        ax.grid(axis="y", alpha=0.2, linewidth=0.5)

        # -- Panel 2: Individual core profiles --------------------------------
        ax2 = axes[1]
        hydro = np.array([s.hydrophilicity for s in self.residue_scores])
        flex = np.array([s.flexibility for s in self.residue_scores])
        access = np.array([s.accessibility for s in self.residue_scores])
        antig = np.array([s.antigenicity for s in self.residue_scores])

        lw = 0.8
        ax2.plot(
            positions, self._norm(hydro),
            color=_CHART_COLOURS["hydrophilicity"], lw=lw,
            label="Hydrophilicity",
        )
        ax2.plot(
            positions, self._norm(access),
            color=_CHART_COLOURS["accessibility"], lw=lw,
            label="Accessibility",
        )
        ax2.plot(
            positions, self._norm(flex),
            color=_CHART_COLOURS["flexibility"], lw=lw,
            label="Flexibility",
        )
        ax2.plot(
            positions, self._norm(antig),
            color=_CHART_COLOURS["antigenicity"], lw=lw,
            label="Antigenicity",
        )
        ax2.set_ylabel("Normalised", fontsize=8)
        ax2.legend(loc="upper right", fontsize=6, ncol=4)
        ax2.set_ylim(-0.05, 1.10)
        ax2.grid(axis="y", alpha=0.2, linewidth=0.5)

        # -- Panel 3: Bio module combined score (if available) ----------------
        if has_bio:
            ax3 = axes[2]
            bio_scores = np.array(
                [r.combined_score for r in self.bio_residue_results],
            )
            ax3.plot(
                positions, bio_scores,
                color="#E83E8C", linewidth=1.2,
                label="Bio Combined Score",
            )
            ax3.fill_between(
                positions, 0, bio_scores,
                color="#E83E8C", alpha=0.08,
            )

            for h in self.bio_hits:
                ax3.axvspan(
                    h.start - 0.5, h.end + 0.5,
                    color="#E83E8C", alpha=0.12,
                )
                mid = (h.start + h.end) / 2
                ymax = bio_scores[h.start - 1:h.end].max()
                ax3.text(
                    mid, ymax + 0.03, f"#{h.rank}",
                    ha="center", va="bottom", fontsize=7, fontweight="bold",
                    color="#E83E8C",
                )

            ax3.set_ylabel("Bio Score", fontsize=9, fontweight="bold")
            ax3.set_ylim(-0.02, 1.08)
            ax3.legend(loc="upper right", fontsize=7)
            ax3.grid(axis="y", alpha=0.2, linewidth=0.5)

        axes[-1].set_xlabel(
            "Residue Position", fontsize=9, fontweight="bold",
        )
        axes[-1].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        fig.tight_layout()

        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.chart_canvas = canvas

    @staticmethod
    def _norm(arr: np.ndarray) -> np.ndarray:
        """Min-max normalisation for visual display."""
        mn, mx = np.min(arr), np.max(arr)
        if mx - mn < 1e-10:
            return np.full_like(arr, 0.5)
        return (arr - mn) / (mx - mn)

    # =================================================================
    # TEXT PROFILE
    # =================================================================
    def _generate_profile_text(self):
        """Generate a text-based score profile visualization."""
        self.profile_text.configure(state=tk.NORMAL)
        self.profile_text.delete("1.0", tk.END)

        if not self.residue_scores:
            self.profile_text.configure(state=tk.DISABLED)
            return

        width = 50
        lines = []
        lines.append("=" * 85)
        lines.append(
            f"  EpiTop1 Score Profile -- {self.sequence_header}",
        )
        lines.append(f"  Sequence length: {len(self.sequence)} residues")
        lines.append(f"  Core epitopes: {len(self.epitopes)}")
        if self.bio_hits:
            lines.append(f"  Bio epitopes:  {len(self.bio_hits)}")
        lines.append("=" * 85)
        lines.append("")

        # Core epitope summary
        if self.epitopes:
            lines.append("  CORE EPITOPE CANDIDATES")
            lines.append("  " + "-" * 75)
            lines.append(
                f"  {'Rank':<5} {'Start':<6} {'End':<5} {'Len':<5} "
                f"{'Score':<8} {'Sequence'}",
            )
            lines.append("  " + "-" * 75)
            for ep in self.epitopes[:15]:
                lines.append(
                    f"  {ep.rank:<5} {ep.start:<6} {ep.end:<5} "
                    f"{ep.length:<5} {ep.global_score:<8.4f} {ep.sequence}",
                )
            lines.append("")

        # Bio epitope summary
        if self.bio_hits:
            lines.append("  BIO MODULE EPITOPE CANDIDATES")
            lines.append("  " + "-" * 80)
            lines.append(
                f"  {'Rank':<5} {'Start':<6} {'End':<5} {'Len':<5} "
                f"{'Score':<8} {'Cons':<6} {'Sequence'}",
            )
            lines.append("  " + "-" * 80)
            for h in self.bio_hits[:15]:
                lines.append(
                    f"  {h.rank:<5} {h.start:<6} {h.end:<5} "
                    f"{h.length:<5} {h.combined_score:<8.4f} "
                    f"{h.consensus_score:<6.2f} {h.sequence}",
                )
            lines.append("")

        # Per-residue bar chart
        lines.append("  GLOBAL SCORE PROFILE (Core)")
        lines.append("  " + "-" * 75)

        epitope_positions = set()
        for ep in self.epitopes:
            for p in range(ep.start, ep.end + 1):
                epitope_positions.add(p)

        bio_positions = set()
        for h in self.bio_hits:
            for p in range(h.start, h.end + 1):
                bio_positions.add(p)

        for s in self.residue_scores:
            bar_len = int(s.global_score * width)
            bar = "#" * bar_len + "." * (width - bar_len)
            markers = ""
            if s.position in epitope_positions:
                markers += " C"
            if s.position in bio_positions:
                markers += " B"
            lines.append(
                f"  {s.position:>4} {s.amino_acid} |{bar}| "
                f"{s.global_score:.3f}{markers}",
            )

        lines.append("")
        lines.append("  C = Core epitope region  |  B = Bio epitope region")
        lines.append("")

        # Individual scores table
        lines.append("  INDIVIDUAL SCORES (normalised)")
        lines.append("  " + "-" * 75)
        lines.append(
            f"  {'Pos':>4} {'AA'} {'Hydrophil':>10} {'Hydrophob':>10} "
            f"{'Flex':>8} {'Access':>8} {'Antig':>8} {'Global':>8}",
        )
        lines.append("  " + "-" * 75)
        for s in self.residue_scores:
            lines.append(
                f"  {s.position:>4} {s.amino_acid}  "
                f"{s.hydrophilicity:>9.4f} {s.hydrophobicity:>9.4f} "
                f"{s.flexibility:>7.4f} {s.accessibility:>7.4f} "
                f"{s.antigenicity:>7.4f} {s.global_score:>7.4f}",
            )

        self.profile_text.insert("1.0", "\n".join(lines))
        self.profile_text.configure(state=tk.DISABLED)

    # =================================================================
    # CLEAR RESULTS
    # =================================================================
    def _clear_results(self):
        """Clear all analysis results."""
        self.epitope_tree.delete(*self.epitope_tree.get_children())
        self.residue_tree.delete(*self.residue_tree.get_children())
        self.bio_tree.delete(*self.bio_tree.get_children())

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.configure(state=tk.DISABLED)

        self.profile_text.configure(state=tk.NORMAL)
        self.profile_text.delete("1.0", tk.END)
        self.profile_text.configure(state=tk.DISABLED)

        if self.chart_canvas:
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.chart_canvas = None

        self.epitopes = []
        self.residue_scores = []
        self.bio_hits = []
        self.bio_residue_results = []

        self.export_csv_btn.configure(state=tk.DISABLED)
        self.export_json_btn.configure(state=tk.DISABLED)
        self.export_bio_csv_btn.configure(state=tk.DISABLED)
        self.export_bio_json_btn.configure(state=tk.DISABLED)

        self.status_var.set("Results cleared")
        self.seq_length_var.set("")

    # =================================================================
    # EXPORT
    # =================================================================
    def _export_csv(self):
        """Export core results to CSV files."""
        if not self.epitopes and not self.residue_scores:
            messagebox.showinfo("No Data", "Run analysis first.")
            return

        dirpath = filedialog.askdirectory(title="Select Export Directory")
        if not dirpath:
            return

        try:
            ep_path = os.path.join(dirpath, "epitop1_epitopes.csv")
            export_csv(self.epitopes, ep_path, self.sequence_header)

            res_path = os.path.join(dirpath, "epitop1_residue_scores.csv")
            export_residue_table(
                self.residue_scores, res_path, self.sequence_header,
            )

            messagebox.showinfo(
                "Export Complete",
                f"Core module files exported to:\n\n"
                f"  {ep_path}\n  {res_path}",
            )
            self.status_var.set(f"Core CSV exported to {dirpath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_json(self):
        """Export core results to JSON."""
        if not self.epitopes and not self.residue_scores:
            messagebox.showinfo("No Data", "Run analysis first.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save JSON Report",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="epitop1_report.json",
        )
        if not filepath:
            return

        try:
            export_json(
                self.epitopes, self.residue_scores, filepath,
                self.sequence_header, self.sequence, self.has_pdb,
            )
            messagebox.showinfo(
                "Export Complete",
                f"JSON report exported to:\n{filepath}",
            )
            self.status_var.set(f"JSON exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_bio_csv(self):
        """Export bio module results to CSV."""
        if not self.bio_hits:
            messagebox.showinfo("No Data", "No bio module results to export.")
            return

        dirpath = filedialog.askdirectory(title="Select Export Directory")
        if not dirpath:
            return

        try:
            import csv
            from config import EXPORT_SETTINGS
            prec = EXPORT_SETTINGS["float_precision"]

            # Epitopes CSV
            ep_path = os.path.join(dirpath, "bio_epitopes.csv")
            with open(ep_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    f"# Bio Module Epitopes -- {self.sequence_header}",
                ])
                w.writerow([
                    f"# Generated: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ])
                w.writerow([])
                w.writerow([
                    "Rank", "Start", "End", "Length", "Sequence",
                    "CombinedScore", "Hydrophilicity", "Accessibility",
                    "Flexibility", "BetaTurn", "Antigenicity",
                    "BepiPred", "Coil", "Welling", "Consensus", "StructuralSASA",
                ])
                for h in self.bio_hits:
                    w.writerow([
                        h.rank, h.start, h.end, h.length, h.sequence,
                        round(h.combined_score, prec),
                        round(h.hydrophilicity, prec),
                        round(h.accessibility, prec),
                        round(h.flexibility, prec),
                        round(h.beta_turn, prec),
                        round(h.antigenicity, prec),
                        round(h.bepipred, prec),
                        round(h.coil, prec),
                        round(h.welling, prec),
                        round(h.consensus_score, prec),
                        round(h.structural_sasa, prec),
                    ])

            # Residue CSV
            res_path = os.path.join(dirpath, "bio_residue_scores.csv")
            with open(res_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    f"# Bio Module Residue Scores -- {self.sequence_header}",
                ])
                w.writerow([])
                w.writerow([
                    "Position", "AA", "Hydrophilicity", "Accessibility",
                    "Flexibility", "BetaTurn", "Antigenicity",
                    "BepiPred", "Coil", "Welling", "Consensus",
                    "StructuralSASA", "CombinedScore", "IsExposed",
                ])
                for r in self.bio_residue_results:
                    w.writerow([
                        r.position, r.amino_acid,
                        round(r.hydrophilicity, prec),
                        round(r.accessibility, prec),
                        round(r.flexibility, prec),
                        round(r.beta_turn, prec),
                        round(r.antigenicity, prec),
                        round(r.bepipred, prec),
                        round(r.coil, prec),
                        round(r.welling, prec),
                        r.consensus_count,
                        round(r.structural_sasa, prec),
                        round(r.combined_score, prec),
                        "Yes" if r.is_exposed else "No",
                    ])

            messagebox.showinfo(
                "Export Complete",
                f"Bio module files exported to:\n\n"
                f"  {ep_path}\n  {res_path}",
            )
            self.status_var.set(f"Bio CSV exported to {dirpath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_bio_json(self):
        """Export bio module results to JSON."""
        if not self.bio_hits:
            messagebox.showinfo("No Data", "No bio module results to export.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Bio JSON Report",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="bio_report.json",
        )
        if not filepath:
            return

        try:
            import json
            from config import (
                EXPORT_SETTINGS, BIO_SCORING_WEIGHTS, BIO_WINDOW_SIZES,
            )
            prec = EXPORT_SETTINGS["float_precision"]

            report = {
                "metadata": {
                    "software": f"EpiTop1 v{__version__} -- Bio Module",
                    "module": "bio",
                    "date": datetime.now().isoformat(),
                    "sequence_header": self.sequence_header,
                    "sequence_length": len(self.sequence),
                    "pdb_used": self.has_pdb,
                    "weights": BIO_SCORING_WEIGHTS,
                    "window_sizes": BIO_WINDOW_SIZES,
                },
                "sequence": self.sequence,
                "epitope_candidates": [
                    {
                        "rank": h.rank,
                        "start_position": h.start,
                        "end_position": h.end,
                        "length": h.length,
                        "peptide_sequence": h.sequence,
                        "combined_score": round(h.combined_score, prec),
                        "hydrophilicity": round(h.hydrophilicity, prec),
                        "accessibility": round(h.accessibility, prec),
                        "flexibility": round(h.flexibility, prec),
                        "beta_turn": round(h.beta_turn, prec),
                        "antigenicity": round(h.antigenicity, prec),
                        "bepipred": round(h.bepipred, prec),
                        "coil": round(h.coil, prec),
                        "welling": round(h.welling, prec),
                        "consensus_score": round(h.consensus_score, prec),
                        "structural_sasa": round(h.structural_sasa, prec),
                    }
                    for h in self.bio_hits
                ],
                "residue_scores": [
                    {
                        "position": r.position,
                        "amino_acid": r.amino_acid,
                        "hydrophilicity": round(r.hydrophilicity, prec),
                        "accessibility": round(r.accessibility, prec),
                        "flexibility": round(r.flexibility, prec),
                        "beta_turn": round(r.beta_turn, prec),
                        "antigenicity": round(r.antigenicity, prec),
                        "bepipred": round(r.bepipred, prec),
                        "coil": round(r.coil, prec),
                        "welling": round(r.welling, prec),
                        "consensus_count": r.consensus_count,
                        "structural_sasa": round(r.structural_sasa, prec),
                        "combined_score": round(r.combined_score, prec),
                        "is_exposed": r.is_exposed,
                    }
                    for r in self.bio_residue_results
                ],
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Export Complete",
                f"Bio JSON report exported to:\n{filepath}",
            )
            self.status_var.set(f"Bio JSON exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # =================================================================
    # DIALOGS
    # =================================================================
    def _show_about(self):
        """Show the About dialog."""
        messagebox.showinfo(
            "About EpiTop1",
            _ABOUT_TEXT.format(version=__version__),
        )

    def _show_references(self):
        """Show method references dialog."""
        refs = (
            "EpiTop1 Method References\n"
            "=" * 50 + "\n\n"
            "Core Module:\n"
            "  Hopp TP, Woods KR (1981) PNAS 78:3824-3828\n"
            "  Kyte J, Doolittle RF (1982) J Mol Biol 157:105-132\n"
            "  Karplus PA, Schulz GE (1985) Naturwiss 72:212-213\n"
            "  Emini EA et al. (1985) J Virol 55:836-839\n"
            "  Kolaskar AS, Tongaonkar PC (1990) FEBS Lett 276:172-174\n\n"
            "Bio Module:\n"
            "  Parker JMR et al. (1986) Biochemistry 25:5425-5432\n"
            "  Chou PY, Fasman GD (1978) Adv Enzymol 47:45-148\n"
            "  Larsen JEP et al. (2006) Immunome Res 2:2\n"
            "  Levitt M (1978) Biochemistry 17:4277-4285\n"
            "  Welling GW et al. (1985) FEBS Lett 188:215-218\n\n"
            "General:\n"
            "  Pellequer JL, Westhof E (1993) Methods Enzymol 237:1-11\n"
            "  Saha S, Raghava GPS (2006) Proteins 65:40-48\n"
            "  Jespersen MC et al. (2017) Nucleic Acids Res 45:W265-W270\n"
            "  Shrake A, Rupley JA (1973) J Mol Biol 79:351-371\n"
        )
        win = tk.Toplevel(self.root)
        win.title("Method References")
        win.geometry("550x450")
        win.resizable(False, False)

        text = scrolledtext.ScrolledText(
            win, font=("Consolas", 9), wrap=tk.WORD,
            bg="white", padx=12, pady=8,
        )
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", refs)
        text.configure(state=tk.DISABLED)

    # =================================================================
    # RUN
    # =================================================================
    def run(self):
        """Start the application main loop."""
        self.root.mainloop()
