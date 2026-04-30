#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import threading
import json
import os
import math
from vtx_table import BAND_TABLE, VTX_12G_TABLE
import tkintermapview

class VTXControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VTX/VRX Pro Controller with Map")
        self.ser = None
        self.marker = None
        self.range_graphics = [] # Store circles and lines
        self.azimuth_labels = []
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        self.fav_vtx_buttons = []
        self.fav_vrx_buttons = []

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

        # 2. Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # --- Tab 1: Controls ---
        control_tab = ttk.Frame(self.notebook)
        self.notebook.add(control_tab, text="Hardware Controls")

        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=5)
        control_tab.rowconfigure(0, weight=1)

        # VTX Side
        vtx_side_frame = ttk.Frame(control_tab)
        vtx_side_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        vtx_freq_lf = ttk.LabelFrame(vtx_side_frame, text="VTX Frequency (1.2G)", padding="5")
        vtx_freq_lf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for freq in VTX_12G_TABLE:
            btn = ttk.Button(vtx_freq_lf, text=f"{freq} MHz",
                             command=lambda f=freq: self.send_command(f"V {f}"))
            btn.pack(fill=tk.X, pady=1)
            btn.bind("<Button-3>", lambda e, f=freq: self.add_to_favorites("vtx", f))

        vtx_pwr_lf = ttk.LabelFrame(vtx_side_frame, text="VTX Power", padding="5")
        vtx_pwr_lf.pack(fill=tk.X, padx=5, pady=5)
        power_levels = [25, 200, 400, 600, 1000, 1600]
        for p in power_levels:
            btn = ttk.Button(vtx_pwr_lf, text=f"{p} mW",
                             command=lambda val=p: self.send_command(f"P {val}"))
            btn.pack(fill=tk.X, pady=1)

        # VRX Grid (3 Columns)
        vrx_main_lf = ttk.LabelFrame(control_tab, text="VRX Channels", padding="5")
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

        bands = list(BAND_TABLE.keys())
        col_count = 3
        per_col = (len(bands) + col_count - 1) // col_count

        for i in range(col_count):
            col_frame = ttk.Frame(scroll_frame)
            col_frame.grid(row=0, column=i, sticky=tk.N, padx=10)
            for j in range(per_col):
                idx = i * per_col + j
                if idx < len(bands):
                    band = bands[idx]
                    band_lf = ttk.LabelFrame(col_frame, text=band, padding="2")
                    band_lf.pack(fill=tk.X, pady=5)
                    for k, freq in enumerate(BAND_TABLE[band]):
                        btn = tk.Button(band_lf, text=f"CH{k+1}\n{freq}", width=8, height=2,
                                        font=('Helvetica', 8), bg="#f0f0f0",
                                        command=lambda f=freq: self.send_command(f"R {f}"))
                        btn.grid(row=k // 4, column=k % 4, padx=1, pady=1)
                        btn.bind("<Button-3>", lambda e, f=freq: self.add_to_favorites("vrx", f))

        # --- Tab 2: Map ---
        map_tab = ttk.Frame(self.notebook)
        self.notebook.add(map_tab, text="Satellite Map")

        # Map Sidebar for Favorites
        self.map_sidebar = ttk.Frame(map_tab, padding="5", width=150)
        self.map_sidebar.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(self.map_sidebar, text="Favorites", font=('Helvetica', 10, 'bold')).pack(pady=5)

        self.fav_vtx_lf = ttk.LabelFrame(self.map_sidebar, text="VTX", padding="2")
        self.fav_vtx_lf.pack(fill=tk.X, pady=5)
        self.fav_vrx_lf = ttk.LabelFrame(self.map_sidebar, text="VRX", padding="2")
        self.fav_vrx_lf.pack(fill=tk.X, pady=5)

        ttk.Button(self.map_sidebar, text="Clear Favs", command=self.clear_favorites).pack(side=tk.BOTTOM, fill=tk.X)

        map_main_frame = ttk.Frame(map_tab)
        map_main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        map_controls = ttk.Frame(map_main_frame, padding="5")
        map_controls.pack(fill=tk.X)

        ttk.Label(map_controls, text="Lat:").pack(side=tk.LEFT)
        self.lat_var = tk.StringVar(value="50.4501")
        ttk.Entry(map_controls, textvariable=self.lat_var, width=12).pack(side=tk.LEFT, padx=5)

        ttk.Label(map_controls, text="Lon:").pack(side=tk.LEFT)
        self.lon_var = tk.StringVar(value="30.5234")
        ttk.Entry(map_controls, textvariable=self.lon_var, width=12).pack(side=tk.LEFT, padx=5)

        ttk.Button(map_controls, text="Update/Refresh Map", command=self.update_map_marker).pack(side=tk.LEFT, padx=5)
        ttk.Label(map_controls, text="(Right-click map to set position)", foreground="gray").pack(side=tk.LEFT, padx=10)

        # Map View
        self.map_widget = tkintermapview.TkinterMapView(map_main_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        # Use Google Hybrid (y) for satellite + labels (cities, roads)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", max_zoom=22)

        # Initialize default position and draw overlay
        self.root.after(100, self.update_map_marker)

        self.map_widget.add_right_click_menu_command(label="Set System Location", command=self.add_marker_event, pass_coords=True)

        self.update_favorites_display()

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

        adv_frame = ttk.LabelFrame(bottom_frame, text="I2C/Config", padding="5")
        adv_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.addr_var = tk.StringVar(value="68")
        ttk.Entry(adv_frame, textvariable=self.addr_var, width=4).grid(row=0, column=0)
        ttk.Button(adv_frame, text="Addr", command=self.set_address).grid(row=0, column=1)
        ttk.Button(adv_frame, text="Scan", command=self.scan_i2c).grid(row=1, column=0, columnspan=2, pady=2)

    def add_marker_event(self, coords):
        self.lat_var.set(f"{coords[0]:.6f}")
        self.lon_var.set(f"{coords[1]:.6f}")
        self.update_map_marker()

    def update_map_marker(self):
        try:
            # Parse coordinates (handle comma/dot)
            l_raw = str(self.lat_var.get()).replace(',', '.')
            o_raw = str(self.lon_var.get()).replace(',', '.')
            lat, lon = float(l_raw), float(o_raw)

            # Full Reset
            self.map_widget.delete_all_marker()
            self.map_widget.delete_all_path()
            self.map_widget.set_position(lat, lon)
            self.map_widget.set_zoom(12)

            # Draw Base Marker
            self.map_widget.set_marker(lat, lon, text="SYSTEM BASE",
                                      text_color="yellow", marker_color_circle="red")

            # Draw Tactical Overlay
            self.draw_enhanced_range_graphics(lat, lon)
            self.log(f"Map: Center updated to {lat}, {lon}")
        except Exception as e:
            self.log(f"Map Update Error: {e}")

    def draw_enhanced_range_graphics(self, lat, lon):
        try:
            R = 6371.0 # Earth radius in km
            lat_rad, lon_rad = math.radians(lat), math.radians(lon)

            # 1. Range Rings (5, 10, 15 km)
            for r_km in [5, 10, 15]:
                pts = []
                d_r = r_km / R
                for i in range(0, 361, 5):
                    br = math.radians(i)
                    p_lat = math.asin(math.sin(lat_rad)*math.cos(d_r) + math.cos(lat_rad)*math.sin(d_r)*math.cos(br))
                    p_lon = lon_rad + math.atan2(math.sin(br)*math.sin(d_r)*math.cos(lat_rad),
                                                math.cos(d_r)-math.sin(lat_rad)*math.sin(p_lat))
                    pts.append((math.degrees(p_lat), math.degrees(p_lon)))
                self.map_widget.set_path(pts, color="white", width=3)

            # 2. Azimuth Radials and Labels
            for angle in range(0, 360, 30):
                br = math.radians(angle)
                d_r = 15.0 / R

                # Draw Radial Line
                e_lat = math.asin(math.sin(lat_rad)*math.cos(d_r) + math.cos(lat_rad)*math.sin(d_r)*math.cos(br))
                e_lon = lon_rad + math.atan2(math.sin(br)*math.sin(d_r)*math.cos(lat_rad),
                                            math.cos(d_r)-math.sin(lat_rad)*math.sin(e_lat))
                self.map_widget.set_path([(lat, lon), (math.degrees(e_lat), math.degrees(e_lon))],
                                         color="white", width=2)

                # Label at 17.0 km
                d_lbl = 17.0 / R
                l_lat = math.asin(math.sin(lat_rad)*math.cos(d_lbl) + math.cos(lat_rad)*math.sin(d_lbl)*math.cos(br))
                l_lon = lon_rad + math.atan2(math.sin(br)*math.sin(d_lbl)*math.cos(lat_rad),
                                            math.cos(d_lbl)-math.sin(lat_rad)*math.sin(l_lat))

                txt = f"{angle}°"
                if angle == 0: txt = "N"
                elif angle == 90: txt = "E"
                elif angle == 180: txt = "S"
                elif angle == 270: txt = "W"

                self.map_widget.set_marker(math.degrees(l_lat), math.degrees(l_lon), text=txt,
                                          font=("Arial", 18, "bold"), text_color="white",
                                          marker_color_circle="black", icon_radius=3)

            # 3. Distance Labels along 165° bearing
            br_dist = math.radians(165)
            for r_km in [5, 10, 15]:
                d_r = (r_km - 0.5) / R # Slightly inside ring
                l_lat = math.asin(math.sin(lat_rad)*math.cos(d_r) + math.cos(lat_rad)*math.sin(d_r)*math.cos(br_dist))
                l_lon = lon_rad + math.atan2(math.sin(br_dist)*math.sin(d_r)*math.cos(lat_rad),
                                            math.cos(d_r)-math.sin(lat_rad)*math.sin(l_lat))
                self.map_widget.set_marker(math.degrees(l_lat), math.degrees(l_lon), text=f"{r_km}km",
                                          font=("Arial", 14, "bold"), text_color="white",
                                          marker_color_circle="black", icon_radius=3)
        except Exception as e:
            self.log(f"Overlay Error: {e}")

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except:
                return {"vtx": [], "vrx": []}
        return {"vtx": [], "vrx": []}

    def save_favorites(self):
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorites, f)
        self.update_favorites_display()

    def update_favorites_display(self):
        for btn in self.fav_vtx_buttons: btn.destroy()
        for btn in self.fav_vrx_buttons: btn.destroy()
        self.fav_vtx_buttons = []
        self.fav_vrx_buttons = []

        for freq in self.favorites["vtx"]:
            btn = ttk.Button(self.fav_vtx_lf, text=f"{freq}", width=10,
                             command=lambda f=freq: self.send_command(f"V {f}"))
            btn.pack(pady=1)
            self.fav_vtx_buttons.append(btn)

        for freq in self.favorites["vrx"]:
            btn = ttk.Button(self.fav_vrx_lf, text=f"{freq}", width=10,
                             command=lambda f=freq: self.send_command(f"R {f}"))
            btn.pack(pady=1)
            self.fav_vrx_buttons.append(btn)

    def clear_favorites(self):
        if messagebox.askyesno("Confirm", "Clear all favorites?"):
            self.favorites = {"vtx": [], "vrx": []}
            self.save_favorites()

    def add_to_favorites(self, type, freq):
        if freq not in self.favorites[type]:
            self.favorites[type].append(freq)
            self.favorites[type].sort()
            self.save_favorites()
            self.log(f"Added {freq} MHz to {type.upper()} favorites")

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
