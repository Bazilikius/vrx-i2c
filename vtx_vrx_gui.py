#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import threading
from vtx_table import BAND_TABLE, VTX_12G_TABLE

class VTXControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VTX/VRX Pro Controller")
        self.ser = None

        # Main Layout
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # 1. Connection Bar (Top)
        conn_frame = ttk.Frame(root, padding="5")
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

        ttk.Label(conn_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=15)
        self.port_combo['values'] = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(conn_frame, text="⟳", width=3, command=self.refresh_ports).pack(side=tk.LEFT)
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(conn_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.LEFT, padx=10)

        # 2. Main Control Area (Middle)
        control_frame = ttk.Frame(root, padding="5")
        control_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        control_frame.columnconfigure(0, weight=1) # VTX Col
        control_frame.columnconfigure(1, weight=5) # VRX Grid Col
        control_frame.rowconfigure(0, weight=1)

        # --- Left Column: VTX Control ---
        vtx_side_frame = ttk.Frame(control_frame)
        vtx_side_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        vtx_freq_lf = ttk.LabelFrame(vtx_side_frame, text="VTX Frequency (1.2G)", padding="5")
        vtx_freq_lf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for freq in VTX_12G_TABLE:
            btn = ttk.Button(vtx_freq_lf, text=f"{freq} MHz",
                             command=lambda f=freq: self.send_command(f"V {f}"))
            btn.pack(fill=tk.X, pady=1)

        vtx_pwr_lf = ttk.LabelFrame(vtx_side_frame, text="VTX Power", padding="5")
        vtx_pwr_lf.pack(fill=tk.X, padx=5, pady=5)
        power_levels = [25, 200, 400, 600, 1000, 1600]
        for p in power_levels:
            btn = ttk.Button(vtx_pwr_lf, text=f"{p} mW",
                             command=lambda val=p: self.send_command(f"P {val}"))
            btn.pack(fill=tk.X, pady=1)

        # --- Right Column: VRX Grid (2 Main Columns of Bands) ---
        vrx_main_lf = ttk.LabelFrame(control_frame, text="VRX Channels", padding="5")
        vrx_main_lf.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)

        canvas = tk.Canvas(vrx_main_lf)
        scrollbar = ttk.Scrollbar(vrx_main_lf, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Organize bands into three major columns
        bands = list(BAND_TABLE.keys())
        num_bands = len(bands)
        # Calculate items per column
        col_count = 3
        per_col = (num_bands + col_count - 1) // col_count

        # We'll create three sub-frames within the scroll_frame
        columns = []
        for i in range(col_count):
            col = ttk.Frame(scroll_frame)
            col.grid(row=0, column=i, sticky=tk.N, padx=10)
            columns.append(col)

        for idx, band in enumerate(bands):
            col_idx = idx // per_col
            parent = columns[min(col_idx, col_count - 1)]

            band_lf = ttk.LabelFrame(parent, text=band, padding="2")
            band_lf.pack(fill=tk.X, pady=5)

            # 4 channels per row within each band
            for i, freq in enumerate(BAND_TABLE[band]):
                btn_text = f"CH{i+1}\n{freq}"
                btn = tk.Button(band_lf, text=btn_text, width=8, height=2,
                                font=('Helvetica', 8),
                                bg="#f0f0f0", activebackground="#4a90e2",
                                command=lambda f=freq: self.send_command(f"R {f}"))
                btn.grid(row=i // 4, column=i % 4, padx=1, pady=1)

        # 3. Console/Advanced (Bottom)
        bottom_frame = ttk.Frame(root, padding="5")
        bottom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        log_frame = ttk.LabelFrame(bottom_frame, text="Console", padding="5")
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=5, width=50)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        adv_frame = ttk.LabelFrame(bottom_frame, text="I2C", padding="5")
        adv_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.addr_var = tk.StringVar(value="68")
        ttk.Entry(adv_frame, textvariable=self.addr_var, width=4).grid(row=0, column=0)
        ttk.Button(adv_frame, text="Set Addr", command=self.set_address).grid(row=0, column=1)
        ttk.Button(adv_frame, text="Scan I2C", command=self.scan_i2c).grid(row=1, column=0, columnspan=2, pady=2)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def refresh_ports(self):
        self.port_combo['values'] = [port.device for port in serial.tools.list_ports.comports()]

    def toggle_connection(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connect_btn.config(text="Connect")
            self.status_var.set("Disconnected")
            self.log("Disconnected.")
        else:
            try:
                port = self.port_var.get()
                if not port: return
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                self.connect_btn.config(text="Disconnect")
                self.status_var.set("Connected")
                self.log("Connected to " + port)
                threading.Thread(target=self.read_serial, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def read_serial(self):
        while self.ser and self.ser.is_open:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='replace').strip()
                if line: self.root.after(0, self.log, line)
            time.sleep(0.01)

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())
            self.log(">> " + cmd)
        else:
            messagebox.showwarning("Warning", "Not connected.")

    def set_address(self):
        self.send_command(f"A {self.addr_var.get()}")

    def scan_i2c(self):
        self.send_command("S")

if __name__ == "__main__":
    root = tk.Tk()
    app = VTXControllerGUI(root)
    root.mainloop()
