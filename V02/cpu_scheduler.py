"""
=============================================================================
  EC 6110: Operating Systems — Task 01
  CPU Scheduling Algorithm Simulator
  University of Jaffna — Faculty of Engineering — Group Assignment 2026
=============================================================================

  Algorithms Implemented:
    1. First Come First Served (FCFS)
    2. Round Robin (RR)
    3. Shortest Process Next (SPN / non-preemptive SJF)
    4. Shortest Remaining Time Next (SRTN / preemptive SJF)
    5. Priority Scheduling (Non-Preemptive and Preemptive)

  Features:
    * Interactive process input table with validation
    * Gantt chart with timeline for each algorithm
    * Per-process metrics: Waiting, Turnaround, Response time
    * Full comparison: bar charts + all 5 mini Gantt charts
    * Automatic best-algorithm recommendation
    * Navigation toolbar (zoom / pan) on every chart
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")                        # must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.gridspec as gridspec
import copy

# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────

PROCESS_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC",
]

BG_DARK   = "#12121f"
BG_PANEL  = "#1c1c30"
BG_CARD   = "#25254a"
ACCENT    = "#e94560"
ACCENT2   = "#533483"
TEXT_W    = "#eaeaea"
TEXT_M    = "#8888aa"
SUCCESS   = "#4ade80"


# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULING ALGORITHMS
# ─────────────────────────────────────────────────────────────────────────────

def fcfs(processes):
    """
    First Come First Served (FCFS)
    ───────────────────────────────
    Execute processes strictly in arrival order.
    Non-preemptive: a running process always runs to completion.
    If no process has arrived yet, the CPU idles until the next arrival.

    Returns (done_list, timeline).
    """
    procs    = sorted(copy.deepcopy(processes), key=lambda p: (p["arrival"], p["pid"]))
    timeline = []
    time     = 0

    for p in procs:
        if time < p["arrival"]:
            time = p["arrival"]          # CPU idle gap

        start = time
        time += p["burst"]
        timeline.append({"pid": p["pid"], "start": start, "end": time})

        p["start"]      = start
        p["finish"]     = time
        p["waiting"]    = start - p["arrival"]    # time spent waiting
        p["turnaround"] = time  - p["arrival"]    # finish - arrival
        p["response"]   = p["waiting"]            # first response = waiting (non-preemptive)

    return procs, timeline


def round_robin(processes, quantum):
    """
    Round Robin (RR)
    ─────────────────
    Processes share the CPU in time slices of length 'quantum'.
    If a process does not finish in its slice, it is appended to
    the back of the ready queue and runs again later.

    Args:
        quantum  positive integer time-slice size

    Key rule: newly arriving processes are added to the queue BEFORE
    the current process is re-queued (so they don't jump ahead).
    """
    procs = copy.deepcopy(processes)
    for p in procs:
        p["remaining"] = p["burst"]
        p["response"]  = None            # will be set on first execution

    procs.sort(key=lambda p: (p["arrival"], p["pid"]))
    timeline  = []
    done      = []
    time      = 0
    queue     = []                       # FIFO ready queue
    not_yet   = list(procs)             # processes not yet in queue

    # Seed queue with time-0 arrivals
    for p in list(not_yet):
        if p["arrival"] <= time:
            queue.append(p)
            not_yet.remove(p)

    while queue or not_yet:
        if not queue:
            # CPU idle — jump to next arrival
            time = not_yet[0]["arrival"]
            for p in list(not_yet):
                if p["arrival"] <= time:
                    queue.append(p)
                    not_yet.remove(p)
            continue

        p = queue.pop(0)

        if p["response"] is None:
            p["response"] = time - p["arrival"]   # first time on CPU

        run   = min(quantum, p["remaining"])
        start = time
        time += run
        timeline.append({"pid": p["pid"], "start": start, "end": time})
        p["remaining"] -= run

        # Admit arrivals that occurred during this slice (before re-queuing p)
        newly = [pr for pr in not_yet if pr["arrival"] <= time]
        newly.sort(key=lambda pr: (pr["arrival"], pr["pid"]))
        for pr in newly:
            not_yet.remove(pr)
            queue.append(pr)

        if p["remaining"] > 0:
            queue.append(p)              # still has work — goes to back
        else:
            p["finish"]     = time
            p["turnaround"] = time - p["arrival"]
            p["waiting"]    = p["turnaround"] - p["burst"]
            p["start"]      = p["finish"] - p["burst"]   # approx for table
            done.append(p)

    return done, timeline


def spn(processes):
    """
    Shortest Process Next (SPN) = Shortest Job First (SJF)
    ────────────────────────────────────────────────────────
    Non-preemptive: at every dispatch point choose the ready process
    with the smallest burst time.  Ties are broken by earliest arrival.
    """
    remaining = sorted(copy.deepcopy(processes), key=lambda p: (p["arrival"], p["pid"]))
    done, timeline = [], []
    time = 0

    while remaining:
        available = [p for p in remaining if p["arrival"] <= time]
        if not available:
            time = min(p["arrival"] for p in remaining)
            continue

        p = min(available, key=lambda x: (x["burst"], x["arrival"]))
        remaining.remove(p)

        start = time
        time += p["burst"]
        timeline.append({"pid": p["pid"], "start": start, "end": time})

        p["start"]      = start
        p["finish"]     = time
        p["waiting"]    = start - p["arrival"]
        p["turnaround"] = time  - p["arrival"]
        p["response"]   = p["waiting"]
        done.append(p)

    return done, timeline


def srtn(processes):
    """
    Shortest Remaining Time Next (SRTN) = Preemptive SJF
    ──────────────────────────────────────────────────────
    At every unit of time the ready process with the least remaining
    burst is run.  A new arrival with a shorter remaining time will
    immediately preempt the current process.

    Implementation: unit-by-unit simulation, then consecutive same-PID
    segments are merged for a cleaner Gantt chart.
    """
    procs = copy.deepcopy(processes)
    for p in procs:
        p["remaining"] = p["burst"]
        p["response"]  = None

    raw_tl = []
    done   = []
    time   = 0

    while len(done) < len(procs):
        available = [p for p in procs
                     if p["arrival"] <= time and p["remaining"] > 0]
        if not available:
            time += 1
            continue

        current = min(available, key=lambda x: (x["remaining"], x["arrival"]))

        if current["response"] is None:
            current["response"] = time - current["arrival"]

        raw_tl.append({"pid": current["pid"], "start": time, "end": time + 1})
        current["remaining"] -= 1
        time += 1

        if current["remaining"] == 0:
            current["finish"]     = time
            current["turnaround"] = time - current["arrival"]
            current["waiting"]    = current["turnaround"] - current["burst"]
            current["start"]      = current["finish"] - current["burst"]
            done.append(current)

    # Merge adjacent same-PID segments
    timeline = []
    for seg in raw_tl:
        if (timeline
                and timeline[-1]["pid"] == seg["pid"]
                and timeline[-1]["end"] == seg["start"]):
            timeline[-1]["end"] = seg["end"]
        else:
            timeline.append(dict(seg))

    return done, timeline


def priority_scheduling(processes, preemptive=False):
    """
    Priority Scheduling
    ────────────────────
    Lower priority number = higher urgency (priority 1 beats priority 4).

    Non-Preemptive: once a process starts it runs until completion.
    Preemptive    : a newly arrived higher-priority process immediately
                    takes the CPU from the current one.

    Args:
        preemptive  set True for preemptive mode
    """
    procs = copy.deepcopy(processes)
    for p in procs:
        p["remaining"] = p["burst"]
        p["response"]  = None

    # ── Non-preemptive ────────────────────────────────────────────────
    if not preemptive:
        remaining = sorted(procs, key=lambda p: (p["arrival"], p["pid"]))
        done, timeline = [], []
        time = 0

        while remaining:
            available = [p for p in remaining if p["arrival"] <= time]
            if not available:
                time = min(p["arrival"] for p in remaining)
                continue

            p = min(available, key=lambda x: (x["priority"], x["arrival"]))
            remaining.remove(p)
            start = time
            time += p["burst"]
            timeline.append({"pid": p["pid"], "start": start, "end": time})

            p["start"]      = start
            p["finish"]     = time
            p["waiting"]    = start - p["arrival"]
            p["turnaround"] = time  - p["arrival"]
            p["response"]   = p["waiting"]
            done.append(p)

        return done, timeline

    # ── Preemptive (unit-by-unit, then merge) ─────────────────────────
    raw_tl = []
    done   = []
    time   = 0

    while len(done) < len(procs):
        available = [p for p in procs
                     if p["arrival"] <= time and p["remaining"] > 0]
        if not available:
            time += 1
            continue

        current = min(available, key=lambda x: (x["priority"], x["arrival"]))

        if current["response"] is None:
            current["response"] = time - current["arrival"]

        raw_tl.append({"pid": current["pid"], "start": time, "end": time + 1})
        current["remaining"] -= 1
        time += 1

        if current["remaining"] == 0:
            current["finish"]     = time
            current["turnaround"] = time - current["arrival"]
            current["waiting"]    = current["turnaround"] - current["burst"]
            current["start"]      = current["finish"] - current["burst"]
            done.append(current)

    # Merge adjacent same-PID segments
    timeline = []
    for seg in raw_tl:
        if (timeline
                and timeline[-1]["pid"] == seg["pid"]
                and timeline[-1]["end"] == seg["start"]):
            timeline[-1]["end"] = seg["end"]
        else:
            timeline.append(dict(seg))

    return done, timeline


def calc_metrics(done):
    """
    Compute average scheduling metrics for a completed process list.

    Returns:
        avg_waiting    average time a process waits in the ready queue
        avg_turnaround average time from arrival to completion
        avg_response   average time from arrival to first CPU access
    """
    n = len(done)
    if n == 0:
        return 0.0, 0.0, 0.0
    awt  = sum(p["waiting"]    for p in done) / n
    atat = sum(p["turnaround"] for p in done) / n
    art  = sum(p["response"]   for p in done) / n
    return awt, atat, art


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN GUI APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class SchedulerApp(tk.Tk):
    """
    Top-level application window.

    Layout:
        Header bar
        ┌──────────────────┬───────────────────────────────────────┐
        │  LEFT PANEL      │  RIGHT NOTEBOOK                       │
        │  • Process input │  Tab 1 — Gantt Chart                  │
        │  • Queue table   │  Tab 2 — Metrics Table                │
        │  • Algo settings │  Tab 3 — Compare All Algorithms       │
        │  • Run buttons   │                                       │
        └──────────────────┴───────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.title(
            "CPU Scheduling Simulator  |  EC 6110  |  University of Jaffna")
        self.geometry("1450x920")
        self.minsize(1100, 760)
        self.configure(bg=BG_DARK)

        # ── App state ─────────────────────────────────────────────────
        self.processes   = []
        self.pid_counter = 1
        self.quantum_var = tk.IntVar(value=2)
        self.prio_mode   = tk.StringVar(value="Non-Preemptive")
        self.algo_var    = tk.StringVar(value="FCFS")

        self._quantum_widget = None   # reference kept for enable/disable
        self._prio_widget    = None

        self._build_styles()
        self._build_ui()
        self._load_sample_data()

    # ─────────────────────────────────────────────────────────────────
    #  TTK STYLES
    # ─────────────────────────────────────────────────────────────────

    def _build_styles(self):
        """Apply dark-theme styles to all ttk widgets."""
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure("TNotebook",      background=BG_DARK,  tabmargins=[2, 6, 2, 0])
        s.configure("TNotebook.Tab",  background=BG_PANEL, foreground=TEXT_M,
                    font=("Segoe UI", 10, "bold"), padding=(18, 9))
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT2)],
              foreground=[("selected", TEXT_W)])

        s.configure("Treeview",
                    background=BG_CARD, foreground=TEXT_W,
                    fieldbackground=BG_CARD,
                    font=("Segoe UI", 9), rowheight=28)
        s.configure("Treeview.Heading",
                    background=ACCENT2, foreground="white",
                    font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

        s.configure("TCombobox",
                    fieldbackground=BG_CARD, background=BG_PANEL,
                    foreground=TEXT_W, selectbackground=ACCENT,
                    arrowcolor=TEXT_W)
        s.configure("TSpinbox",
                    fieldbackground=BG_CARD, background=BG_PANEL,
                    foreground=TEXT_W, arrowcolor=TEXT_W)

        # Fix combobox dropdown colours (platform-dependent trick)
        self.option_add("*TCombobox*Listbox.background", BG_CARD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT_W)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

    # ─────────────────────────────────────────────────────────────────
    #  TOP-LEVEL LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        pane = tk.PanedWindow(self, orient="horizontal",
                              bg=BG_DARK, sashwidth=6,
                              sashrelief="flat", sashpad=2)
        pane.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        left  = tk.Frame(pane, bg=BG_PANEL, width=375)
        right = tk.Frame(pane, bg=BG_DARK)

        pane.add(left,  minsize=340)
        pane.add(right, minsize=720)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_header(self):
        """Top banner: title on the left, module info on the right."""
        hdr = tk.Frame(self, bg=BG_PANEL, height=66)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        lf = tk.Frame(hdr, bg=BG_PANEL)
        lf.pack(side="left", padx=18, pady=8)
        tk.Label(lf, text="⚙", bg=BG_PANEL, fg=ACCENT,
                 font=("Segoe UI", 22)).pack(side="left", padx=(0, 8))
        tk.Label(lf, text="CPU Scheduling Simulator",
                 bg=BG_PANEL, fg=TEXT_W,
                 font=("Segoe UI", 17, "bold")).pack(side="left")

        rf = tk.Frame(hdr, bg=BG_PANEL)
        rf.pack(side="right", padx=18)
        tk.Label(rf, text="EC 6110: Operating Systems",
                 bg=BG_PANEL, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="e")
        tk.Label(rf, text="University of Jaffna  |  Faculty of Engineering",
                 bg=BG_PANEL, fg=TEXT_M,
                 font=("Segoe UI", 8)).pack(anchor="e")

        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")  # accent divider

    # ─────────────────────────────────────────────────────────────────
    #  LEFT PANEL
    # ─────────────────────────────────────────────────────────────────

    def _build_left_panel(self, parent):
        parent.pack_propagate(False)

        # ── 1. Process Input ─────────────────────────────────────────
        sec1 = self._labeled_box(parent, "➕  Add New Process")
        sec1.pack(fill="x", padx=10, pady=(10, 4))

        form = tk.Frame(sec1, bg=BG_PANEL)
        form.pack(fill="x", padx=10, pady=6)

        fields = [
            ("Arrival Time", "0",  "When the process enters the system  (≥ 0)"),
            ("Burst Time",   "5",  "Total CPU time required               (> 0)"),
            ("Priority",     "1",  "Scheduling priority  (1 = highest)"),
        ]
        self.entries = {}
        for row, (lbl, default, hint) in enumerate(fields):
            tk.Label(form, text=lbl, bg=BG_PANEL, fg=TEXT_M,
                     font=("Segoe UI", 9)).grid(row=row, column=0,
                                                sticky="w", pady=3)
            e = tk.Entry(form,
                         bg=BG_CARD, fg=TEXT_W, insertbackground=TEXT_W,
                         font=("Segoe UI", 10), width=12, relief="flat",
                         highlightthickness=1,
                         highlightcolor=ACCENT,
                         highlightbackground="#2a2a50")
            e.insert(0, default)
            e.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=3)
            tk.Label(form, text=hint, bg=BG_PANEL, fg="#555577",
                     font=("Segoe UI", 7)).grid(row=row, column=2,
                                                sticky="w", padx=(6, 0))
            self.entries[lbl] = e
        form.columnconfigure(1, weight=1)

        br = tk.Frame(sec1, bg=BG_PANEL)
        br.pack(fill="x", padx=10, pady=(2, 10))
        self._btn(br, "＋ Add",       self._add_process,    ACCENT  ).pack(side="left", padx=(0, 4))
        self._btn(br, "✕ Remove",    self._remove_process, "#553355").pack(side="left", padx=(0, 4))
        self._btn(br, "↺ Clear All", self._clear_processes,"#333355").pack(side="left")

        # ── 2. Process Queue ─────────────────────────────────────────
        sec2 = self._labeled_box(parent, "📋  Process Queue")
        sec2.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("PID", "Arrival", "Burst", "Priority")
        self.proc_tree = ttk.Treeview(sec2, columns=cols, show="headings", height=8)
        for c, w in zip(cols, (58, 68, 62, 68)):
            self.proc_tree.heading(c, text=c)
            self.proc_tree.column(c, width=w, anchor="center")
        self.proc_tree.tag_configure("odd",  background="#1e1e38")
        self.proc_tree.tag_configure("even", background=BG_CARD)

        vsb = ttk.Scrollbar(sec2, orient="vertical",
                            command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=vsb.set)
        self.proc_tree.pack(side="left", fill="both", expand=True,
                            padx=(8, 0), pady=6)
        vsb.pack(side="right", fill="y", pady=6, padx=(0, 6))

        # ── 3. Algorithm Settings ─────────────────────────────────────
        sec3 = self._labeled_box(parent, "⚙  Algorithm Settings")
        sec3.pack(fill="x", padx=10, pady=4)

        cfg = tk.Frame(sec3, bg=BG_PANEL)
        cfg.pack(fill="x", padx=10, pady=8)

        algo_names = [
            "FCFS",
            "Round Robin",
            "SPN (SJF)",
            "SRTN (Preemptive SJF)",
            "Priority",
        ]

        # Algorithm selector
        tk.Label(cfg, text="Algorithm:", bg=BG_PANEL, fg=TEXT_M,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        algo_cb = ttk.Combobox(cfg, textvariable=self.algo_var,
                               values=algo_names, state="readonly", width=24)
        algo_cb.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        algo_cb.bind("<<ComboboxSelected>>", self._on_algo_change)

        # Round Robin quantum
        tk.Label(cfg, text="RR Quantum:", bg=BG_PANEL, fg=TEXT_M,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        self._quantum_widget = ttk.Spinbox(cfg, from_=1, to=50,
                                           textvariable=self.quantum_var, width=8)
        self._quantum_widget.grid(row=1, column=1, sticky="w", padx=(8, 0))

        # Priority mode
        tk.Label(cfg, text="Priority Mode:", bg=BG_PANEL, fg=TEXT_M,
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        self._prio_widget = ttk.Combobox(cfg, textvariable=self.prio_mode,
                                         values=["Non-Preemptive", "Preemptive"],
                                         state="readonly", width=24)
        self._prio_widget.grid(row=2, column=1, sticky="ew", padx=(8, 0))
        cfg.columnconfigure(1, weight=1)

        self._on_algo_change()   # set correct initial enable/disable state

        # ── 4. Run Buttons ────────────────────────────────────────────
        run_fr = tk.Frame(parent, bg=BG_PANEL)
        run_fr.pack(fill="x", padx=10, pady=(4, 12))
        self._btn(run_fr, "▶  Run Selected Algorithm",
                  self._run_single, ACCENT, width=28).pack(fill="x", pady=3)
        self._btn(run_fr, "📊  Compare ALL Algorithms",
                  self._run_comparison, ACCENT2, width=28).pack(fill="x", pady=3)

    # ─────────────────────────────────────────────────────────────────
    #  RIGHT PANEL — NOTEBOOK
    # ─────────────────────────────────────────────────────────────────

    def _build_right_panel(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self.tab_gantt   = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_metrics = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_compare = tk.Frame(self.notebook, bg=BG_DARK)

        self.notebook.add(self.tab_gantt,   text="  📊 Gantt Chart  ")
        self.notebook.add(self.tab_metrics, text="  📋 Metrics Table  ")
        self.notebook.add(self.tab_compare, text="  🔍 Compare All  ")

        self._build_gantt_tab()
        self._build_metrics_tab()
        self._build_compare_tab()

    # ── Tab 1: Gantt ─────────────────────────────────────────────────

    def _build_gantt_tab(self):
        # Info bar
        info = tk.Frame(self.tab_gantt, bg=BG_PANEL, height=46)
        info.pack(fill="x")
        info.pack_propagate(False)
        self.gantt_title_lbl = tk.Label(
            info, text="Choose an algorithm and click  ▶ Run",
            bg=BG_PANEL, fg=TEXT_M, font=("Segoe UI", 12, "bold"))
        self.gantt_title_lbl.pack(side="left", padx=16, pady=10)
        self.gantt_metric_lbl = tk.Label(
            info, text="", bg=BG_PANEL, fg=SUCCESS, font=("Segoe UI", 10))
        self.gantt_metric_lbl.pack(side="right", padx=16, pady=10)
        tk.Frame(self.tab_gantt, bg=ACCENT2, height=1).pack(fill="x")

        # Canvas area
        self.gantt_area = tk.Frame(self.tab_gantt, bg=BG_DARK)
        self.gantt_area.pack(fill="both", expand=True)
        self._placeholder(self.gantt_area,
                          "Add processes  →  select algorithm  →  click  ▶ Run")

    # ── Tab 2: Metrics ───────────────────────────────────────────────

    def _build_metrics_tab(self):
        cols = ("PID", "Arrival", "Burst", "Priority",
                "Start", "Finish", "Waiting", "Turnaround", "Response")
        self.met_tree = ttk.Treeview(self.tab_metrics,
                                     columns=cols, show="headings")
        widths = (55, 65, 60, 68, 58, 60, 68, 90, 78)
        for c, w in zip(cols, widths):
            self.met_tree.heading(c, text=c)
            self.met_tree.column(c, width=w, anchor="center")
        self.met_tree.tag_configure("odd",  background="#1e1e38")
        self.met_tree.tag_configure("even", background=BG_CARD)

        vsb = ttk.Scrollbar(self.tab_metrics, orient="vertical",
                            command=self.met_tree.yview)
        self.met_tree.configure(yscrollcommand=vsb.set)
        self.met_tree.pack(side="left", fill="both", expand=True,
                           padx=(8, 0), pady=8)
        vsb.pack(side="right", fill="y", pady=8, padx=(0, 8))

        # Summary footer
        self.met_summary_fr = tk.Frame(self.tab_metrics, bg=BG_PANEL, height=50)
        self.met_summary_fr.pack(fill="x", side="bottom")
        self.met_summary_fr.pack_propagate(False)
        self.summary_lbl = tk.Label(self.met_summary_fr, text="",
                                    bg=BG_PANEL, fg=SUCCESS,
                                    font=("Segoe UI", 11, "bold"))
        self.summary_lbl.pack(padx=16, pady=12)

    # ── Tab 3: Compare ───────────────────────────────────────────────

    def _build_compare_tab(self):
        self.compare_area = tk.Frame(self.tab_compare, bg=BG_DARK)
        self.compare_area.pack(fill="both", expand=True)
        self._placeholder(self.compare_area,
                          "Click  📊 Compare ALL Algorithms  to see the comparison")

    # ─────────────────────────────────────────────────────────────────
    #  PROCESS MANAGEMENT
    # ─────────────────────────────────────────────────────────────────

    def _add_process(self):
        """Validate input fields and append a new process to the queue."""
        try:
            arrival  = int(self.entries["Arrival Time"].get())
            burst    = int(self.entries["Burst Time"].get())
            priority = int(self.entries["Priority"].get())
            if arrival < 0:
                raise ValueError("Arrival time must be >= 0.")
            if burst <= 0:
                raise ValueError("Burst time must be > 0.")
            if priority < 1:
                raise ValueError("Priority must be >= 1.")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self)
            return

        pid = f"P{self.pid_counter}"
        self.pid_counter += 1
        proc = {"pid": pid, "arrival": arrival,
                "burst": burst, "priority": priority}
        self.processes.append(proc)

        tag = "odd" if len(self.processes) % 2 else "even"
        self.proc_tree.insert("", "end",
                              values=(pid, arrival, burst, priority),
                              tags=(tag,))

        # Reset entry fields to defaults for the next process
        for key, val in [("Arrival Time","0"),("Burst Time","5"),("Priority","1")]:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, val)

    def _remove_process(self):
        """Delete selected row(s) from the queue."""
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showinfo("Nothing Selected",
                                "Please click a row first.", parent=self)
            return
        for item in sel:
            pid = self.proc_tree.item(item)["values"][0]
            self.processes = [p for p in self.processes if p["pid"] != pid]
            self.proc_tree.delete(item)
        # Re-stripe
        for i, item in enumerate(self.proc_tree.get_children()):
            self.proc_tree.item(item, tags=("odd" if i % 2 else "even",))

    def _clear_processes(self):
        """Remove every process and reset the PID counter."""
        if self.processes:
            if not messagebox.askyesno("Clear All",
                                       "Remove all processes?", parent=self):
                return
        self.processes.clear()
        self.pid_counter = 1
        for item in self.proc_tree.get_children():
            self.proc_tree.delete(item)

    def _load_sample_data(self):
        """Pre-populate with five sample processes for immediate demonstration."""
        for arr, bur, pri in [(0,6,3),(2,4,1),(4,8,2),(6,3,4),(8,5,2)]:
            for key, val in [("Arrival Time",arr),
                             ("Burst Time",bur),("Priority",pri)]:
                self.entries[key].delete(0,"end")
                self.entries[key].insert(0,str(val))
            self._add_process()

    # ─────────────────────────────────────────────────────────────────
    #  ALGORITHM CONTROL
    # ─────────────────────────────────────────────────────────────────

    def _on_algo_change(self, _=None):
        """Enable quantum spinner only for RR; enable priority-mode only for Priority."""
        algo  = self.algo_var.get()
        q_st  = "normal"   if algo == "Round Robin" else "disabled"
        p_st  = "readonly" if algo == "Priority"    else "disabled"
        if self._quantum_widget:
            self._quantum_widget.configure(state=q_st)
        if self._prio_widget:
            self._prio_widget.configure(state=p_st)

    def _dispatch_algo(self, name):
        """
        Run the named algorithm on self.processes.
        Returns (done_list, timeline) or (None, None) on failure.
        """
        if not self.processes:
            messagebox.showwarning("No Processes",
                                   "Add at least one process first.", parent=self)
            return None, None
        try:
            q   = self.quantum_var.get()
            pre = self.prio_mode.get() == "Preemptive"
            if   name == "FCFS":                    return fcfs(self.processes)
            elif name == "Round Robin":             return round_robin(self.processes, q)
            elif name == "SPN (SJF)":               return spn(self.processes)
            elif name == "SRTN (Preemptive SJF)":   return srtn(self.processes)
            elif name == "Priority":                return priority_scheduling(self.processes, pre)
            else:
                messagebox.showerror("Error", f"Unknown algorithm: {name}", parent=self)
                return None, None
        except Exception as exc:
            messagebox.showerror("Runtime Error", str(exc), parent=self)
            return None, None

    def _run_single(self):
        """Run the selected algorithm and show results in Gantt + Metrics tabs."""
        name = self.algo_var.get()
        done, timeline = self._dispatch_algo(name)
        if done is None:
            return

        awt, atat, art = calc_metrics(done)
        display = name
        if name == "Round Robin":
            display += f"  (Quantum = {self.quantum_var.get()})"
        elif name == "Priority":
            display += f"  [{self.prio_mode.get()}]"

        self._render_gantt(timeline, done, display, awt, atat, art)
        self._fill_metrics(done, awt, atat, art)
        self.notebook.select(0)

    def _run_comparison(self):
        """
        Run all five algorithms, gather metrics, and render the comparison view.
        Automatically selects the best algorithm based on a combined score.
        """
        if not self.processes:
            messagebox.showwarning("No Processes",
                                   "Add at least one process first.", parent=self)
            return

        algo_names = [
            "FCFS",
            "Round Robin",
            "SPN (SJF)",
            "SRTN (Preemptive SJF)",
            "Priority",
        ]

        results   = {}
        timelines = {}

        for name in algo_names:
            done, tl = self._dispatch_algo(name)
            if done is None:
                return
            awt, atat, art = calc_metrics(done)
            results[name]   = {"awt": awt, "atat": atat, "art": art, "done": done}
            timelines[name] = tl

        self._render_comparison(results, timelines)
        self.notebook.select(2)

    # ─────────────────────────────────────────────────────────────────
    #  RENDERING — GANTT CHART
    # ─────────────────────────────────────────────────────────────────

    def _render_gantt(self, timeline, done, label, awt, atat, art):
        """
        Draw a horizontal Gantt chart for one algorithm inside Tab 1.
        Each process gets a unique colour.  Segment boundaries are ticked.
        """
        self._clear_frame(self.gantt_area)

        # Update info bar
        self.gantt_title_lbl.config(text=f"Algorithm:  {label}", fg=TEXT_W)
        self.gantt_metric_lbl.config(
            text=(f"Avg Wait: {awt:.2f}   |   Avg Turnaround: {atat:.2f}"
                  f"   |   Avg Response: {art:.2f}"))

        # PID → colour map (sorted for consistency)
        pids = sorted({p["pid"] for p in done},
                      key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        cmap = {pid: PROCESS_COLORS[i % len(PROCESS_COLORS)]
                for i, pid in enumerate(pids)}

        # Create figure — single axes occupying most of the canvas
        fig = plt.Figure(facecolor=BG_DARK)
        ax  = fig.add_axes([0.04, 0.28, 0.93, 0.52])
        ax.set_facecolor(BG_PANEL)

        BY, BH = 0.5, 0.60   # bar Y-centre and height

        for seg in timeline:
            w = seg["end"] - seg["start"]
            if w <= 0:
                continue
            ax.barh(BY, w, left=seg["start"], height=BH,
                    color=cmap.get(seg["pid"], "#888"),
                    edgecolor=BG_DARK, linewidth=1.0, zorder=3)
            if w >= 0.6:
                ax.text((seg["start"] + seg["end"]) / 2, BY,
                        seg["pid"],
                        ha="center", va="center",
                        fontsize=9, fontweight="bold", color="white", zorder=4)

        # ── X axis ticks at every segment boundary ────────────────────
        if timeline:
            max_t  = max(s["end"] for s in timeline)
            ticks  = sorted({s["start"] for s in timeline} |
                            {s["end"]   for s in timeline})
            ax.set_xticks(ticks)
            ax.set_xticklabels([str(int(t)) for t in ticks],
                               color=TEXT_W, fontsize=8)
            ax.set_xlim(-0.3, max_t + 0.5)
            for t in ticks:
                ax.axvline(t, color="#2a2a50", linewidth=0.7,
                           linestyle="--", zorder=1)
        else:
            ax.set_xlim(0, 10)

        ax.set_ylim(0, 1.15)
        ax.set_yticks([])
        ax.tick_params(axis="x", colors=TEXT_W, length=4)
        for sp in ax.spines.values():
            sp.set_edgecolor("#2a2a50")

        # ── Legend ────────────────────────────────────────────────────
        patches = [mpatches.Patch(facecolor=cmap[p], label=p,
                                  edgecolor="white", linewidth=0.4)
                   for p in pids]
        ax.legend(handles=patches,
                  loc="upper center", bbox_to_anchor=(0.5, 1.62),
                  ncol=min(len(pids), 10), framealpha=0.25,
                  facecolor=BG_CARD, edgecolor="#444466",
                  labelcolor="white", fontsize=9, handlelength=1.4)

        ax.set_title(f"Gantt Chart  —  {label}",
                     color=TEXT_W, fontsize=12, fontweight="bold", pad=32)

        # ── Embed canvas ──────────────────────────────────────────────
        cv = FigureCanvasTkAgg(fig, master=self.gantt_area)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

        tb_fr = tk.Frame(self.gantt_area, bg=BG_PANEL)
        tb_fr.pack(fill="x")
        tb = NavigationToolbar2Tk(cv, tb_fr)
        tb.config(background=BG_PANEL)
        tb.update()

    # ─────────────────────────────────────────────────────────────────
    #  RENDERING — METRICS TABLE
    # ─────────────────────────────────────────────────────────────────

    def _fill_metrics(self, done, awt, atat, art):
        """Populate Tab 2 with per-process timing data and averages."""
        for row in self.met_tree.get_children():
            self.met_tree.delete(row)

        sorted_done = sorted(done,
                             key=lambda p: int(p["pid"][1:])
                             if p["pid"][1:].isdigit() else 0)
        for idx, p in enumerate(sorted_done):
            st  = p.get("start", p["finish"] - p["burst"])
            tag = "odd" if idx % 2 else "even"
            self.met_tree.insert("", "end", tags=(tag,), values=(
                p["pid"],
                p["arrival"],
                p["burst"],
                p.get("priority", "—"),
                int(st),
                p["finish"],
                round(p["waiting"],    2),
                round(p["turnaround"], 2),
                round(p["response"],   2),
            ))

        self.summary_lbl.config(
            text=(f"  Avg Waiting: {awt:.2f}   |   "
                  f"Avg Turnaround: {atat:.2f}   |   "
                  f"Avg Response: {art:.2f}  "))

    # ─────────────────────────────────────────────────────────────────
    #  RENDERING — COMPARISON VIEW
    # ─────────────────────────────────────────────────────────────────

    def _render_comparison(self, results, timelines):
        """
        Build the full comparison view in Tab 3:
          - Row 0: bar charts for AWT, ATAT, ART (all 5 algorithms)
          - Rows 1-2: mini Gantt charts for each algorithm
          - Bottom-right cell: recommendation summary box
        """
        self._clear_frame(self.compare_area)

        algos = list(results.keys())

        awt_vals  = [results[a]["awt"]  for a in algos]
        atat_vals = [results[a]["atat"] for a in algos]
        art_vals  = [results[a]["art"]  for a in algos]

        # Find which algorithm wins each metric (lowest value)
        best_awt  = algos[awt_vals.index(min(awt_vals))]
        best_atat = algos[atat_vals.index(min(atat_vals))]
        best_art  = algos[art_vals.index(min(art_vals))]

        # Consistent colour per algorithm (for bar charts)
        algo_clr = {a: PROCESS_COLORS[i % len(PROCESS_COLORS)]
                    for i, a in enumerate(algos)}

        # Short labels (prevent x-axis overlap)
        short = {
            "FCFS":                  "FCFS",
            "Round Robin":           "RR",
            "SPN (SJF)":             "SPN",
            "SRTN (Preemptive SJF)": "SRTN",
            "Priority":              "Priority",
        }
        xlabels = [short.get(a, a) for a in algos]

        # Consistent colour per process PID (for Gantt bars)
        all_pids = sorted(
            {seg["pid"] for tl in timelines.values() for seg in tl},
            key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        pid_clr = {pid: PROCESS_COLORS[i % len(PROCESS_COLORS)]
                   for i, pid in enumerate(all_pids)}

        # ── Figure layout: 3 rows × 3 cols ───────────────────────────
        
        # =====================================================================
        # ADDED FIX: Lowered the 'top' margin to 0.85 (from 0.93) to provide 
        # enough clearance between the main suptitle and the row 0 subplot titles.
        # =====================================================================
        fig = plt.Figure(figsize=(14, 10), facecolor=BG_DARK)
        gs  = gridspec.GridSpec(
            3, 3, figure=fig,
            hspace=0.72, wspace=0.38,
            left=0.05, right=0.98,
            top=0.85, bottom=0.05,
        )

        # ── Helper: bar chart ─────────────────────────────────────────
        def bar_chart(ax, vals, title, best):
            """
            Draw a grouped bar chart for one metric across all algorithms.
            The winning bar gets a green outline; its x-label is highlighted.
            """
            colors = [algo_clr[a] for a in algos]
            bars   = ax.bar(xlabels, vals, color=colors,
                            edgecolor=BG_DARK, linewidth=1.0, zorder=3)

            max_v = max(vals) if max(vals) > 0 else 1

            for bar, v, a in zip(bars, vals, algos):
                if a == best:
                    bar.set_edgecolor(SUCCESS)
                    bar.set_linewidth(2.5)
                # Value label above bar
                ax.text(bar.get_x() + bar.get_width() / 2,
                        v + max_v * 0.025,
                        f"{v:.2f}",
                        ha="center", va="bottom",
                        fontsize=7.5, color=TEXT_W, zorder=4)

            ax.set_facecolor(BG_PANEL)
            ax.set_title(title, color=TEXT_W, fontsize=9,
                         fontweight="bold", pad=7)
            ax.set_ylim(0, max_v * 1.35)
            ax.yaxis.grid(True, color="#2a2a50", linewidth=0.5, zorder=0)
            ax.set_axisbelow(True)

            # Colour-code x-tick labels; highlight winner
            ax.set_xticks(range(len(xlabels)))
            ax.set_xticklabels(xlabels, fontsize=8)
            for tick, a in zip(ax.get_xticklabels(), algos):
                tick.set_color(SUCCESS if a == best else TEXT_W)
                if a == best:
                    tick.set_fontweight("bold")

            ax.tick_params(axis="y", colors=TEXT_W, labelsize=7)
            for sp in ax.spines.values():
                sp.set_edgecolor("#2a2a50")

        # ── Draw the three bar charts (row 0) ─────────────────────────
        bar_chart(fig.add_subplot(gs[0, 0]),
                  awt_vals,  "Avg Waiting Time\n(lower = better)", best_awt)
        bar_chart(fig.add_subplot(gs[0, 1]),
                  atat_vals, "Avg Turnaround Time\n(lower = better)", best_atat)
        bar_chart(fig.add_subplot(gs[0, 2]),
                  art_vals,  "Avg Response Time\n(lower = better)", best_art)

        # ── Helper: mini Gantt ────────────────────────────────────────
        def mini_gantt(ax, algo_name):
            """
            Draw a compact Gantt timeline for one algorithm.
            The title turns green if this algorithm wins any metric.
            """
            tl  = timelines[algo_name]
            awt = results[algo_name]["awt"]
            ax.set_facecolor(BG_PANEL)
            ax.set_yticks([])

            if not tl:
                ax.set_title(short.get(algo_name, algo_name),
                             color=TEXT_W, fontsize=8, fontweight="bold")
                return

            max_t = max(s["end"] for s in tl)
            BY, BH = 0.5, 0.55

            for seg in tl:
                w = seg["end"] - seg["start"]
                if w <= 0:
                    continue
                ax.barh(BY, w, left=seg["start"], height=BH,
                        color=pid_clr.get(seg["pid"], "#888"),
                        edgecolor=BG_DARK, linewidth=0.6, zorder=3)
                # Label only if bar is wide enough
                min_label_w = max(1, max_t / 22)
                if w >= min_label_w:
                    ax.text((seg["start"] + seg["end"]) / 2, BY,
                            seg["pid"],
                            ha="center", va="center",
                            fontsize=6, color="white",
                            fontweight="bold", zorder=4)

            # Tick marks at all boundaries
            ticks = sorted({s["start"] for s in tl} | {s["end"] for s in tl})
            ax.set_xticks(ticks)
            ax.set_xticklabels([str(int(t)) for t in ticks],
                               color=TEXT_W, fontsize=5.5, rotation=45)
            ax.set_xlim(-0.3, max_t + 0.5)
            ax.set_ylim(0, 1.1)
            ax.tick_params(axis="x", colors=TEXT_W, length=2, pad=1)
            for sp in ax.spines.values():
                sp.set_edgecolor("#2a2a50")

            # Green title if this algorithm wins at least one metric
            is_winner = algo_name in {best_awt, best_atat, best_art}
            ax.set_title(
                f"{short.get(algo_name, algo_name)}  (AWT={awt:.1f})",
                color=SUCCESS if is_winner else TEXT_W,
                fontsize=8, fontweight="bold", pad=5)

        # ── Draw mini Gantt charts (rows 1-2) ────────────────────────
        positions = [(1,0),(1,1),(1,2),(2,0),(2,1)]
        for (r, c), algo in zip(positions, algos):
            mini_gantt(fig.add_subplot(gs[r, c]), algo)

        # ── Recommendation box (row 2, col 2) ────────────────────────
        ax_rec = fig.add_subplot(gs[2, 2])
        ax_rec.set_facecolor("#0d0d24")
        ax_rec.set_xticks([])
        ax_rec.set_yticks([])
        for sp in ax_rec.spines.values():
            sp.set_edgecolor(ACCENT)
            sp.set_linewidth(1.8)

        # Score: 1 point per metric won
        score = {a: 0 for a in algos}
        for w in [best_awt, best_atat, best_art]:
            score[w] += 1
        best_overall = max(score, key=score.get)

        rec_content = [
            # (text, x-position, y-position, align, font-size, colour, weight)
            ("★  RECOMMENDATION  ★",            0.5,  0.85, "center", 11, SUCCESS, "bold"),
            ("Best Overall Algorithm",           0.5,  0.70, "center",  9, TEXT_W,  "bold"),
            (short.get(best_overall, best_overall),  0.5,  0.57, "center", 14, SUCCESS, "bold"),
            ("",                                 0.5,  0.46, "center",  1, TEXT_W,  "normal"),
            
            # --- Aligned text block below ---
            ("Best AWT",                         0.28, 0.38, "left",    8, TEXT_W,  "normal"),
            (f"→  {short.get(best_awt, best_awt)}",  0.52, 0.38, "left",    8, SUCCESS, "bold"),
            
            ("Best ATAT",                        0.28, 0.27, "left",    8, TEXT_W,  "normal"),
            (f"→  {short.get(best_atat, best_atat)}",0.52, 0.27, "left",    8, SUCCESS, "bold"),
            
            ("Best ART",                         0.28, 0.16, "left",    8, TEXT_W,  "normal"),
            (f"→  {short.get(best_art, best_art)}",  0.52, 0.16, "left",    8, SUCCESS, "bold"),
            
            ("lower value = better",             0.5,  0.05, "center",  7, TEXT_M,  "normal"),
        ]

        # Note the updated unpacking variables (txt, x, y, align, fs, col, wt)
        for txt, x, y, align, fs, col, wt in rec_content:
            ax_rec.text(x, y, txt,
                        transform=ax_rec.transAxes,
                        ha=align, va="center",
                        fontsize=fs, color=col, fontweight=wt)

        # ── Global figure title ────────────────────────────────────────
        fig.suptitle(
            "CPU Scheduling — Full Algorithm Comparison",
            color=TEXT_W, fontsize=13, fontweight="bold", y=0.98)

        # ── Process legend (top-right corner of figure) ───────────────
        leg_patches = [mpatches.Patch(facecolor=pid_clr[p], label=p,
                                      linewidth=0)
                       for p in all_pids]
        fig.legend(handles=leg_patches,
                   loc="upper right", bbox_to_anchor=(0.99, 0.975),
                   ncol=1, framealpha=0.2,
                   facecolor=BG_CARD, edgecolor="#444466",
                   labelcolor="white", fontsize=7.5,
                   title="Processes", title_fontsize=8)

        # ── Embed canvas + toolbar ────────────────────────────────────
        cv = FigureCanvasTkAgg(fig, master=self.compare_area)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

        tb_fr = tk.Frame(self.compare_area, bg=BG_PANEL)
        tb_fr.pack(fill="x")
        tb = NavigationToolbar2Tk(cv, tb_fr)
        tb.config(background=BG_PANEL)
        tb.update()

    # ─────────────────────────────────────────────────────────────────
    #  UTILITY HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _clear_frame(self, frame):
        """Destroy all child widgets inside frame (clears before re-drawing)."""
        for w in frame.winfo_children():
            w.destroy()

    def _placeholder(self, frame, msg):
        """Show a centred hint message in an empty frame."""
        tk.Label(frame, text=msg, bg=BG_DARK, fg=TEXT_M,
                 font=("Segoe UI", 12)).pack(expand=True)

    def _labeled_box(self, parent, title):
        """Create and return a styled LabelFrame section box."""
        lf = tk.LabelFrame(parent,
                           text=f"  {title}  ",
                           bg=BG_PANEL, fg=ACCENT,
                           font=("Segoe UI", 10, "bold"),
                           relief="groove", bd=1, labelanchor="nw")
        return lf

    def _btn(self, parent, text, cmd, color, width=None):
        """Create a flat styled tk.Button."""
        kw = dict(text=text, command=cmd,
                  bg=color, fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=color, activeforeground="#dddddd",
                  padx=10, pady=7)
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()