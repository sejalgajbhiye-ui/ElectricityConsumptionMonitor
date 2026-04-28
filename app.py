import hashlib
import math
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mysql.connector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mysql.connector import Error
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas


DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "shru@1234"
DB_NAME = "electricity_app"

APPLIANCE_WATTAGE = {
    "Fan": 75,
    "LED Bulb": 9,
    "Tube Light": 40,
    "TV": 100,
    "Refrigerator": 200,
    "AC": 1500,
    "Washing Machine": 500,
}

APPLIANCE_EFFICIENCY = {
    "AC": 0.6,
    "Fan": 0.9,
    "TV": 0.8,
    "LED Bulb": 1.0,
    "Tube Light": 1.0,
    "Refrigerator": 0.85,
    "Washing Machine": 0.75,
}

FIXED_CHARGE = 115.0
ELECTRICITY_DUTY_RATE = 0.21
CO2_FACTOR = 0.45
TREE_OFFSET = 21.0
HIGH_USAGE_THRESHOLD = 200.0
HIGH_APPLIANCE_THRESHOLD = 150.0


def get_connection():
    """Create a connection to the application database."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def initialize_database():
    """Create the database and users table if they do not already exist."""
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password VARCHAR(255)
            )
            """
        )
        connection.commit()
        return True
    except Error as error:
        messagebox.showerror("Database Error", f"Could not initialize database.\n{error}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def hash_password(password):
    """Hash the password with SHA-256 before saving or comparing it."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register(username, password):
    """Register a new user with a hashed password."""
    if not username.strip() or not password.strip():
        messagebox.showerror("Register", "Username and password are required.")
        return False

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username.strip(), hash_password(password)),
        )
        connection.commit()
        messagebox.showinfo("Register", "Registration successful. You can now log in.")
        return True
    except mysql.connector.IntegrityError:
        messagebox.showerror("Register", "This username already exists. Please choose another one.")
        return False
    except Error as error:
        messagebox.showerror("Register", f"Could not register user.\n{error}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def login(username, password):
    """Check whether a user exists and the hashed password matches."""
    if not username.strip() or not password.strip():
        return False

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE username = %s",
            (username.strip(),),
        )
        result = cursor.fetchone()
        if not result:
            return False
        return result[0] == hash_password(password)
    except Error:
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, _event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            bg="#fbf7d8",
            fg="#2d4137",
            relief="solid",
            bd=1,
            padx=8,
            pady=4,
            font=("Segoe UI", 9),
        )
        label.pack()

    def hide_tip(self, _event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - Electricity Consumption Monitor")
        self.root.geometry("460x360")
        self.root.minsize(420, 330)
        self.root.configure(bg="#eef5f1")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        wrapper = ttk.Frame(self.root, padding=22)
        wrapper.pack(fill="both", expand=True)

        card = ttk.Frame(wrapper, padding=18)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Electricity Consumption Monitor", font=("Segoe UI", 19, "bold"), foreground="#173f35").pack(anchor="w")
        ttk.Label(
            card,
            text="Log in or register to access the local desktop electricity dashboard.",
            font=("Segoe UI", 10),
            foreground="#55766a",
        ).pack(anchor="w", pady=(4, 18))

        ttk.Label(card, text="Username").pack(anchor="w")
        username_entry = ttk.Entry(card, textvariable=self.username_var)
        username_entry.pack(fill="x", pady=(6, 14))

        ttk.Label(card, text="Password").pack(anchor="w")
        self.password_entry = ttk.Entry(card, textvariable=self.password_var, show="*")
        self.password_entry.pack(fill="x", pady=(6, 8))

        ttk.Checkbutton(
            card,
            text="Show Password",
            variable=self.show_password_var,
            command=self.toggle_password,
        ).pack(anchor="w", pady=(0, 18))

        button_row = ttk.Frame(card)
        button_row.pack(fill="x")
        button_row.columnconfigure((0, 1), weight=1)

        login_button = ttk.Button(button_row, text="Login", command=self.handle_login)
        login_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        register_button = ttk.Button(button_row, text="Register", command=self.handle_register)
        register_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ToolTip(login_button, "Check username and password, then open the main monitor.")
        ToolTip(register_button, "Create a new user in the MySQL users table.")

    def toggle_password(self):
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def handle_register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        register(username, password)

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            messagebox.showerror("Login", "Please enter both username and password.")
            return

        if login(username, password):
            self.root.destroy()
            launch_main_app(username)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


class ElectricityConsumptionMonitor:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        self.root.title("Electricity Consumption Monitor")
        self.root.geometry("1340x900")
        self.root.minsize(1180, 760)
        self.root.configure(bg="#eef5f1")

        self.mode_var = tk.StringVar(value="appliance")
        self.appliance_var = tk.StringVar(value="Fan")
        self.power_var = tk.StringVar(value=str(APPLIANCE_WATTAGE["Fan"]))
        self.hours_var = tk.StringVar(value="1")
        self.days_var = tk.StringVar(value="30")
        self.inverter_ac_var = tk.BooleanVar(value=False)
        self.realistic_units_var = tk.StringVar(value="0.00 kWh")
        self.appliance_units_var = self.realistic_units_var

        self.current_reading_var = tk.StringVar(value="0")
        self.previous_reading_var = tk.StringVar(value="0")
        self.reading_units_var = tk.StringVar(value="0.00 units")

        self.previous_month_units_var = tk.StringVar(value="0")

        self.total_units_var = tk.StringVar(value="0.00 units")
        self.energy_charge_var = tk.StringVar(value="Rs 0.00")
        self.duty_var = tk.StringVar(value="Rs 0.00")
        self.fixed_charge_var = tk.StringVar(value=f"Rs {FIXED_CHARGE:.2f}")
        self.final_bill_var = tk.StringVar(value="Rs 0.00")
        self.amount_words_var = tk.StringVar(value="Zero rupees only")

        self.highest_appliance_var = tk.StringVar(value="No appliance data yet")
        self.usage_change_var = tk.StringVar(value="Enter previous month units for comparison")
        self.insight_message_var = tk.StringVar(value="Add appliance data or meter readings to generate insights")

        self.co2_var = tk.StringVar(value="0.00 kg CO2")
        self.trees_var = tk.StringVar(value="0.00 trees")
        self.eco_message_var = tk.StringVar(value="Low impact")

        self.appliance_rows = []
        self.chart_canvases = []
        self.warning_state = {"high_units": False, "high_appliance": False}
        self.meter_refresh_job = None

        self._configure_style()
        self._build_layout()
        self._bind_events()
        self.update_mode_view()
        self.refresh_all()

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#eef5f1")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#eef5f1", foreground="#173f35", font=("Segoe UI", 22, "bold"))
        style.configure("SubHeader.TLabel", background="#eef5f1", foreground="#55766a", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#dfece6", foreground="#153a31", font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background="#ffffff", foreground="#28493f", font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="#ffffff", foreground="#153a31", font=("Segoe UI", 10, "bold"))
        style.configure("Summary.TLabel", background="#ffffff", foreground="#0f5132", font=("Segoe UI", 16, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#5a7569", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))

    def _build_layout(self):
        shell = ttk.Frame(self.root, style="App.TFrame")
        shell.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(shell, bg="#eef5f1", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        wrapper = ttk.Frame(self.canvas, style="App.TFrame", padding=18)
        self.canvas_window = self.canvas.create_window((0, 0), window=wrapper, anchor="nw")
        wrapper.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        header = ttk.Frame(wrapper, style="App.TFrame")
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="Electricity Consumption Monitor", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=f"Welcome, {self.username}. A bill-style desktop application with appliance tracking, meter mode, billing, insights, CO2 impact, and exports.",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        top_actions = ttk.Frame(wrapper, style="App.TFrame")
        top_actions.pack(fill="x", pady=(0, 10))
        logout_button = ttk.Button(top_actions, text="Logout", command=self.logout)
        logout_button.pack(side="right")
        ToolTip(logout_button, "Close the dashboard and return to the login window.")

        mode_card = self._make_card(wrapper)
        mode_card.pack(fill="x", pady=(0, 10))
        ttk.Label(mode_card, text="MODE SELECTION", style="Section.TLabel").pack(fill="x", pady=(0, 10))
        mode_row = ttk.Frame(mode_card, style="Card.TFrame")
        mode_row.pack(fill="x")
        ttk.Radiobutton(mode_row, text="Appliance Mode", variable=self.mode_var, value="appliance", command=self.update_mode_view).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mode_row, text="Meter Reading Mode", variable=self.mode_var, value="meter", command=self.update_mode_view).pack(side="left")

        body = ttk.Frame(wrapper, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        self.input_card = self._make_card(body)
        self.input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.billing_card = self._make_card(body)
        self.billing_card.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        self.impact_card = self._make_card(body)
        self.impact_card.grid(row=1, column=1, sticky="nsew")
        self.tips_card = self._make_card(body)
        self.tips_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.chart_card = self._make_card(body)
        self.chart_card.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

        self._build_input_section()
        self._build_billing_section()
        self._build_environment_section()
        self._build_tips_section()
        self._build_chart_section()

    def _make_card(self, parent):
        return ttk.Frame(parent, style="Card.TFrame", padding=14)

    def _build_input_section(self):
        ttk.Label(self.input_card, text="APPLIANCE-BASED INPUT", style="Section.TLabel").pack(fill="x", pady=(0, 10))

        self.appliance_mode_frame = ttk.Frame(self.input_card, style="Card.TFrame")
        self.appliance_mode_frame.pack(fill="x")
        self.appliance_mode_frame.columnconfigure((0, 1, 2, 3, 4), weight=1)

        appliance_headers = [
            "Appliance",
            "Power (W)",
            "Hours / Day",
            "Days",
            "Realistic Units",
        ]
        for column, text in enumerate(appliance_headers):
            self._table_cell(self.appliance_mode_frame, 0, column, text, header=True)

        self.appliance_combo = ttk.Combobox(
            self.appliance_mode_frame,
            textvariable=self.appliance_var,
            values=list(APPLIANCE_WATTAGE.keys()),
            state="readonly",
            width=18,
        )
        self.appliance_combo.grid(row=1, column=0, sticky="nsew")
        self.power_entry = self._entry_cell(self.appliance_mode_frame, 1, 1, self.power_var)
        self.hours_spinbox = self._spinbox_cell(self.appliance_mode_frame, 1, 2, self.hours_var, 0.5, 24, 0.5)
        self.days_spinbox = self._spinbox_cell(self.appliance_mode_frame, 1, 3, self.days_var, 1, 365, 1)
        self._table_cell(self.appliance_mode_frame, 1, 4, self.realistic_units_var, is_var=True)

        ac_options_row = ttk.Frame(self.input_card, style="Card.TFrame")
        ac_options_row.pack(fill="x", pady=(8, 0))
        self.inverter_check = ttk.Checkbutton(
            ac_options_row,
            text="Inverter AC",
            variable=self.inverter_ac_var,
            command=self.update_appliance_preview,
        )
        self.inverter_check.pack(side="left")
        ToolTip(
            self.inverter_check,
            "For AC only: after 2 hours, inverter AC uses 40% power and non-inverter AC uses 60%.",
        )

        appliance_buttons = ttk.Frame(self.input_card, style="Card.TFrame")
        appliance_buttons.pack(fill="x", pady=(10, 12))
        appliance_buttons.columnconfigure((0, 1, 2), weight=1)
        add_button = ttk.Button(appliance_buttons, text="Add Appliance", command=self.add_appliance)
        add_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        remove_button = ttk.Button(appliance_buttons, text="Remove Selected", command=self.remove_selected)
        remove_button.grid(row=0, column=1, sticky="ew", padx=6)
        reset_button = ttk.Button(appliance_buttons, text="Reset All", command=self.reset_all)
        reset_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        ToolTip(add_button, "Add the current appliance setup to the monthly list.")
        ToolTip(remove_button, "Remove the selected appliance row from the table.")
        ToolTip(reset_button, "Clear appliance data, meter values, and all totals.")

        columns = ("appliance", "power", "hours", "days", "units")
        self.tree = ttk.Treeview(self.input_card, columns=columns, show="headings", height=9)
        self.tree.pack(fill="both", expand=True)
        headings = {
            "appliance": "Appliance",
            "power": "Power (W)",
            "hours": "Hours / Day",
            "days": "Days",
            "units": "Realistic Units",
        }
        widths = {
            "appliance": 180,
            "power": 110,
            "hours": 110,
            "days": 90,
            "units": 130,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="center")

        ttk.Label(self.input_card, text="CURRENT CONSUMPTION DETAILS", style="Section.TLabel").pack(fill="x", pady=(14, 10))

        self.meter_mode_frame = ttk.Frame(self.input_card, style="Card.TFrame")
        self.meter_mode_frame.pack(fill="x")
        self.meter_mode_frame.columnconfigure((0, 1, 2), weight=1)

        meter_headers = ["Current Reading", "Previous Reading", "Total Consumption"]
        for column, text in enumerate(meter_headers):
            self._table_cell(self.meter_mode_frame, 0, column, text, header=True)

        self.current_entry = self._entry_cell(self.meter_mode_frame, 1, 0, self.current_reading_var)
        self.previous_entry = self._entry_cell(self.meter_mode_frame, 1, 1, self.previous_reading_var)
        self._table_cell(self.meter_mode_frame, 1, 2, self.reading_units_var, is_var=True)

        comparison_frame = ttk.Frame(self.input_card, style="Card.TFrame")
        comparison_frame.pack(fill="x", pady=(14, 0))
        ttk.Label(comparison_frame, text="Previous Month Units", style="Field.TLabel").pack(side="left")
        self.previous_month_entry = ttk.Entry(comparison_frame, textvariable=self.previous_month_units_var, width=14, justify="center")
        self.previous_month_entry.pack(side="left", padx=(10, 0))
        ToolTip(self.previous_month_entry, "Enter last month's total units to compare increase or decrease.")

    def _build_billing_section(self):
        ttk.Label(self.billing_card, text="BILLING DETAILS", style="Section.TLabel").pack(fill="x", pady=(0, 10))

        slab_frame = ttk.Frame(self.billing_card, style="Card.TFrame")
        slab_frame.pack(fill="x")
        slab_frame.columnconfigure((0, 1, 2), weight=1)

        headers = ["Units Consumed", "Rate Per Unit", "Charges"]
        for column, text in enumerate(headers):
            self._table_cell(slab_frame, 0, column, text, header=True)

        self.slab_1_var = tk.StringVar(value="Rs 0.00")
        self.slab_2_var = tk.StringVar(value="Rs 0.00")
        self.slab_3_var = tk.StringVar(value="Rs 0.00")
        slabs = [
            ("0-100 units", "Rs 3.00", self.slab_1_var),
            ("101-200 units", "Rs 5.00", self.slab_2_var),
            ("Above 200 units", "Rs 8.00", self.slab_3_var),
        ]
        for row_index, (name, rate, variable) in enumerate(slabs, start=1):
            self._table_cell(slab_frame, row_index, 0, name)
            self._table_cell(slab_frame, row_index, 1, rate)
            self._table_cell(slab_frame, row_index, 2, variable, is_var=True)

        summary = ttk.Frame(self.billing_card, style="Card.TFrame")
        summary.pack(fill="x", pady=(14, 10))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        self._summary_row(summary, 0, "Total Units", self.total_units_var)
        self._summary_row(summary, 1, "Energy Charges", self.energy_charge_var)
        self._summary_row(summary, 2, "Electricity Duty (21%)", self.duty_var)
        self._summary_row(summary, 3, "Fixed Charge", self.fixed_charge_var)
        self._summary_row(summary, 4, "Final Bill Amount", self.final_bill_var, emphasize=True)
        self._summary_row(summary, 5, "Amount in Words", self.amount_words_var)

        ttk.Label(self.billing_card, text="SMART INSIGHTS", style="Section.TLabel").pack(fill="x", pady=(6, 10))
        insight_frame = ttk.Frame(self.billing_card, style="Card.TFrame")
        insight_frame.pack(fill="x")
        self._summary_row(insight_frame, 0, "Highest Consuming Appliance", self.highest_appliance_var)
        self._summary_row(insight_frame, 1, "Insight", self.insight_message_var)

    def _build_environment_section(self):
        ttk.Label(self.impact_card, text="ENVIRONMENTAL IMPACT", style="Section.TLabel").pack(fill="x", pady=(0, 10))

        info_frame = ttk.Frame(self.impact_card, style="Card.TFrame")
        info_frame.pack(fill="x")
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        self._summary_row(info_frame, 0, "CO2 Emission", self.co2_var)
        self._summary_row(info_frame, 1, "Trees Required", self.trees_var)
        self._summary_row(info_frame, 2, "Eco Message", self.eco_message_var, emphasize=True)

        note = "Environmental estimate uses 1 kWh ~= 0.45 kg CO2 and 1 tree ~= 21 kg CO2 per year."
        ttk.Label(self.impact_card, text=note, style="Muted.TLabel", wraplength=360, justify="left").pack(anchor="w", pady=(12, 0))

    def _build_tips_section(self):
        ttk.Label(self.tips_card, text="REFERENCE & ENERGY TIPS", style="Section.TLabel").pack(fill="x", pady=(0, 10))

        wattage_frame = ttk.LabelFrame(self.tips_card, text="Typical Wattage Reference", padding=12)
        wattage_frame.pack(fill="x", pady=(0, 10))
        wattage_text = "\n".join(f"{name}: {wattage}W" for name, wattage in APPLIANCE_WATTAGE.items())
        ttk.Label(wattage_frame, text=wattage_text, style="Field.TLabel", justify="left").pack(anchor="w")

        tips_frame = ttk.LabelFrame(self.tips_card, text="Energy Saving Tips", padding=12)
        tips_frame.pack(fill="x", pady=(0, 10))
        tips_text = (
            "1. Reduce AC usage during peak summer hours.\n"
            "2. Replace old bulbs with LED lights.\n"
            "3. Avoid standby power loss from idle devices.\n"
            "4. Run washing machines with full loads.\n"
            "5. Track high-consuming appliances every month."
        )
        ttk.Label(tips_frame, text=tips_text, style="Muted.TLabel", justify="left").pack(anchor="w")

        export_frame = ttk.LabelFrame(self.tips_card, text="Export Options", padding=12)
        export_frame.pack(fill="x")
        export_buttons = ttk.Frame(export_frame, style="Card.TFrame")
        export_buttons.pack(fill="x")
        export_buttons.columnconfigure(0, weight=1)
        pdf_button = ttk.Button(export_buttons, text="Export PDF Bill", command=self.export_pdf)
        pdf_button.grid(row=0, column=0, sticky="ew")
        ToolTip(pdf_button, "Export a clean electricity bill PDF using reportlab.")

    def _build_chart_section(self):
        ttk.Label(self.chart_card, text="CONSUMPTION VISUALIZATION", style="Section.TLabel").pack(fill="x", pady=(0, 10))

        chart_wrap = ttk.Frame(self.chart_card, style="Card.TFrame")
        chart_wrap.pack(fill="both", expand=True, pady=(0, 4))
        chart_wrap.columnconfigure((0, 1), weight=1)
        chart_wrap.rowconfigure((0, 1), weight=1)

        self.chart_hosts = []
        chart_titles = [
            ("Top Energy Consuming Appliances", 0, 0),
            ("Consumption Distribution", 0, 1),
            ("Bill Breakdown", 1, 0),
            ("CO2 Distribution", 1, 1),
        ]
        for title, row, column in chart_titles:
            frame = ttk.LabelFrame(chart_wrap, text=title, padding=8)
            frame.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
            host = ttk.Frame(frame, style="Card.TFrame")
            host.pack(fill="both", expand=True)
            self.chart_hosts.append(host)

    def _table_cell(self, parent, row, column, value, header=False, is_var=False):
        frame = tk.Frame(
            parent,
            bg="#d8e6df" if header else "#ffffff",
            highlightbackground="#88a59a",
            highlightthickness=1,
            bd=0,
        )
        frame.grid(row=row, column=column, sticky="nsew")
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(column, weight=1)

        if is_var:
            label = ttk.Label(frame, textvariable=value, style="Value.TLabel", anchor="center")
        else:
            style = "Section.TLabel" if header else "Field.TLabel"
            label = ttk.Label(frame, text=value, style=style, anchor="center", justify="center")
        label.pack(fill="both", expand=True, padx=8, pady=10)

    def _entry_cell(self, parent, row, column, variable):
        frame = tk.Frame(parent, bg="#ffffff", highlightbackground="#88a59a", highlightthickness=1, bd=0)
        frame.grid(row=row, column=column, sticky="nsew")
        entry = ttk.Entry(frame, textvariable=variable, justify="center")
        entry.pack(fill="both", expand=True, padx=8, pady=8)
        return entry

    def _spinbox_cell(self, parent, row, column, variable, start, end, increment):
        frame = tk.Frame(parent, bg="#ffffff", highlightbackground="#88a59a", highlightthickness=1, bd=0)
        frame.grid(row=row, column=column, sticky="nsew")
        spinbox = tk.Spinbox(
            frame,
            from_=start,
            to=end,
            increment=increment,
            textvariable=variable,
            font=("Segoe UI", 10),
            relief="flat",
            justify="center",
        )
        spinbox.pack(fill="both", expand=True, padx=8, pady=8)
        return spinbox

    def _summary_row(self, parent, row, label_text, variable, emphasize=False):
        ttk.Label(parent, text=label_text, style="Field.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        style = "Summary.TLabel" if emphasize else "Value.TLabel"
        ttk.Label(parent, textvariable=variable, style=style).grid(row=row, column=1, sticky="e", pady=4)

    def _bind_events(self):
        self.appliance_combo.bind("<<ComboboxSelected>>", self.on_appliance_change)
        for variable in (self.power_var, self.hours_var, self.days_var):
            variable.trace_add("write", self.on_appliance_input_change)
        # FOCUS UPDATE
        self.current_entry.bind("<FocusOut>", self.on_meter_focus_out)
        self.previous_entry.bind("<FocusOut>", self.on_meter_focus_out)
        self.previous_month_entry.bind("<FocusOut>", self.on_meter_focus_out)

    def _on_frame_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_mode_view(self):
        appliance_mode = self.mode_var.get() == "appliance"
        appliance_state = "normal" if appliance_mode else "disabled"
        meter_state = "normal" if not appliance_mode else "disabled"

        for widget in (
            self.appliance_combo,
            self.power_entry,
            self.hours_spinbox,
            self.days_spinbox,
            self.inverter_check,
        ):
            widget.configure(state=appliance_state)
        self.current_entry.configure(state=meter_state)
        self.previous_entry.configure(state=meter_state)
        self.refresh_all()

    def on_appliance_change(self, _event=None):
        appliance = self.appliance_var.get()
        self.power_var.set(str(APPLIANCE_WATTAGE.get(appliance, "")))
        if appliance != "AC":
            self.inverter_ac_var.set(False)
        self.update_appliance_preview()

    def on_appliance_input_change(self, *_args):
        self.update_appliance_preview()

    def on_meter_input_change(self, value):
        # FIX: prevent cursor jump
        value = value.strip()
        if not value:
            return

        # VALIDATION
        try:
            float(value)
        except ValueError:
            return

        self._schedule_meter_refresh()

    def on_meter_focus_out(self, _event=None):
        # FOCUS UPDATE
        for value in (
            self.current_reading_var.get(),
            self.previous_reading_var.get(),
            self.previous_month_units_var.get(),
        ):
            self.on_meter_input_change(value)
        self.refresh_all()

    def _schedule_meter_refresh(self):
        # FIX: prevent cursor jump
        if self.meter_refresh_job:
            self.root.after_cancel(self.meter_refresh_job)

        # OPTIONAL DEBOUNCE
        self.meter_refresh_job = self.root.after(250, self._debounced_meter_refresh)

    def _debounced_meter_refresh(self):
        self.meter_refresh_job = None
        focused_widget = self.root.focus_get()
        if focused_widget in (self.current_entry, self.previous_entry, self.previous_month_entry):
            return
        self.refresh_all()

    def update_appliance_preview(self):
        parsed = self.parse_appliance_input(show_errors=False)
        if not parsed:
            self.realistic_units_var.set("0.00 kWh")
            return
        appliance, power, hours, days, efficiency, inverter = parsed
        _, realistic_units = self.calculate_appliance_units(
            appliance,
            power,
            hours,
            days,
            efficiency,
            inverter=inverter,
            apply_variation=False,
        )
        self.realistic_units_var.set(f"{realistic_units:.2f} kWh")

    def parse_appliance_input(self, show_errors=True):
        try:
            appliance = self.appliance_var.get().strip()
            power = float(self.power_var.get())
            hours = float(self.hours_var.get())
            days = int(float(self.days_var.get()))
            efficiency = APPLIANCE_EFFICIENCY.get(appliance, 1.0)
            inverter = self.inverter_ac_var.get()
            if not appliance:
                raise ValueError("Please select an appliance.")
            if power <= 0 or hours <= 0 or days <= 0:
                raise ValueError("Power, hours, and days must be greater than 0.")
            return appliance, power, hours, days, efficiency, inverter
        except ValueError as error:
            if show_errors:
                messagebox.showerror("Invalid Appliance Input", str(error))
            return None

    def calculate_theoretical_units(self, power, hours, days):
        """Classic full-power estimate kept for side-by-side comparison."""
        return (power * hours * days) / 1000

    def calculate_ac_units(self, power, hours, days, inverter=False, apply_variation=True):
        """
        AC runs at full power for the first 2 hours, then at reduced power.
        Inverter AC cools more efficiently after stabilization.
        """
        full_power_hours = min(hours, 2)
        reduced_hours = max(hours - 2, 0)
        reduced_factor = 0.4 if inverter else 0.6

        daily_wh = (power * full_power_hours) + (power * reduced_factor * reduced_hours)
        units = (daily_wh * days) / 1000

        if apply_variation:
            units *= random.uniform(0.9, 1.1)
        return units

    def calculate_appliance_units(self, appliance, power, hours, days, efficiency_factor, inverter=False, apply_variation=True):
        """
        Return both the old theoretical estimate and a more realistic estimate.
        Realistic usage applies appliance efficiency and AC cooldown behavior.
        """
        theoretical_units = self.calculate_theoretical_units(power, hours, days)

        if appliance == "AC":
            realistic_units = self.calculate_ac_units(
                power,
                hours,
                days,
                inverter=inverter,
                apply_variation=apply_variation,
            )
        else:
            realistic_units = (power * hours * days * efficiency_factor) / 1000
            if apply_variation:
                realistic_units *= random.uniform(0.9, 1.1)

        return theoretical_units, realistic_units

    def add_appliance(self):
        parsed = self.parse_appliance_input(show_errors=True)
        if not parsed:
            return

        appliance, power, hours, days, efficiency, inverter = parsed
        theoretical_units, realistic_units = self.calculate_appliance_units(
            appliance,
            power,
            hours,
            days,
            efficiency,
            inverter=inverter,
        )

        # CHECK DUPLICATE
        for index, item in enumerate(self.appliance_rows):
            if item["appliance"] == appliance:
                # PREVENT DUPLICATE
                existing_items = self.tree.get_children()
                if index < len(existing_items):
                    existing_row = existing_items[index]
                    self.tree.selection_set(existing_row)
                    self.tree.focus(existing_row)
                    self.tree.see(existing_row)
                messagebox.showwarning("Duplicate Entry", f"{appliance} is already added to the list.")
                return

        row = {
            "appliance": appliance,
            "power": power,
            "hours": hours,
            "days": days,
            "efficiency": efficiency,
            "theoretical_units": theoretical_units,
            "units": realistic_units,
            "inverter": inverter,
        }
        self.appliance_rows.append(row)
        self.tree.insert(
            "",
            "end",
            values=(
                appliance,
                f"{power:.0f}",
                f"{hours:.1f}",
                days,
                f"{realistic_units:.2f}",
            ),
        )
        self.refresh_all()

    def remove_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Remove Appliance", "Please select a row to remove.")
            return
        if not messagebox.askyesno("Confirm Remove", "Remove the selected appliance entry?"):
            return

        indices = [self.tree.index(item) for item in selected_items]
        for item in selected_items:
            self.tree.delete(item)
        for index in sorted(indices, reverse=True):
            if index < len(self.appliance_rows):
                self.appliance_rows.pop(index)
        self.refresh_all()

    def reset_all(self):
        if not messagebox.askyesno("Reset", "Clear all appliance entries and bill values?"):
            return
        self.appliance_rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.appliance_var.set("Fan")
        self.power_var.set(str(APPLIANCE_WATTAGE["Fan"]))
        self.hours_var.set("1")
        self.days_var.set("30")
        self.inverter_ac_var.set(False)
        self.realistic_units_var.set("0.00 kWh")
        self.current_reading_var.set("0")
        self.previous_reading_var.set("0")
        self.previous_month_units_var.set("0")
        self.warning_state = {"high_units": False, "high_appliance": False}
        self.refresh_all()

    def get_meter_units(self):
        try:
            current = float(self.current_reading_var.get())
            previous = float(self.previous_reading_var.get())
            units = current - previous
            if units < 0:
                self.reading_units_var.set("0.00 units")
                return 0.0
            self.reading_units_var.set(f"{units:.2f} units")
            return units
        except ValueError:
            self.reading_units_var.set("0.00 units")
            return 0.0

    def get_total_units(self):
        if self.mode_var.get() == "meter":
            return self.get_meter_units()
        return sum(item["units"] for item in self.appliance_rows)

    def calculate_energy_charge(self, units):
        slab_1_units = min(units, 100)
        slab_2_units = min(max(units - 100, 0), 100)
        slab_3_units = max(units - 200, 0)

        slab_1_charge = slab_1_units * 3
        slab_2_charge = slab_2_units * 5
        slab_3_charge = slab_3_units * 8

        self.slab_1_var.set(f"Rs {slab_1_charge:.2f}")
        self.slab_2_var.set(f"Rs {slab_2_charge:.2f}")
        self.slab_3_var.set(f"Rs {slab_3_charge:.2f}")

        return slab_1_charge + slab_2_charge + slab_3_charge

    def refresh_all(self):
        total_units = self.get_total_units()
        energy_charge = self.calculate_energy_charge(total_units)
        duty = energy_charge * ELECTRICITY_DUTY_RATE
        final_bill = energy_charge + duty + FIXED_CHARGE

        self.total_units_var.set(f"{total_units:.2f} units")
        self.energy_charge_var.set(f"Rs {energy_charge:.2f}")
        self.duty_var.set(f"Rs {duty:.2f}")
        self.fixed_charge_var.set(f"Rs {FIXED_CHARGE:.2f}")
        self.final_bill_var.set(f"Rs {final_bill:.2f}")
        self.amount_words_var.set(self.amount_to_words(int(final_bill)))

        self.update_insights(total_units)
        self.update_environment(total_units)
        self.update_charts()
        self.show_alerts(total_units)

    def update_insights(self, total_units):
        if self.appliance_rows:
            highest = max(self.appliance_rows, key=lambda item: item["units"])
            percentage = (highest["units"] / total_units * 100) if total_units > 0 else 0
            self.highest_appliance_var.set(f"{highest['appliance']} ({percentage:.1f}%)")
        else:
            self.highest_appliance_var.set("No appliance data available")

        try:
            previous_units = float(self.previous_month_units_var.get())
        except ValueError:
            previous_units = 0.0

        difference = total_units - previous_units
        if previous_units <= 0:
            self.usage_change_var.set("Previous month units not available")
        elif difference > 0:
            self.usage_change_var.set(f"This month usage increased by {difference:.2f} units")
        elif difference < 0:
            self.usage_change_var.set(f"This month usage decreased by {abs(difference):.2f} units")
        else:
            self.usage_change_var.set("This month usage is unchanged")

        if total_units > HIGH_USAGE_THRESHOLD:
            self.insight_message_var.set("High usage detected. Review AC and refrigerator usage.")
        elif self.appliance_rows:
            highest = max(self.appliance_rows, key=lambda item: item["units"])
            if highest["units"] > HIGH_APPLIANCE_THRESHOLD:
                self.insight_message_var.set(f"{highest['appliance']} is consuming heavily. Consider reducing usage.")
            else:
                self.insight_message_var.set("Usage looks moderate. Small optimizations can still reduce the bill.")
        else:
            self.insight_message_var.set("Add appliance data or enter meter readings to generate insights")

    def update_environment(self, total_units):
        co2 = total_units * CO2_FACTOR
        trees = co2 / TREE_OFFSET if TREE_OFFSET else 0

        if co2 < 100:
            message = "Low impact"
        elif co2 < 250:
            message = "Medium impact"
        else:
            message = "High impact"

        self.co2_var.set(f"{co2:.2f} kg CO2")
        self.trees_var.set(f"{trees:.2f} trees")
        self.eco_message_var.set(message)

    def show_alerts(self, total_units):
        if total_units > HIGH_USAGE_THRESHOLD and not self.warning_state["high_units"]:
            self.warning_state["high_units"] = True
            messagebox.showwarning("High Usage Alert", "Total consumption exceeded 200 units.")
        if total_units <= HIGH_USAGE_THRESHOLD:
            self.warning_state["high_units"] = False

        overused = [item for item in self.appliance_rows if item["units"] > HIGH_APPLIANCE_THRESHOLD]
        if overused and not self.warning_state["high_appliance"]:
            self.warning_state["high_appliance"] = True
            appliance = max(overused, key=lambda item: item["units"])
            messagebox.showwarning(
                "Appliance Alert",
                f"{appliance['appliance']} is consuming {appliance['units']:.2f} kWh. Consider reducing its usage.",
            )
        if not overused:
            self.warning_state["high_appliance"] = False

    def amount_to_words(self, amount):
        if amount == 0:
            return "Zero rupees only"

        ones = [
            "",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        def two_digits(number):
            if number < 20:
                return ones[number]
            return tens[number // 10] + ("" if number % 10 == 0 else f" {ones[number % 10]}")

        def three_digits(number):
            hundred = number // 100
            remainder = number % 100
            parts = []
            if hundred:
                parts.append(f"{ones[hundred]} hundred")
            if remainder:
                parts.append(two_digits(remainder))
            return " ".join(parts)

        chunks = []
        if amount >= 1000:
            chunks.append(f"{three_digits(amount // 1000)} thousand")
            amount %= 1000
        if amount > 0:
            chunks.append(three_digits(amount))
        return f"{' '.join(chunk.strip() for chunk in chunks if chunk).title()} rupees only"

    def appliance_chart_data(self, top_n=None):
        # Sort by highest unit consumption so charts can focus on the biggest loads.
        sorted_rows = sorted(self.appliance_rows, key=lambda item: item["units"], reverse=True)
        if top_n is not None:
            sorted_rows = sorted_rows[:top_n]

        names = [item["appliance"] for item in sorted_rows]
        units = [item["units"] for item in sorted_rows]
        return names, units

    def build_bar_figure(self):
        figure = Figure(figsize=(4.1, 3.3), dpi=100)
        axis = figure.add_subplot(111)
        names, units = self.appliance_chart_data(top_n=3)
        if units:
            colors = ["#d9534f"] + ["#5d9c77"] * (len(units) - 1)
            bars = axis.bar(names, units, color=colors)
            axis.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
        else:
            axis.text(0.5, 0.5, "No appliance data yet", ha="center", va="center", transform=axis.transAxes)
        axis.set_title("Top 3 Energy Consuming Appliances")
        axis.tick_params(axis="x", rotation=20)
        axis.set_ylabel("kWh")
        figure.tight_layout()
        return figure

    def build_pie_figure(self):
        figure = Figure(figsize=(4.1, 3.3), dpi=100)
        axis = figure.add_subplot(111)
        names, units = self.appliance_chart_data()
        if units and sum(units) > 0:
            bars = axis.bar(names, units, color=["#6fa8dc", "#93c47d", "#f6b26b", "#8e7cc3", "#76a5af", "#c27ba0", "#ffd966"])
            axis.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)
        else:
            axis.text(0.5, 0.5, "No appliance data yet", ha="center", va="center", transform=axis.transAxes)
        axis.set_title("Consumption Distribution")
        axis.set_ylabel("kWh")
        axis.tick_params(axis="x", rotation=20)
        figure.tight_layout()
        return figure

    def build_bill_figure(self):
        figure = Figure(figsize=(4.1, 3.3), dpi=100)
        axis = figure.add_subplot(111)
        try:
            energy = float(self.energy_charge_var.get().replace("Rs", "").strip())
            duty = float(self.duty_var.get().replace("Rs", "").strip())
            fixed = FIXED_CHARGE
        except ValueError:
            energy, duty, fixed = 0.0, 0.0, FIXED_CHARGE

        values = [energy, duty, fixed]
        labels = ["Energy", "Duty", "Fixed"]
        if sum(values) > 0:
            axis.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        else:
            axis.text(0.5, 0.5, "No bill data yet", ha="center", va="center", transform=axis.transAxes)
        axis.set_title("Bill Breakdown")
        figure.tight_layout()
        return figure

    def build_co2_figure(self):
        figure = Figure(figsize=(4.1, 3.3), dpi=100)
        axis = figure.add_subplot(111)
        total_units = self.get_total_units()
        co2 = total_units * CO2_FACTOR
        saved = max(0, 300 - co2)
        values = [co2, saved]
        labels = ["CO2 Emission", "Low Impact Gap"]
        if sum(values) > 0:
            axis.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        else:
            axis.text(0.5, 0.5, "No CO2 data yet", ha="center", va="center", transform=axis.transAxes)
        axis.set_title("CO2 Distribution")
        figure.tight_layout()
        return figure

    def update_charts(self):
        figures = [
            self.build_bar_figure(),
            self.build_pie_figure(),
            self.build_bill_figure(),
            self.build_co2_figure(),
        ]

        for canvas_widget in self.chart_canvases:
            canvas_widget.get_tk_widget().destroy()
        self.chart_canvases.clear()

        for host, figure in zip(self.chart_hosts, figures):
            canvas_widget = FigureCanvasTkAgg(figure, master=host)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill="both", expand=True)
            self.chart_canvases.append(canvas_widget)

    def export_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Export Bill PDF",
        )
        if not path:
            return

        pdf = pdf_canvas.Canvas(path, pagesize=A4)
        width, height = A4

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(40, height - 50, "Electricity Consumption Monitor")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(40, height - 72, f"User: {self.username}")
        pdf.drawString(40, height - 90, f"Mode: {self.mode_var.get().title()}")

        y = height - 125
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Bill Summary")
        y -= 22
        pdf.setFont("Helvetica", 10)
        summary_lines = [
            f"Total Units: {self.total_units_var.get()}",
            f"Energy Charges: {self.energy_charge_var.get()}",
            f"Electricity Duty: {self.duty_var.get()}",
            f"Fixed Charge: {self.fixed_charge_var.get()}",
            f"Final Bill: {self.final_bill_var.get()}",
            f"Amount in Words: {self.amount_words_var.get()}",
            f"CO2 Emission: {self.co2_var.get()}",
            f"Trees Required: {self.trees_var.get()}",
            f"Eco Message: {self.eco_message_var.get()}",
            f"Highest Appliance: {self.highest_appliance_var.get()}",
            f"Usage Change: {self.usage_change_var.get()}",
        ]
        for line in summary_lines:
            pdf.drawString(40, y, line)
            y -= 16

        y -= 8
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Appliance Details")
        y -= 20
        pdf.setFont("Helvetica", 10)
        for item in self.appliance_rows:
            text = f"{item['appliance']} | {item['power']}W | {item['hours']}h/day | {item['days']} days | {item['units']:.2f} kWh"
            pdf.drawString(40, y, text)
            y -= 16
            if y < 70:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)

        pdf.save()
        messagebox.showinfo("Export PDF", "PDF bill exported successfully.")

    def logout(self):
        if not messagebox.askyesno("Logout", "Log out and return to the login window?"):
            return
        self.root.destroy()
        launch_login_window()


def launch_main_app(username):
    root = tk.Tk()
    ElectricityConsumptionMonitor(root, username)
    root.mainloop()


def launch_login_window():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


def main():
    if initialize_database():
        launch_login_window()


if __name__ == "__main__":
    main()
