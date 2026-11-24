import sqlite3
from translations import get_text
DB_NAME = "biashara_manager.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    return conn

# --- 1. BUSINESS REGISTRATION & CUSTOM FIELDS ---
def register_business(business_name, business_type=None, lang="en"):
    """Dynamically registers any shop on the fly."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO businesses (business_name, business_type)
        VALUES (?, ?)
    """,
        (business_name, business_type),
    )
    business_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(
        get_text("biz_registered", lang=lang, name=business_name, id=business_id)
    )
    return business_id

def register_business_fields(business_id, field_names, lang="en"):
    """Allows a business owner to define custom columns/attributes for their specific shop."""
    conn = get_db_connection()
    cursor = conn.cursor()
    for name in field_names:
        cursor.execute(
            """
            INSERT INTO business_fields (business_id, field_name)
            VALUES (?, ?)
        """,
            (business_id, name.strip()),
        )
    conn.commit()
    conn.close()
    print(f"Registered {len(field_names)} custom fields for business ID {business_id}.")

# --- 2. INVENTORY & CUSTOM ATTRIBUTES ---
def add_product_with_custom_fields(
    business_id,
    product_name,
    buying_price,
    selling_price,
    stock_quantity,
    supplier_id=None,
    reorder_level=5.0,
    custom_fields=None,
):
    """Adds a universal product, saves custom EAV fields, and checks initial stock levels."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert core product
    cursor.execute(
        """
        INSERT INTO products (business_id, supplier_id, product_name, buying_price, selling_price, stock_quantity, reorder_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            business_id,
            supplier_id,
            product_name,
            buying_price,
            selling_price,
            stock_quantity,
            reorder_level,
        ),
    )
    product_id = cursor.lastrowid
    # Insert custom fields
    if custom_fields:
        for field_id, value in custom_fields.items():
            cursor.execute(
                """
                INSERT INTO product_field_values (product_id, field_id, field_value)
                VALUES (?, ?, ?)
            """,
                (product_id, field_id, str(value)),
            )
    conn.commit()
    conn.close()
    print(f"Product '{product_name}' added successfully with ID {product_id}.")
    # Immediate stock check notification upon creation
    if stock_quantity <= reorder_level:
        print(
            f"⚠️ **NOTIFICATION**: Low stock alert for '{product_name}'! Current"
            f" stock ({stock_quantity}) is at or below reorder level"
            f" ({reorder_level})."
        )
    return product_id

def view_inventory_levels(business_id):
    """Displays current stock levels and reorder thresholds for a business."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT product_id, product_name, stock_quantity, reorder_level, selling_price
        FROM products
        WHERE business_id = ?
    """,
        (business_id,),
    )
    items = cursor.fetchall()
    conn.close()
    if not items:
        print("No products found in inventory.")
        return
    print(f"\n📋 === INVENTORY & REORDER LEVELS (Shop ID: {business_id}) ===")
    for item in items:
        status = (
            "⚠️ LOW" if item["stock_quantity"] <= item["reorder_level"] else "✅ OK"
        )
        print(
            f"ID: {item['product_id']} | {item['product_name']:<15} | Stock:"
            f" {item['stock_quantity']:<6} | Reorder At:"
            f" {item['reorder_level']:<6} | Status: {status}"
        )
    print("-" * 65)

def update_reorder_level(product_id, new_reorder_level):
    """Updates the low-stock threshold for an existing product."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE products
        SET reorder_level = ?
        WHERE product_id = ?
    """,
        (new_reorder_level, product_id),
    )
    conn.commit()
    conn.close()
    print(
        f"✅ Updated Product ID {product_id} reorder level to"
        f" {new_reorder_level}."
    )

# --- 3. IN-APP POPUP NOTIFICATIONS & DASHBOARD ALERTS ---
def run_biashara_alerts(business_id=None, lang="en"):
    """Fires clean in-app notification popups for low stock warnings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("\n" + "=" * 50)
    print("🔔 📱 [BIASHARA IN-APP NOTIFICATION CENTER]")
    print("=" * 50)
    # --- LOW STOCK WARNINGS ---
    if business_id:
        cursor.execute(
            """
            SELECT p.product_name, p.stock_quantity, p.reorder_level, b.business_name
            FROM products p
            JOIN businesses b ON p.business_id = b.business_id
            WHERE p.business_id = ? AND p.stock_quantity <= p.reorder_level
        """,
            (business_id,),
        )
    else:
        cursor.execute("""
            SELECT p.product_name, p.stock_quantity, p.reorder_level, b.business_name
            FROM products p
            JOIN businesses b ON p.business_id = b.business_id
            WHERE p.stock_quantity <= p.reorder_level
        """)
    stock_alerts = cursor.fetchall()
    print("\n📦 [Inventory Stock Alerts]")
    if stock_alerts:
        for alert in stock_alerts:
            print(
                f"  ⚠️ ALERT: '{alert['product_name']}' ({alert['business_name']})"
                f" is running low! Left: {alert['stock_quantity']} (Threshold:"
                f" {alert['reorder_level']})"
            )
    else:
        print("  ✅ All stock levels are healthy. No inventory warnings.")
    print("\n" + "=" * 50)
    conn.close()

# --- 4. TRANSACTIONS (SALES & EXPENSES) [UPDATED WITH PAYMENTS] ---
def record_sale(business_id, sale_items_list, payment_method="Cash", payment_reference=None, lang="en"):
    """Records a sale transaction, updates inventory stock levels, logs line items,
    saves payment information, and triggers automatic low-stock alerts if thresholds are breached.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate total amount
    total_amount = sum(
        item["quantity"] * item["unit_price"] for item in sale_items_list
    )

    clean_ref = payment_reference.strip().upper() if payment_reference else None
    
    # Insert sale header with payment method and reference
    cursor.execute(
        """
        INSERT INTO sales (business_id, total_amount, payment_method, payment_reference)
        VALUES (?, ?, ?, ?)
    """,
        (business_id, total_amount, payment_method, clean_ref),
    )
    sale_id = cursor.lastrowid
    
    # Insert line items, deduct stock, and check restock levels
    for item in sale_items_list:
        cursor.execute(
            """
            INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
        """,
            (sale_id, item["product_id"], item["quantity"], item["unit_price"]),
        )
        
        # Automatically deduct stock quantity
        cursor.execute(
            """
            UPDATE products 
            SET stock_quantity = stock_quantity - ? 
            WHERE product_id = ?
        """,
            (item["quantity"], item["product_id"]),
        )
        
        # --- AUTOMATIC RESTOCK ALERT CHECK ---
        cursor.execute(
            """
            SELECT product_name, stock_quantity, reorder_level 
            FROM products WHERE product_id = ?
        """,
            (item["product_id"],),
        )
        prod = cursor.fetchone()
        if prod and prod["stock_quantity"] <= prod["reorder_level"]:
            print("\n" + "!" * 50)
            print(f"🚨 **AUTOMATIC RESTOCK ALERT** 🚨")
            print(
                f"• Product: '{prod['product_name']}' is running critically low!"
                f" Remaining Stock: {prod['stock_quantity']} (Reorder Level:"
                f" {prod['reorder_level']})"
            )
            print("!" * 50 + "\n")