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
        ttk.Label(main_frame, text="Serial Port:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(main_frame, textvariable=self.port_var)
        self.port_combo['values'] = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.refresh_btn = ttk.Button(main_frame, text="Refresh", command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5)

        self.connect_btn = ttk.Button(main_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3)

        # Status
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(main_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=1, column=1, columnspan=3, sticky=tk.W)

        # Control Section
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)

        # I2C Pins
        ttk.Label(main_frame, text="I2C SDA Pin:").grid(row=3, column=0, sticky=tk.W)
        self.sda_var = tk.StringVar(value="21")
        ttk.Entry(main_frame, textvariable=self.sda_var, width=5).grid(row=3, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="SCL Pin:").grid(row=3, column=2, sticky=tk.W)
        self.scl_var = tk.StringVar(value="22")
        ttk.Entry(main_frame, textvariable=self.scl_var, width=5).grid(row=3, column=3, sticky=tk.W)

        ttk.Button(main_frame, text="Set I2C Pins", command=self.set_i2c_pins).grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)

        # Band/Channel Selection
        ttk.Label(main_frame, text="Band:").grid(row=6, column=0, sticky=tk.W)
        self.band_var = tk.StringVar()
        self.band_combo = ttk.Combobox(main_frame, textvariable=self.band_var, values=list(BAND_TABLE.keys()), state="readonly")
        self.band_combo.grid(row=6, column=1, sticky=(tk.W, tk.E))
        self.band_combo.bind("<<ComboboxSelected>>", self.update_freq_from_table)

        ttk.Label(main_frame, text="Channel:").grid(row=6, column=2, sticky=tk.W, padx=5)
        self.chan_var = tk.StringVar()
        self.chan_combo = ttk.Combobox(main_frame, textvariable=self.chan_var, values=[str(i) for i in range(1, 9)], state="readonly", width=5)
        self.chan_combo.grid(row=6, column=3, sticky=tk.W)
        self.chan_combo.bind("<<ComboboxSelected>>", self.update_freq_from_table)

        # Frequency
        ttk.Label(main_frame, text="Frequency (MHz):").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.freq_var = tk.StringVar(value="1200")
        ttk.Entry(main_frame, textvariable=self.freq_var).grid(row=7, column=1, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="Set Frequency", command=self.set_frequency).grid(row=7, column=2, columnspan=2, sticky=(tk.W, tk.E), padx=5)

        # Power
        ttk.Label(main_frame, text="Power (mW):").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.power_var = tk.StringVar(value="25")
        ttk.Entry(main_frame, textvariable=self.power_var).grid(row=8, column=1, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="Set Power", command=self.set_power).grid(row=8, column=2, columnspan=2, sticky=(tk.W, tk.E), padx=5)

        # I2C Address
        ttk.Label(main_frame, text="VRX I2C Addr (Hex):").grid(row=9, column=0, sticky=tk.W)
        self.addr_var = tk.StringVar(value="68")
        ttk.Entry(main_frame, textvariable=self.addr_var).grid(row=9, column=1, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="Set Address", command=self.set_address).grid(row=9, column=2, columnspan=2, sticky=(tk.W, tk.E), padx=5)

        # Scanner
        ttk.Button(main_frame, text="Scan I2C Bus", command=self.scan_i2c).grid(row=10, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E))

        # Log Output
        ttk.Label(main_frame, text="Console:").grid(row=11, column=0, sticky=tk.W)
        self.log_text = tk.Text(main_frame, height=10, width=50)
        self.log_text.grid(row=12, column=0, columnspan=4, sticky=(tk.W, tk.E))

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=12, column=4, sticky=(tk.N, tk.S))
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
            self.log("Disconnected from " + self.port_var.get())
        else:
            try:
                port = self.port_var.get()
                if not port:
                    messagebox.showwarning("Warning", "Please select a serial port.")
                    return
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                self.connect_btn.config(text="Disconnect")
                self.status_var.set("Connected to " + port)
                self.log("Connected to " + port)

                # Start reading thread
                self.stop_thread = False
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
            messagebox.showwarning("Warning", "Not connected to ESP32.")

    def update_freq_from_table(self, event=None):
        band = self.band_var.get()
        chan = self.chan_var.get()
        if band and chan:
            freq = BAND_TABLE[band][int(chan) - 1]
            self.freq_var.set(str(freq))

    def set_frequency(self):
        self.send_command(f"F {self.freq_var.get()}")

    def set_power(self):
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
