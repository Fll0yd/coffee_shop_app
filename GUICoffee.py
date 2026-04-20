import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


# =========================
# Configuration
# =========================
APP_TITLE = "Flloyd's Coffee Shop"
APP_WIDTH = 1200
APP_HEIGHT = 760
PREP_MINUTES_PER_ITEM = 2

MENU_PRICES = {
    "Espresso": 5.00,
    "Americano": 6.00,
    "Latte": 9.00,
    "Cappuccino": 10.00,
    "Mocha": 7.00,
    "Almond Cappuccino": 11.00,
    "Mint Latte": 8.00,
    "Coffee Frappe": 13.00,
    "Iced Coffee": 4.00,
    "Black Coffee": 3.00,
}

VIP_CUSTOMERS = {"Kenneth", "Flloyd"}
SPECIAL_CHECK_CUSTOMERS = {"Ben", "Loki", "Patricia"}


# =========================
# Data Models
# =========================
@dataclass
class OrderItem:
    item_name: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


# =========================
# Persistence Layer
# =========================
class OrderRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    total_items INTEGER NOT NULL,
                    prep_minutes INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ready_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_order(
        self,
        customer_name: str,
        items: list[OrderItem],
        total_cost: float,
        total_items: int,
        prep_minutes: int,
        status: str,
        created_at: str,
        ready_at: str,
    ) -> int:
        items_json = json.dumps(
            [
                {
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal,
                }
                for item in items
            ]
        )

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO orders (
                    customer_name, items_json, total_cost, total_items,
                    prep_minutes, status, created_at, ready_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_name,
                    items_json,
                    total_cost,
                    total_items,
                    prep_minutes,
                    status,
                    created_at,
                    ready_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_order_status(self, order_id: int, status: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id),
            )
            conn.commit()

    def get_all_orders(self):
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, customer_name, total_items, total_cost, prep_minutes,
                       status, created_at, ready_at
                FROM orders
                ORDER BY id DESC
                """
            )
            return cursor.fetchall()

    def get_order_items(self, order_id: int):
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT items_json FROM orders WHERE id = ?",
                (order_id,),
            )
            row = cursor.fetchone()
            if not row:
                return []
            return json.loads(row[0])


# =========================
# Business Logic
# =========================
class CoffeeShopService:
    def __init__(self, menu_prices: dict[str, float]):
        self.menu_prices = menu_prices

    def validate_customer_name(self, name: str) -> str | None:
        name = name.strip()
        if not name:
            return "Please enter your name before placing an order."
        return None

    def check_customer_status(self, customer_name: str) -> tuple[bool, str]:
        customer_name = customer_name.strip()

        if customer_name in VIP_CUSTOMERS:
            return True, f"Welcome back, {customer_name}. Great to see you again."

        if customer_name in SPECIAL_CHECK_CUSTOMERS:
            return True, (
                f"Welcome, {customer_name}. Your order can be placed as normal."
            )

        return True, f"Welcome, {customer_name}. Thanks for stopping by."

    def build_items_from_inputs(
        self, raw_items: list[tuple[str, str]]
    ) -> list[OrderItem]:
        items: list[OrderItem] = []

        for item_name, quantity_str in raw_items:
            item_name = item_name.strip()
            quantity_str = quantity_str.strip()

            if not item_name and not quantity_str:
                continue

            if not item_name:
                raise ValueError("One of the order rows is missing a selected item.")

            if not quantity_str:
                raise ValueError(f"Quantity is missing for '{item_name}'.")

            try:
                quantity = int(quantity_str)
            except ValueError:
                raise ValueError(f"Quantity for '{item_name}' must be a whole number.")

            if quantity <= 0:
                raise ValueError(f"Quantity for '{item_name}' must be greater than zero.")

            if item_name not in self.menu_prices:
                raise ValueError(f"'{item_name}' is not on the menu.")

            items.append(
                OrderItem(
                    item_name=item_name,
                    quantity=quantity,
                    unit_price=self.menu_prices[item_name],
                )
            )

        if not items:
            raise ValueError("Please add at least one item to the order.")

        return items

    def calculate_order_summary(self, items: list[OrderItem]) -> dict:
        total_items = sum(item.quantity for item in items)
        total_cost = sum(item.subtotal for item in items)
        prep_minutes = max(1, total_items * PREP_MINUTES_PER_ITEM)

        return {
            "total_items": total_items,
            "total_cost": round(total_cost, 2),
            "prep_minutes": prep_minutes,
        }


# =========================
# UI Layer
# =========================
class CoffeeShopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.minsize(1100, 700)

        base_dir = Path(__file__).resolve().parent
        self.assets_dir = base_dir / "assets"
        self.db_path = base_dir / "coffee_shop.db"

        self.repo = OrderRepository(self.db_path)
        self.service = CoffeeShopService(MENU_PRICES)

        self.order_rows: list[tuple[ttk.Combobox, ttk.Entry]] = []
        self.active_countdowns: dict[int, dict] = {}

        self._configure_style()
        self._build_ui()
        self._load_background()
        self.refresh_order_history()

    def _configure_style(self):
        self.root.configure(bg="#f7f4ef")

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), background="#f7f4ef", foreground="#2d2a26")
        style.configure("Section.TLabelframe", background="#ffffff")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 12, "bold"))
        style.configure("TLabel", background="#f7f4ef", foreground="#2d2a26", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Treeview", font=("Consolas", 10), rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        self.background_label = tk.Label(self.root, bd=0)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.main_container = tk.Frame(self.root, bg="#f7f4ef")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=16)

        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_rowconfigure(1, weight=1)

        title = ttk.Label(self.main_container, text=APP_TITLE, style="Title.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        subtitle = ttk.Label(
            self.main_container,
            text="Interactive coffee ordering app with order tracking and SQLite history",
        )
        subtitle.grid(row=0, column=0, columnspan=2, sticky="w", pady=(42, 14))

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        left = ttk.LabelFrame(self.main_container, text="New Order", style="Section.TLabelframe", padding=14)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=4)
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(2, weight=1)

        ttk.Label(left, text="Customer Name").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.entry_name = ttk.Entry(left, width=30)
        self.entry_name.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 8))
        self.entry_name.bind("<Return>", lambda _event: self.handle_customer_check())

        self.btn_check_customer = ttk.Button(left, text="Check In Customer", command=self.handle_customer_check)
        self.btn_check_customer.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=(0, 8))

        self.customer_status_var = tk.StringVar(value="Enter a customer name to begin.")
        self.lbl_customer_status = ttk.Label(left, textvariable=self.customer_status_var)
        self.lbl_customer_status.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 14))

        ttk.Label(left, text="Item").grid(row=2, column=0, sticky="w")
        ttk.Label(left, text="Quantity").grid(row=2, column=1, sticky="w")
        ttk.Label(left, text="Subtotal").grid(row=2, column=2, sticky="w")

        self.items_frame = tk.Frame(left, bg="#ffffff")
        self.items_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(6, 10))
        self.items_frame.grid_columnconfigure(0, weight=3)
        self.items_frame.grid_columnconfigure(1, weight=1)
        self.items_frame.grid_columnconfigure(2, weight=1)

        self.add_order_row()

        self.btn_add_item = ttk.Button(left, text="Add Item", command=self.add_order_row)
        self.btn_add_item.grid(row=4, column=0, sticky="w", pady=(0, 14))

        summary_frame = tk.Frame(left, bg="#ffffff")
        summary_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 14))
        summary_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(summary_frame, text="Total Items").grid(row=0, column=0, sticky="w")
        self.total_items_var = tk.StringVar(value="0")
        ttk.Label(summary_frame, textvariable=self.total_items_var).grid(row=0, column=1, sticky="w")

        ttk.Label(summary_frame, text="Total Cost").grid(row=1, column=0, sticky="w")
        self.total_cost_var = tk.StringVar(value="$0.00")
        ttk.Label(summary_frame, textvariable=self.total_cost_var).grid(row=1, column=1, sticky="w")

        ttk.Label(summary_frame, text="Estimated Prep Time").grid(row=2, column=0, sticky="w")
        self.prep_time_var = tk.StringVar(value="0 minute(s)")
        ttk.Label(summary_frame, textvariable=self.prep_time_var).grid(row=2, column=1, sticky="w")

        btn_frame = tk.Frame(left, bg="#ffffff")
        btn_frame.grid(row=6, column=0, columnspan=4, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_preview = ttk.Button(btn_frame, text="Preview Order", command=self.preview_order)
        self.btn_preview.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_submit = ttk.Button(btn_frame, text="Submit Order", command=self.submit_order)
        self.btn_submit.grid(row=0, column=1, sticky="ew", padx=6)

        self.btn_reset = ttk.Button(btn_frame, text="Reset Form", command=self.reset_form)
        self.btn_reset.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        countdown_frame = ttk.LabelFrame(left, text="Active Order Timer", style="Section.TLabelframe", padding=12)
        countdown_frame.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(16, 0))

        self.active_order_var = tk.StringVar(value="No active order")
        ttk.Label(countdown_frame, textvariable=self.active_order_var, font=("Consolas", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )

    def _build_right_panel(self):
        right = ttk.LabelFrame(self.main_container, text="Order History", style="Section.TLabelframe", padding=14)
        right.grid(row=1, column=1, sticky="nsew", pady=4)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            right,
            columns=("id", "customer", "items", "total", "status", "created"),
            show="headings",
            height=18,
        )

        headings = {
            "id": "ID",
            "customer": "Customer",
            "items": "Items",
            "total": "Total",
            "status": "Status",
            "created": "Created",
        }

        widths = {
            "id": 50,
            "customer": 120,
            "items": 60,
            "total": 80,
            "status": 100,
            "created": 160,
        }

        for key, title in headings.items():
            self.history_tree.heading(key, text=title)
            self.history_tree.column(key, width=widths[key], anchor="center")

        self.history_tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(right, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        details_frame = ttk.LabelFrame(right, text="Selected Order Details", style="Section.TLabelframe", padding=10)
        details_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        details_frame.grid_columnconfigure(0, weight=1)

        self.order_details_text = tk.Text(details_frame, height=10, wrap="word", font=("Consolas", 10))
        self.order_details_text.grid(row=0, column=0, sticky="ew")
        self.order_details_text.configure(state="disabled")

        self.history_tree.bind("<<TreeviewSelect>>", self.on_order_select)

    def _load_background(self):
        bg_path = self.assets_dir / "background.png"
        if bg_path.exists():
            try:
                self.bg_image = tk.PhotoImage(file=str(bg_path))
                self.background_label.configure(image=self.bg_image)
            except tk.TclError:
                self.background_label.configure(bg="#f7f4ef")
        else:
            self.background_label.configure(bg="#f7f4ef")

    def add_order_row(self):
        row_index = len(self.order_rows)

        item_box = ttk.Combobox(
            self.items_frame,
            values=list(MENU_PRICES.keys()),
            state="readonly",
            width=28,
        )
        item_box.grid(row=row_index, column=0, sticky="ew", padx=(0, 8), pady=4)

        qty_entry = ttk.Entry(self.items_frame, width=10)
        qty_entry.grid(row=row_index, column=1, sticky="ew", padx=(0, 8), pady=4)

        subtotal_var = tk.StringVar(value="$0.00")
        subtotal_label = ttk.Label(self.items_frame, textvariable=subtotal_var)
        subtotal_label.grid(row=row_index, column=2, sticky="w", pady=4)

        def update_subtotal(*_args):
            item_name = item_box.get().strip()
            qty = qty_entry.get().strip()
            if item_name and qty.isdigit():
                subtotal = MENU_PRICES[item_name] * int(qty)
                subtotal_var.set(f"${subtotal:.2f}")
            else:
                subtotal_var.set("$0.00")
            self._update_summary_if_possible()

        item_box.bind("<<ComboboxSelected>>", update_subtotal)
        qty_entry.bind("<KeyRelease>", update_subtotal)

        self.order_rows.append((item_box, qty_entry))

    def handle_customer_check(self):
        customer_name = self.entry_name.get().strip()
        error = self.service.validate_customer_name(customer_name)
        if error:
            messagebox.showwarning("Missing Name", error)
            return

        allowed, message = self.service.check_customer_status(customer_name)
        self.customer_status_var.set(message)

        if allowed:
            messagebox.showinfo("Customer Check-In", message)

    def _collect_raw_inputs(self) -> list[tuple[str, str]]:
        return [(item_box.get(), qty_entry.get()) for item_box, qty_entry in self.order_rows]

    def _build_order(self):
        customer_name = self.entry_name.get().strip()
        name_error = self.service.validate_customer_name(customer_name)
        if name_error:
            raise ValueError(name_error)

        items = self.service.build_items_from_inputs(self._collect_raw_inputs())
        summary = self.service.calculate_order_summary(items)
        return customer_name, items, summary

    def _update_summary_if_possible(self):
        try:
            _customer_name, items, summary = self._build_order()
            self.total_items_var.set(str(summary["total_items"]))
            self.total_cost_var.set(f"${summary['total_cost']:.2f}")
            self.prep_time_var.set(f"{summary['prep_minutes']} minute(s)")
        except Exception:
            self.total_items_var.set("0")
            self.total_cost_var.set("$0.00")
            self.prep_time_var.set("0 minute(s)")

    def preview_order(self):
        try:
            customer_name, items, summary = self._build_order()
        except ValueError as exc:
            messagebox.showerror("Invalid Order", str(exc))
            return

        lines = [
            f"Customer: {customer_name}",
            "",
            "Items:",
        ]
        for item in items:
            lines.append(
                f"- {item.item_name} x{item.quantity} @ ${item.unit_price:.2f} = ${item.subtotal:.2f}"
            )

        lines.extend(
            [
                "",
                f"Total Items: {summary['total_items']}",
                f"Total Cost: ${summary['total_cost']:.2f}",
                f"Estimated Prep Time: {summary['prep_minutes']} minute(s)",
            ]
        )

        messagebox.showinfo("Order Preview", "\n".join(lines))

    def submit_order(self):
        try:
            customer_name, items, summary = self._build_order()
        except ValueError as exc:
            messagebox.showerror("Invalid Order", str(exc))
            return

        confirm = messagebox.askyesno(
            "Confirm Order",
            (
                f"Customer: {customer_name}\n"
                f"Total Items: {summary['total_items']}\n"
                f"Total Cost: ${summary['total_cost']:.2f}\n"
                f"Estimated Prep Time: {summary['prep_minutes']} minute(s)\n\n"
                f"Submit this order?"
            ),
        )
        if not confirm:
            return

        created_at_dt = datetime.now()
        ready_at_dt = created_at_dt + timedelta(minutes=summary["prep_minutes"])

        order_id = self.repo.create_order(
            customer_name=customer_name,
            items=items,
            total_cost=summary["total_cost"],
            total_items=summary["total_items"],
            prep_minutes=summary["prep_minutes"],
            status="Queued",
            created_at=created_at_dt.isoformat(timespec="seconds"),
            ready_at=ready_at_dt.isoformat(timespec="seconds"),
        )

        self.active_countdowns[order_id] = {
            "ready_at": ready_at_dt,
            "status": "Queued",
        }

        self._start_order_lifecycle(order_id, ready_at_dt)
        self.refresh_order_history()
        self.reset_form(clear_customer=False)

        messagebox.showinfo(
            "Order Submitted",
            f"Order #{order_id} has been placed successfully.\n\n"
            f"Estimated ready time: {summary['prep_minutes']} minute(s)."
        )

    def _start_order_lifecycle(self, order_id: int, ready_at: datetime):
        self.repo.update_order_status(order_id, "Preparing")
        self._update_active_order_display(order_id, ready_at)
        self.refresh_order_history()

        def tick():
            if order_id not in self.active_countdowns:
                return

            now = datetime.now()
            if now >= ready_at:
                self.repo.update_order_status(order_id, "Ready")
                self.active_order_var.set(f"Order #{order_id}: Ready for pickup")
                self.refresh_order_history()
                del self.active_countdowns[order_id]
                messagebox.showinfo("Order Ready", f"Order #{order_id} is now ready for pickup.")
                return

            self._update_active_order_display(order_id, ready_at)
            self.root.after(1000, tick)

        self.root.after(1000, tick)

    def _update_active_order_display(self, order_id: int, ready_at: datetime):
        remaining = ready_at - datetime.now()
        seconds = max(0, int(remaining.total_seconds()))
        minutes, secs = divmod(seconds, 60)
        self.active_order_var.set(
            f"Order #{order_id}: Preparing | Ready in {minutes:02d}:{secs:02d}"
        )

    def reset_form(self, clear_customer: bool = True):
        if clear_customer:
            self.entry_name.delete(0, tk.END)
            self.customer_status_var.set("Enter a customer name to begin.")

        for widget in self.items_frame.winfo_children():
            widget.destroy()

        self.order_rows.clear()
        self.add_order_row()

        self.total_items_var.set("0")
        self.total_cost_var.set("$0.00")
        self.prep_time_var.set("0 minute(s)")

    def refresh_order_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        for order in self.repo.get_all_orders():
            order_id, customer, total_items, total_cost, _prep_minutes, status, created_at, _ready_at = order
            created_display = created_at.replace("T", " ")
            self.history_tree.insert(
                "",
                "end",
                values=(
                    order_id,
                    customer,
                    total_items,
                    f"${total_cost:.2f}",
                    status,
                    created_display,
                ),
            )

    def on_order_select(self, _event):
        selection = self.history_tree.selection()
        if not selection:
            return

        values = self.history_tree.item(selection[0], "values")
        if not values:
            return

        order_id = int(values[0])
        items = self.repo.get_order_items(order_id)

        details_lines = [f"Order #{order_id}", ""]
        for item in items:
            details_lines.append(
                f"{item['item_name']} x{item['quantity']} @ ${item['unit_price']:.2f} = ${item['subtotal']:.2f}"
            )

        self.order_details_text.configure(state="normal")
        self.order_details_text.delete("1.0", tk.END)
        self.order_details_text.insert(tk.END, "\n".join(details_lines))
        self.order_details_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = CoffeeShopApp(root)
    root.mainloop()
