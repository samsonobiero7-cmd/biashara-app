import sqlite3
from translations import get_text
DB_NAME = "biashara_manager.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
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
    
    # Insert sale header with payment method and reference
    cursor.execute(
        """
        INSERT INTO sales (business_id, total_amount, payment_method, payment_reference)
        VALUES (?, ?, ?, ?)
    """,
        (business_id, total_amount, payment_method, payment_reference),
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
            
    conn.commit()
    conn.close()
    
    ref_text = f" (Ref: {payment_reference})" if payment_reference else ""
    print(
        f"✅ Sale recorded successfully! ID: {sale_id} | Total: KES {total_amount} | Paid via: {payment_method}{ref_text}"
    )
    return sale_id

def record_expense(business_id, category, amount, description="", lang="en"):
    """Records an operational overhead or business expense."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO expenses (business_id, category, amount, description)
        VALUES (?, ?, ?, ?)
    """,
        (business_id, category, amount, description),
    )
    conn.commit()
    conn.close()
    print(
        f"✅ Expense logged: KES {amount} under category '{category}' -"
        f" {description}"
    )

# --- 5. DAILY REPORTING ---
def get_daily_summary(lang="en"):
    """Fetches the aggregated daily financial and activity summary across shops."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_business_summary")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        print(get_text("no_activity", lang=lang))
        return
    print(get_text("summary_title", lang=lang))
    for row in rows:
        date_val = row["activity_date"] or get_text("no_activity_date", lang=lang)
        print(f"Biashara: {row['business_name']}")
        print(f"  - Date / Tarehe: {date_val}")
        print(f"  - Transactions / Mauzo: {row['total_transactions']}")
        print(f"  - Revenue / Mapato: {row['total_revenue']}")
        print(f"  - Expenses / Matumizi: {row['total_expenses']}")
        print(f"  - Restock Cost / Gharama za Bidhaa: {row['total_restock_cost']}")
        print("-" * 40)

# --- 6. ADVANCED INVENTORY RESTOCKING (PURCHASES) ---
def record_purchase(business_id, supplier_id, purchase_items_list, notes="", lang="en"):
    """
    Records a restock purchase from a supplier, automatically increases 
    product stock levels, and updates buying prices if changed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate total purchase cost
        total_cost = sum(item['quantity_added'] * item['unit_buying_price'] for item in purchase_items_list)
        
        # Insert purchase header
        cursor.execute("""
            INSERT INTO purchases (business_id, supplier_id, total_cost, notes)
            VALUES (?, ?, ?, ?)
        """, (business_id, supplier_id, total_cost, notes))
        purchase_id = cursor.lastrowid
        
        # Process each restocked item
        for item in purchase_items_list:
            cursor.execute("""
                INSERT INTO purchase_items (purchase_id, product_id, quantity_added, unit_buying_price)
                VALUES (?, ?, ?, ?)
            """, (purchase_id, item['product_id'], item['quantity_added'], item['unit_buying_price']))
            
            # Automatically increase stock quantity and update buying price
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity + ?, 
                    buying_price = ?
                WHERE product_id = ?
            """, (item['quantity_added'], item['unit_buying_price'], item['product_id']))
            
        conn.commit()
        print(f"✅ Restock purchase recorded successfully! Purchase ID: {purchase_id}, Total Cost: KES {total_cost}")
        return purchase_id
    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Error recording purchase, transaction rolled back: {e}")
        return None
    finally:
        conn.close()

# --- 7. SAFE TRANSACTION WRAPPER WITH INVENTORY VALIDATION [UPDATED WITH PAYMENTS] ---
def record_sale_secure(business_id, sale_items_list, payment_method="Cash", payment_reference=None, lang="en"):
    """
    Records a sale with strict validation: checks if stock is sufficient 
    BEFORE executing, includes payment method/reference tracking, and uses 
    database transactions (rollback) to prevent partial or corrupt states.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Pre-check inventory availability for all items
        for item in sale_items_list:
            cursor.execute("SELECT product_name, stock_quantity FROM products WHERE product_id = ?", (item['product_id'],))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Product ID {item['product_id']} does not exist.")
            if prod['stock_quantity'] < item['quantity']:
                raise ValueError(f"❌ Insufficient stock for '{prod['product_name']}'. Available: {prod['stock_quantity']}, Requested: {item['quantity']}")
                
        # Step 2: Calculate total and insert sale header with payment info
        total_amount = sum(item['quantity'] * item['unit_price'] for item in sale_items_list)
        cursor.execute("""
            INSERT INTO sales (business_id, total_amount, payment_method, payment_reference)
            VALUES (?, ?, ?, ?)
        """, (business_id, total_amount, payment_method, payment_reference))
        sale_id = cursor.lastrowid
        
        # Step 3: Insert line items and deduct stock safely
        for item in sale_items_list:
            cursor.execute("""
                INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (sale_id, item['product_id'], item['quantity'], item['unit_price']))
            
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity - ? 
                WHERE product_id = ?
            """, (item['quantity'], item['product_id']))
            
            # Check for low stock notification
            cursor.execute("SELECT product_name, stock_quantity, reorder_level FROM products WHERE product_id = ?", (item['product_id'],))
            prod = cursor.fetchone()
            if prod and prod['stock_quantity'] <= prod['reorder_level']:
                print(f"\n🚨 **AUTOMATIC RESTOCK ALERT**: '{prod['product_name']}' is low! Left: {prod['stock_quantity']} (Threshold: {prod['reorder_level']})")
                
        conn.commit()
        ref_text = f" (Ref: {payment_reference})" if payment_reference else ""
        print(f"✅ Secure sale recorded successfully! ID: {sale_id} | Total: KES {total_amount} | Paid via: {payment_method}{ref_text}")
        return sale_id
        
    except Exception as e:
        conn.rollback() # Revert all database changes if anything fails
        print(f"❌ Transaction Failed & Rolled Back: {e}")
        return None
    finally:
        conn.close()