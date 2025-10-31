import sqlite3
from datetime import datetime

DB_FILE = "inventory.db"

# ---------------------------
# Helpers
# ---------------------------
def get_connection():
    """Return a sqlite3 connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def input_int(prompt, allow_empty=False):
    """Prompt for an integer, repeat until valid or empty allowed."""
    while True:
        val = input(prompt).strip()
        if allow_empty and val == "":
            return None
        try:
            return int(val)
        except ValueError:
            print("⚠️ Please enter a valid integer.")

def input_float(prompt):
    """Prompt for a float, repeat until valid."""
    while True:
        val = input(prompt).strip()
        try:
            return float(val)
        except ValueError:
            print("⚠️ Please enter a valid number (e.g., 12.50).")

# ---------------------------
# Table Creation
# ---------------------------
def create_tables():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                supplier_id INTEGER,
                FOREIGN KEY(supplier_id) REFERENCES Suppliers(supplier_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Transactions (
                trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                trans_type TEXT CHECK(trans_type IN ('IN','OUT')),
                quantity INTEGER NOT NULL,
                date TEXT,
                FOREIGN KEY(product_id) REFERENCES Products(product_id)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print("DB Error on create_tables:", e)
    finally:
        conn.close()

# ---------------------------
# Supplier Management
# ---------------------------
def add_supplier():
    print("\n--- Add Supplier ---")
    name = input("Supplier name: ").strip()
    if not name:
        print("⚠️ Name cannot be empty.")
        return
    contact = input("Contact (phone/email) [optional]: ").strip() or None

    conn = get_connection()
    try:
        conn.execute("INSERT INTO Suppliers (name, contact) VALUES (?, ?)", (name, contact))
        conn.commit()
        print(f"✅ Supplier '{name}' added.")
    except sqlite3.Error as e:
        print("DB Error adding supplier:", e)
    finally:
        conn.close()

def view_suppliers():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT supplier_id, name, contact FROM Suppliers ORDER BY supplier_id").fetchall()
        if not rows:
            print("ℹ️ No suppliers found.")
            return
        print("\n📋 Suppliers:")
        for r in rows:
            print(f"ID: {r['supplier_id']} | Name: {r['name']} | Contact: {r['contact'] or '-'}")
    except sqlite3.Error as e:
        print("DB Error viewing suppliers:", e)
    finally:
        conn.close()

def supplier_exists(supplier_id):
    if supplier_id is None:
        return False
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM Suppliers WHERE supplier_id=?", (supplier_id,)).fetchone()
        return bool(row)
    finally:
        conn.close()

# ---------------------------
# Product Management
# ---------------------------
def add_product():
    print("\n--- Add Product ---")
    name = input("Product name: ").strip()
    if not name:
        print("⚠️ Product name cannot be empty.")
        return
    category = input("Category [optional]: ").strip() or None
    quantity = input_int("Initial quantity: ")
    if quantity is None or quantity < 0:
        print("⚠️ Quantity must be 0 or greater.")
        return
    price = input_float("Price per unit: ")
    print("\nAvailable suppliers (optional):")
    view_suppliers()
    supplier_id = input_int("Enter supplier ID (or press Enter to skip): ", allow_empty=True)

    if supplier_id is not None and not supplier_exists(supplier_id):
        print("⚠️ Supplier ID does not exist. Use existing supplier or add a new one.")
        return

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO Products (name, category, quantity, price, supplier_id) VALUES (?, ?, ?, ?, ?)",
            (name, category, quantity, price, supplier_id)
        )
        conn.commit()
        print(f"📦 Product '{name}' added successfully.")
    except sqlite3.Error as e:
        print("DB Error adding product:", e)
    finally:
        conn.close()

def view_products():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.product_id, p.name, p.category, p.quantity, p.price,
                   s.supplier_id, s.name AS supplier_name
            FROM Products p
            LEFT JOIN Suppliers s ON p.supplier_id = s.supplier_id
            ORDER BY p.product_id
        """).fetchall()
        if not rows:
            print("ℹ️ No products found.")
            return
        print("\n📋 Products:")
        for r in rows:
            supplier = f"{r['supplier_name']} (ID:{r['supplier_id']})" if r['supplier_name'] else "-"
            print(f"ID: {r['product_id']} | Name: {r['name']} | Cat: {r['category'] or '-'} | Qty: {r['quantity']} | Price: {r['price']} | Supplier: {supplier}")
    except sqlite3.Error as e:
        print("DB Error viewing products:", e)
    finally:
        conn.close()

