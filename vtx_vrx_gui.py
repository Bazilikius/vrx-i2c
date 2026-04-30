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

        # 2. Main Control Area (Middle) - 3 Columns
        control_frame = ttk.Frame(root, padding="5")
        control_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        control_frame.columnconfigure(0, weight=1) # VTX Freq
        control_frame.columnconfigure(1, weight=1) # VTX Power
        control_frame.columnconfigure(2, weight=3) # VRX Freq (Wide)
        control_frame.rowconfigure(0, weight=1)

        # --- Column 1: VTX Frequency ---
        vtx_freq_lf = ttk.LabelFrame(control_frame, text="VTX Frequency (1.2G)", padding="5")
        vtx_freq_lf.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)
        for i, freq in enumerate(VTX_12G_TABLE):
            btn = ttk.Button(vtx_freq_lf, text=f"{freq} MHz",
                             command=lambda f=freq: self.send_command(f"V {f}"))
            btn.pack(fill=tk.X, pady=2)

        # --- Column 2: VTX Power ---
        vtx_pwr_lf = ttk.LabelFrame(control_frame, text="VTX Power", padding="5")
        vtx_pwr_lf.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)
        power_levels = [25, 200, 400, 600, 1000, 1600]
        for p in power_levels:
            btn = ttk.Button(vtx_pwr_lf, text=f"{p} mW",
                             command=lambda val=p: self.send_command(f"P {val}"))
            btn.pack(fill=tk.X, pady=2)

        # --- Column 3: VRX Frequency (Scrollable) ---
        vrx_freq_lf = ttk.LabelFrame(control_frame, text="VRX Frequency Select", padding="5")
        vrx_freq_lf.grid(row=0, column=2, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)

        canvas = tk.Canvas(vrx_freq_lf)
        scrollbar = ttk.Scrollbar(vrx_freq_lf, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate VRX buttons from BAND_TABLE
        row_idx = 0
        for band, freqs in BAND_TABLE.items():
            ttk.Label(scroll_frame, text=band, font=('Helvetica', 10, 'bold')).grid(row=row_idx, column=0, columnspan=4, sticky=tk.W, pady=(5,0))
            row_idx += 1
            for i, freq in enumerate(freqs):
                btn_text = f"CH{i+1}\n{freq}"
                btn = tk.Button(scroll_frame, text=btn_text, width=8, height=2,
                                bg="#e1e1e1", activebackground="#4a90e2",
                                command=lambda f=freq: self.send_command(f"R {f}"))
                btn.grid(row=row_idx + (i // 4), column=i % 4, padx=2, pady=2)
            row_idx += 2

        # 3. Console/Advanced (Bottom)
        bottom_frame = ttk.Frame(root, padding="5")
        bottom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        # Log
        log_frame = ttk.LabelFrame(bottom_frame, text="Console", padding="5")
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=6, width=50)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Advanced Tiny Frame
        adv_frame = ttk.LabelFrame(bottom_frame, text="I2C", padding="5")
        adv_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.addr_var = tk.StringVar(value="68")
        ttk.Entry(adv_frame, textvariable=self.addr_var, width=4).grid(row=0, column=0)
        ttk.Button(adv_frame, text="Set", width=4, command=self.set_address).grid(row=0, column=1)
        ttk.Button(adv_frame, text="Scan", width=8, command=self.scan_i2c).grid(row=1, column=0, columnspan=2, pady=2)

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
