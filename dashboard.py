"""
╔══════════════════════════════════════════════════════════════╗
║  Fuzzy Humidity Control — IoT Dashboard                     ║
║  STM32F103C8 Real-Time Monitor                              ║
║  Supervisor: Ir. Kemalasari, M.T.                           ║
╚══════════════════════════════════════════════════════════════╝

Dependencies:
    pip install pyserial matplotlib

Usage:
    python dashboard.py
    python dashboard.py --port COM12 --baud 115200
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import threading
import queue
import re
import time
import sys
import argparse
from collections import deque

# ── Matplotlib embed ─────────────────────────────────────────
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

# ── Serial ───────────────────────────────────────────────────
import serial
import serial.tools.list_ports

# ═════════════════════════════════════════════════════════════
#  CONFIG
# ═════════════════════════════════════════════════════════════
DEFAULT_PORT = "COM12"
DEFAULT_BAUD = 115200
CHART_POINTS = 200          # jumlah titik data di grafik
GUI_REFRESH_MS = 40         # refresh GUI setiap 40ms (25 FPS)

# ═════════════════════════════════════════════════════════════
#  COLORS — Dark IoT Theme
# ═════════════════════════════════════════════════════════════
C = {
    "bg":           "#0f1117",
    "card":         "#1a1d27",
    "card_border":  "#2a2d3a",
    "text":         "#e4e6ed",
    "text_dim":     "#6b7085",
    "accent_blue":  "#3b82f6",
    "accent_cyan":  "#06b6d4",
    "accent_green": "#10b981",
    "accent_amber": "#f59e0b",
    "accent_red":   "#ef4444",
    "accent_purple":"#8b5cf6",
    "bar_bg":       "#1e2130",
    "chart_bg":     "#141620",
    "chart_grid":   "#1e2130",
}

# ═════════════════════════════════════════════════════════════
#  SERIAL PARSER  (regex, compiled once)
# ═════════════════════════════════════════════════════════════
# Format: Suhu:49.3C | Kel:98.4% | PWM:255 | RAW[4038,4031]
RE_DATA = re.compile(
    r"Suhu:\s*(\d+)\.(\d+)C\s*\|\s*Kel:\s*(\d+)\.(\d+)%\s*\|"
    r"\s*PWM:\s*(\d+)\s*\|\s*RAW\[(\d+),(\d+)\]"
)


def parse_line(line: str):
    """Parse satu baris serial → dict atau None."""
    m = RE_DATA.search(line)
    if not m:
        return None
    g = m.groups()
    return {
        "suhu": int(g[0]) + int(g[1]) / 10.0,
        "kel":  int(g[2]) + int(g[3]) / 10.0,
        "pwm":  int(g[4]),
        "raw0": int(g[5]),
        "raw1": int(g[6]),
    }


# ═════════════════════════════════════════════════════════════
#  SERIAL READER THREAD
# ═════════════════════════════════════════════════════════════
class SerialReader(threading.Thread):
    """Thread yang membaca serial dan push ke queue."""

    def __init__(self, port, baud, data_queue, status_queue):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.dq = data_queue
        self.sq = status_queue
        self._stop_evt = threading.Event()

    def stop(self):
        self._stop_evt.set()

    def run(self):
        while not self._stop_evt.is_set():
            try:
                self.sq.put(("connecting", self.port))
                ser = serial.Serial(self.port, self.baud, timeout=0.1)
                self.sq.put(("connected", self.port))
                buf = ""
                while not self._stop_evt.is_set():
                    chunk = ser.read(ser.in_waiting or 1)
                    if chunk:
                        buf += chunk.decode("ascii", errors="ignore")
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            d = parse_line(line.strip())
                            if d:
                                self.dq.put(d)
            except serial.SerialException as e:
                self.sq.put(("error", str(e)))
                time.sleep(2)      # retry setelah 2 detik
            except Exception as e:
                self.sq.put(("error", str(e)))
                time.sleep(2)


# ═════════════════════════════════════════════════════════════
#  GAUGE CARD WIDGET
# ═════════════════════════════════════════════════════════════
class GaugeCard(tk.Frame):
    """Card dengan label, value besar, unit, dan progress bar."""

    def __init__(self, parent, title, unit, color, vmin=0, vmax=100, **kw):
        super().__init__(parent, bg=C["card"], highlightbackground=C["card_border"],
                         highlightthickness=1, **kw)
        self.color = color
        self.vmin = vmin
        self.vmax = vmax

        # Title
        tk.Label(self, text=title, font=("Segoe UI", 10), fg=C["text_dim"],
                 bg=C["card"], anchor="w").pack(fill="x", padx=16, pady=(14, 0))

        # Value frame
        vf = tk.Frame(self, bg=C["card"])
        vf.pack(fill="x", padx=16, pady=(2, 0))

        self.lbl_val = tk.Label(vf, text="—", font=("Consolas", 36, "bold"),
                                fg=color, bg=C["card"], anchor="w")
        self.lbl_val.pack(side="left")

        self.lbl_unit = tk.Label(vf, text=unit, font=("Segoe UI", 14),
                                 fg=C["text_dim"], bg=C["card"], anchor="sw")
        self.lbl_unit.pack(side="left", padx=(4, 0), pady=(0, 6))

        # Progress bar (canvas)
        self.bar_h = 6
        self.bar_canvas = tk.Canvas(self, height=self.bar_h, bg=C["bar_bg"],
                                     highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=16, pady=(8, 14))
        self.bar_rect = None

    def set_value(self, val):
        text = f"{val:.1f}" if isinstance(val, float) else str(val)
        self.lbl_val.config(text=text)

        # Update bar
        self.bar_canvas.delete("all")
        w = self.bar_canvas.winfo_width()
        if w > 1:
            frac = max(0.0, min(1.0, (val - self.vmin) / (self.vmax - self.vmin)))
            fill_w = int(w * frac)
            # Background
            self.bar_canvas.create_rectangle(0, 0, w, self.bar_h,
                                              fill=C["bar_bg"], outline="")
            # Filled
            if fill_w > 0:
                self.bar_canvas.create_rectangle(0, 0, fill_w, self.bar_h,
                                                  fill=self.color, outline="")


# ═════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═════════════════════════════════════════════════════════════
class Dashboard(tk.Tk):
    def __init__(self, port, baud):
        super().__init__()
        self.title("🌡️ Fuzzy Humidity Control — IoT Dashboard")
        self.configure(bg=C["bg"])
        self.geometry("980x700")
        self.minsize(820, 600)

        self.data_q = queue.Queue(maxsize=500)
        self.status_q = queue.Queue(maxsize=50)

        # Chart data buffers
        self.t_data = deque(maxlen=CHART_POINTS)
        self.suhu_data = deque(maxlen=CHART_POINTS)
        self.kel_data = deque(maxlen=CHART_POINTS)
        self.pwm_data = deque(maxlen=CHART_POINTS)
        self.t_counter = 0

        self._build_ui()
        self._build_chart()

        # Start serial reader
        self.reader = SerialReader(port, baud, self.data_q, self.status_q)
        self.reader.start()

        # Start GUI refresh loop
        self.after(GUI_REFRESH_MS, self._refresh)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI Layout ────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ───────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(hdr, text="⚡ Fuzzy Humidity Control",
                 font=("Segoe UI Semibold", 18), fg=C["text"],
                 bg=C["bg"]).pack(side="left")

        # Status indicator
        sf = tk.Frame(hdr, bg=C["bg"])
        sf.pack(side="right")

        self.status_dot = tk.Canvas(sf, width=10, height=10, bg=C["bg"],
                                     highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6))
        self._dot = self.status_dot.create_oval(1, 1, 9, 9, fill=C["accent_amber"],
                                                 outline="")

        self.status_lbl = tk.Label(sf, text="Connecting...",
                                    font=("Segoe UI", 9), fg=C["text_dim"],
                                    bg=C["bg"])
        self.status_lbl.pack(side="left")

        # ── Subtitle ─────────────────────────────────────────
        tk.Label(self, text="Supervisor: Ir. Kemalasari, M.T.  •  STM32F103C8  •  Fuzzy Sugeno",
                 font=("Segoe UI", 9), fg=C["text_dim"],
                 bg=C["bg"]).pack(anchor="w", padx=20, pady=(2, 12))

        # ── Gauge Cards Row ──────────────────────────────────
        cards = tk.Frame(self, bg=C["bg"])
        cards.pack(fill="x", padx=20, pady=(0, 12))
        cards.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="card")

        self.g_suhu = GaugeCard(cards, "🌡️ SUHU", "°C", C["accent_red"],
                                 vmin=0, vmax=50)
        self.g_suhu.grid(row=0, column=0, sticky="nsew", padx=(0, 6), ipady=2)

        self.g_kel = GaugeCard(cards, "💧 KELEMBAPAN", "%", C["accent_cyan"],
                                vmin=0, vmax=100)
        self.g_kel.grid(row=0, column=1, sticky="nsew", padx=6, ipady=2)

        self.g_pwm = GaugeCard(cards, "⚙️ PWM OUTPUT", "/ 255", C["accent_green"],
                                vmin=0, vmax=255)
        self.g_pwm.grid(row=0, column=2, sticky="nsew", padx=6, ipady=2)

        self.g_raw0 = GaugeCard(cards, "📊 RAW ADC CH0", "", C["accent_purple"],
                                 vmin=0, vmax=4095)
        self.g_raw0.grid(row=0, column=3, sticky="nsew", padx=6, ipady=2)

        self.g_raw1 = GaugeCard(cards, "📊 RAW ADC CH1", "", C["accent_blue"],
                                 vmin=0, vmax=4095)
        self.g_raw1.grid(row=0, column=4, sticky="nsew", padx=(6, 0), ipady=2)

    # ── Chart ────────────────────────────────────────────────
    def _build_chart(self):
        chart_frame = tk.Frame(self, bg=C["card"], highlightbackground=C["card_border"],
                               highlightthickness=1)
        chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Title
        tk.Label(chart_frame, text="📈 REAL-TIME TREND",
                 font=("Segoe UI", 10), fg=C["text_dim"],
                 bg=C["card"], anchor="w").pack(fill="x", padx=16, pady=(10, 0))

        # Matplotlib figure
        self.fig = Figure(figsize=(9, 3), dpi=100, facecolor=C["chart_bg"])
        self.fig.subplots_adjust(left=0.06, right=0.94, top=0.92, bottom=0.12)

        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_facecolor(C["chart_bg"])
        self.ax1.tick_params(colors=C["text_dim"], labelsize=8)
        self.ax1.spines["top"].set_visible(False)
        self.ax1.spines["right"].set_visible(False)
        self.ax1.spines["bottom"].set_color(C["chart_grid"])
        self.ax1.spines["left"].set_color(C["chart_grid"])
        self.ax1.grid(True, color=C["chart_grid"], linewidth=0.5, alpha=0.5)
        self.ax1.set_ylabel("Suhu (°C) / Kel (%)", fontsize=8, color=C["text_dim"])

        # Twin axis for PWM
        self.ax2 = self.ax1.twinx()
        self.ax2.tick_params(colors=C["text_dim"], labelsize=8)
        self.ax2.spines["top"].set_visible(False)
        self.ax2.spines["right"].set_color(C["chart_grid"])
        self.ax2.spines["left"].set_visible(False)
        self.ax2.spines["bottom"].set_visible(False)
        self.ax2.set_ylabel("PWM", fontsize=8, color=C["text_dim"])

        # Init lines (empty)
        self.line_suhu, = self.ax1.plot([], [], color=C["accent_red"],
                                         linewidth=1.5, label="Suhu")
        self.line_kel,  = self.ax1.plot([], [], color=C["accent_cyan"],
                                         linewidth=1.5, label="Kel")
        self.line_pwm,  = self.ax2.plot([], [], color=C["accent_green"],
                                         linewidth=1.5, alpha=0.7, label="PWM",
                                         linestyle="--")

        # Legend
        lines = [self.line_suhu, self.line_kel, self.line_pwm]
        labels = [l.get_label() for l in lines]
        self.ax1.legend(lines, labels, loc="upper left", fontsize=7,
                        facecolor=C["card"], edgecolor=C["card_border"],
                        labelcolor=C["text_dim"])

        self.ax1.set_ylim(-2, 105)
        self.ax2.set_ylim(-5, 270)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(4, 10))

    # ── Refresh Loop ─────────────────────────────────────────
    def _refresh(self):
        updated = False

        # Drain status queue
        while not self.status_q.empty():
            try:
                kind, msg = self.status_q.get_nowait()
                if kind == "connected":
                    self.status_lbl.config(text=f"Connected • {msg}")
                    self.status_dot.itemconfig(self._dot, fill=C["accent_green"])
                elif kind == "connecting":
                    self.status_lbl.config(text=f"Connecting to {msg}...")
                    self.status_dot.itemconfig(self._dot, fill=C["accent_amber"])
                elif kind == "error":
                    self.status_lbl.config(text=f"Error: {msg[:40]}")
                    self.status_dot.itemconfig(self._dot, fill=C["accent_red"])
            except queue.Empty:
                break

        # Drain data queue — ambil semua data, pakai yang terakhir untuk gauge
        last = None
        count = 0
        while not self.data_q.empty():
            try:
                d = self.data_q.get_nowait()
                last = d
                count += 1

                # Append to chart data
                self.t_counter += 1
                self.t_data.append(self.t_counter)
                self.suhu_data.append(d["suhu"])
                self.kel_data.append(d["kel"])
                self.pwm_data.append(d["pwm"])
            except queue.Empty:
                break

        # Update gauge cards dengan data terakhir
        if last:
            self.g_suhu.set_value(last["suhu"])
            self.g_kel.set_value(last["kel"])
            self.g_pwm.set_value(last["pwm"])
            self.g_raw0.set_value(last["raw0"])
            self.g_raw1.set_value(last["raw1"])
            updated = True

        # Update chart (hanya jika ada data baru)
        if updated and len(self.t_data) > 1:
            t = list(self.t_data)
            self.line_suhu.set_data(t, list(self.suhu_data))
            self.line_kel.set_data(t, list(self.kel_data))
            self.line_pwm.set_data(t, list(self.pwm_data))

            self.ax1.set_xlim(t[0], t[-1])
            self.ax2.set_xlim(t[0], t[-1])

            self.canvas.draw_idle()

        # Schedule next refresh
        self.after(GUI_REFRESH_MS, self._refresh)

    def _on_close(self):
        self.reader.stop()
        self.destroy()


# ═════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Fuzzy Humidity Control Dashboard")
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--list", action="store_true", help="List available serial ports")
    args = parser.parse_args()

    if args.list:
        print("Available serial ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device:10s}  {p.description}")
        sys.exit(0)

    print(f"Starting dashboard — port={args.port}, baud={args.baud}")
    print("Tip: gunakan --list untuk melihat port yang tersedia")

    app = Dashboard(args.port, args.baud)
    app.mainloop()


if __name__ == "__main__":
    main()