def get_product(product_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM Products WHERE product_id=?", (product_id,)).fetchone()
    finally:
        conn.close()

# ---------------------------
# Stock Transactions
# ---------------------------
def stock_in():
    print("\n--- Stock IN ---")
    view_products()
    product_id = input_int("Enter product ID to add stock to: ")
    product = get_product(product_id)
    if not product:
        print("⚠️ Product not found.")
        return
    qty = input_int("Quantity to add: ")
    if qty is None or qty <= 0:
        print("⚠️ Quantity must be a positive integer.")
        return

    conn = get_connection()
    try:
        conn.execute("UPDATE Products SET quantity = quantity + ? WHERE product_id=?", (qty, product_id))
        conn.execute("INSERT INTO Transactions (product_id, trans_type, quantity, date) VALUES (?, 'IN', ?, ?)",
                     (product_id, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        print(f"✅ Stock updated: +{qty} to '{product['name']}' (ID: {product_id}).")
    except sqlite3.Error as e:
        print("DB Error on stock_in:", e)
    finally:
        conn.close()

def stock_out():
    print("\n--- Stock OUT ---")
    view_products()
    product_id = input_int("Enter product ID to remove stock from: ")
    product = get_product(product_id)
    if not product:
        print("⚠️ Product not found.")
        return
    qty = input_int("Quantity to remove: ")
    if qty is None or qty <= 0:
        print("⚠️ Quantity must be a positive integer.")
        return

    if product['quantity'] < qty:
        print(f"⚠️ Not enough stock. Available: {product['quantity']}")
        return

    conn = get_connection()
    try:
        conn.execute("UPDATE Products SET quantity = quantity - ? WHERE product_id=?", (qty, product_id))
        conn.execute("INSERT INTO Transactions (product_id, trans_type, quantity, date) VALUES (?, 'OUT', ?, ?)",
                     (product_id, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        print(f"✅ Stock decreased: -{qty} from '{product['name']}' (ID: {product_id}).")
    except sqlite3.Error as e:
        print("DB Error on stock_out:", e)
    finally:
        conn.close()

# ---------------------------
# Reports
# ---------------------------
def low_stock_report():
    print("\n--- Low Stock Report ---")
    threshold = input_int("Enter low stock threshold: ")
    if threshold is None or threshold < 0:
        print("⚠️ Threshold must be 0 or greater.")
        return
    conn = get_connection()
    try:
        rows = conn.execute("SELECT product_id, name, quantity FROM Products WHERE quantity <= ? ORDER BY quantity", (threshold,)).fetchall()
        if not rows:
            print("✅ No products with quantity <= threshold.")
            return
        print("\n⚠️ Low Stock Products:")
        for r in rows:
            print(f"ID: {r['product_id']} | Name: {r['name']} | Qty: {r['quantity']}")
    except sqlite3.Error as e:
        print("DB Error on low_stock_report:", e)
    finally:
        conn.close()

def transaction_report():
    print("\n--- Transactions Report ---")
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT t.trans_id, t.product_id, p.name AS product_name, t.trans_type, t.quantity, t.date
            FROM Transactions t
            LEFT JOIN Products p ON t.product_id = p.product_id
            ORDER BY t.date DESC, t.trans_id DESC
        """).fetchall()
        if not rows:
            print("ℹ️ No transactions found.")
            return
        print("\n📊 Transactions:")
        for r in rows:
            print(f"TransID: {r['trans_id']} | ProdID: {r['product_id']} | Product: {r['product_name'] or '-'} | Type: {r['trans_type']} | Qty: {r['quantity']} | Date: {r['date']}")
    except sqlite3.Error as e:
        print("DB Error on transaction_report:", e)
    finally:
        conn.close()

# ---------------------------
# Menu System
# ---------------------------
def main_menu():
    create_tables()
    print("===== 📦 Inventory Management System =====")

    actions = {
        "1": add_supplier,
        "2": view_suppliers,
        "3": add_product,
        "4": view_products,
        "5": stock_in,
        "6": stock_out,
        "7": low_stock_report,
        "8": transaction_report,
    }

    while True:
        print("\n1. Add Supplier\n2. View Suppliers\n3. Add Product\n4. View Products")
        print("5. Stock IN\n6. Stock OUT\n7. Low Stock Report\n8. Transaction Report\n9. Exit")
        choice = input("Enter choice: ").strip()

        if choice == "9":
            print("👋 Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("⚠️ Invalid choice. Please enter a number from 1 to 9.")

if __name__ == "__main__":
    main_menu()
