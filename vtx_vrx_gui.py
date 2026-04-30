#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import threading
from vtx_table import BAND_TABLE

class VTXControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VTX/VRX Controller")
        self.ser = None

        # Main Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Connection Section
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="5")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(conn_frame, text="Serial Port:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var)
        self.port_combo['values'] = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3)

        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=1, column=0, columnspan=4, sticky=tk.W)

        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Tab 1: Frequency Control
        freq_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(freq_tab, text="Frequency Control")

        # Band/Channel Selection in Tab
        ttk.Label(freq_tab, text="Band:").grid(row=0, column=0, sticky=tk.W)
        self.band_var = tk.StringVar()
        self.band_combo = ttk.Combobox(freq_tab, textvariable=self.band_var, values=list(BAND_TABLE.keys()), state="readonly")
        self.band_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.band_combo.bind("<<ComboboxSelected>>", self.update_freq_from_table)

        ttk.Label(freq_tab, text="Channel:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.chan_var = tk.StringVar()
        self.chan_combo = ttk.Combobox(freq_tab, textvariable=self.chan_var, values=[str(i) for i in range(1, 9)], state="readonly", width=5)
        self.chan_combo.grid(row=0, column=3, sticky=tk.W)
        self.chan_combo.bind("<<ComboboxSelected>>", self.update_freq_from_table)

        ttk.Label(freq_tab, text="Target Frequency (MHz):").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.freq_var = tk.StringVar(value="1200")
        ttk.Entry(freq_tab, textvariable=self.freq_var).grid(row=1, column=1, sticky=(tk.W, tk.E))

        # Buttons for separate control
        btn_frame = ttk.Frame(freq_tab)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=5)

        ttk.Button(btn_frame, text="Set VTX Frequency", command=self.set_vtx_frequency).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text="Set VRX Frequency", command=self.set_vrx_frequency).grid(row=0, column=1, padx=2)
        ttk.Button(btn_frame, text="Set BOTH", command=self.set_both_frequency).grid(row=0, column=2, padx=2)

        # Tab 2: VTX Power
        power_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(power_tab, text="VTX Power")

        ttk.Label(power_tab, text="Preset Power (mW):").grid(row=0, column=0, columnspan=4, sticky=tk.W)
        power_presets = [25, 200, 400, 600, 1000, 1600]
        for i, p in enumerate(power_presets):
            ttk.Button(power_tab, text=f"{p} mW", command=lambda val=p: self.set_power(val)).grid(row=1 + (i//3), column=i%3, padx=5, pady=5, sticky=(tk.W, tk.E))

        ttk.Label(power_tab, text="Manual Entry (mW):").grid(row=3, column=0, sticky=tk.W, pady=10)
        self.power_var = tk.StringVar(value="25")
        ttk.Entry(power_tab, textvariable=self.power_var, width=10).grid(row=3, column=1, sticky=tk.W)
        ttk.Button(power_tab, text="Set Manual", command=lambda: self.set_power()).grid(row=3, column=2, padx=5)

        # Tab 3: Advanced / I2C
        adv_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(adv_tab, text="Advanced")

        ttk.Label(adv_tab, text="I2C SDA Pin:").grid(row=0, column=0, sticky=tk.W)
        self.sda_var = tk.StringVar(value="21")
        ttk.Entry(adv_tab, textvariable=self.sda_var, width=5).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(adv_tab, text="SCL Pin:").grid(row=0, column=2, sticky=tk.W)
        self.scl_var = tk.StringVar(value="22")
        ttk.Entry(adv_tab, textvariable=self.scl_var, width=5).grid(row=0, column=3, sticky=tk.W)
        ttk.Button(adv_tab, text="Set Pins", command=self.set_i2c_pins).grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(adv_tab, text="VRX I2C Addr:").grid(row=2, column=0, sticky=tk.W)
        self.addr_var = tk.StringVar(value="68")
        ttk.Entry(adv_tab, textvariable=self.addr_var, width=5).grid(row=2, column=1, sticky=tk.W)
        ttk.Button(adv_tab, text="Set Addr", command=self.set_address).grid(row=2, column=2, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Button(adv_tab, text="Scan I2C Bus", command=self.scan_i2c).grid(row=3, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E))

        # Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.log_text = tk.Text(log_frame, height=8, width=60)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set

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
                if not port:
                    messagebox.showwarning("Warning", "Select a port.")
                    return
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                self.connect_btn.config(text="Disconnect")
                self.status_var.set("Connected to " + port)
                self.log("Connected to " + port)
                threading.Thread(target=self.read_serial, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def read_serial(self):
        while self.ser and self.ser.is_open:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    self.root.after(0, self.log, line)
            time.sleep(0.01)

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())
            self.log(">> " + cmd)
        else:
            messagebox.showwarning("Warning", "Not connected.")

    def update_freq_from_table(self, event=None):
        band = self.band_var.get()
        chan = self.chan_var.get()
        if band and chan:
            freq = BAND_TABLE[band][int(chan) - 1]
            self.freq_var.set(str(freq))

    def set_vtx_frequency(self):
        self.send_command(f"V {self.freq_var.get()}")

    def set_vrx_frequency(self):
        self.send_command(f"R {self.freq_var.get()}")

    def set_both_frequency(self):
        self.send_command(f"F {self.freq_var.get()}")

    def set_power(self, val=None):
        if val is not None:
            self.send_command(f"P {val}")
        else:
            self.send_command(f"P {self.power_var.get()}")

    def set_address(self):
        self.send_command(f"A {self.addr_var.get()}")

    def set_i2c_pins(self):
        self.send_command(f"I {self.sda_var.get()} {self.scl_var.get()}")

    def scan_i2c(self):
        self.send_command("S")

if __name__ == "__main__":
    root = tk.Tk()
    app = VTXControllerGUI(root)
    root.mainloop()
