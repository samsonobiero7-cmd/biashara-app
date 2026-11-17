import sqlite3

def create_biashara_database():
    conn = sqlite3.connect("biashara_manager.db")
    cursor = conn.cursor()

    # 1. Businesses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            business_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            business_type TEXT NOT NULL
        )
    """)

    # 2. Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            product_name TEXT NOT NULL,
            buying_price REAL DEFAULT 0.0,
            selling_price REAL DEFAULT 0.0,
            stock_quantity REAL DEFAULT 0.0,
            reorder_level REAL DEFAULT 5.0,
            FOREIGN KEY (business_id) REFERENCES businesses(business_id)
        )
    """)

    # 3. Sales Table (with comprehensive payment support & reference codes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL DEFAULT 0.0,
            payment_method TEXT DEFAULT 'Cash',
            payment_reference TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses(business_id)
        )
    """)

    # Safely migrate/add columns if upgrading an older database version
    cursor.execute("PRAGMA table_info(sales)")
    sales_cols = [col[1] for col in cursor.fetchall()]
    
    if "payment_method" not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
        
    if "payment_reference" not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN payment_reference TEXT")

    # 4. Sale Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # 5. Expenses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses(business_id)
        )
    """)

    # 6. Purchases / Restocks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            supplier_name TEXT,
            total_cost REAL DEFAULT 0.0,
            notes TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses(business_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_items (
            purchase_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER,
            product_id INTEGER,
            quantity_added REAL NOT NULL,
            unit_buying_price REAL NOT NULL,
            FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # 7. Financial & Daily Summary View
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS daily_business_summary AS
        SELECT 
            b.business_id,
            b.business_name,
            COUNT(DISTINCT s.sale_id) AS total_transactions,
            SUM(s.total_amount) AS total_revenue,
            (SELECT SUM(amount) FROM expenses e WHERE e.business_id = b.business_id) AS total_expenses,
            (SELECT SUM(total_cost) FROM purchases pr WHERE pr.business_id = b.business_id) AS total_restock_cost
        FROM businesses b
        LEFT JOIN sales s ON b.business_id = s.business_id
        GROUP BY b.business_id, b.business_name
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_biashara_database()
    print("Database schema created/updated successfully with payment tracking.")