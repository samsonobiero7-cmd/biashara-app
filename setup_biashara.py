from database import get_db_connection


def create_biashara_database():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    business_id BIGSERIAL PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    business_name TEXT NOT NULL,
                    business_type TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id BIGSERIAL PRIMARY KEY,
                    business_id BIGINT NOT NULL REFERENCES businesses(business_id),
                    product_name TEXT NOT NULL,
                    buying_price DOUBLE PRECISION NOT NULL DEFAULT 0,
                    selling_price DOUBLE PRECISION NOT NULL DEFAULT 0,
                    stock_quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
                    reorder_level DOUBLE PRECISION NOT NULL DEFAULT 5
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id BIGSERIAL PRIMARY KEY,
                    business_id BIGINT NOT NULL REFERENCES businesses(business_id),
                    sale_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                    payment_method TEXT NOT NULL DEFAULT 'Cash',
                    payment_reference TEXT,
                    offline_sale_id UUID
                )
            """)
            cursor.execute("""
                ALTER TABLE sales
                ADD COLUMN IF NOT EXISTS offline_sale_id UUID
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_offline_sale_id
                ON sales (offline_sale_id)
                WHERE offline_sale_id IS NOT NULL
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    sale_item_id BIGSERIAL PRIMARY KEY,
                    sale_id BIGINT NOT NULL REFERENCES sales(sale_id),
                    product_id BIGINT NOT NULL REFERENCES products(product_id),
                    quantity DOUBLE PRECISION NOT NULL,
                    unit_price DOUBLE PRECISION NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    expense_id BIGSERIAL PRIMARY KEY,
                    business_id BIGINT NOT NULL REFERENCES businesses(business_id),
                    expense_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    category TEXT NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    description TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    purchase_id BIGSERIAL PRIMARY KEY,
                    business_id BIGINT NOT NULL REFERENCES businesses(business_id),
                    purchase_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
                    notes TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchase_items (
                    purchase_item_id BIGSERIAL PRIMARY KEY,
                    purchase_id BIGINT NOT NULL REFERENCES purchases(purchase_id),
                    product_id BIGINT NOT NULL REFERENCES products(product_id),
                    quantity_added DOUBLE PRECISION NOT NULL,
                    unit_buying_price DOUBLE PRECISION NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_fields (
                    field_id BIGSERIAL PRIMARY KEY,
                    business_id BIGINT NOT NULL REFERENCES businesses(business_id),
                    field_name TEXT NOT NULL,
                    UNIQUE (business_id, field_name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_field_values (
                    product_id BIGINT NOT NULL REFERENCES products(product_id),
                    field_id BIGINT NOT NULL REFERENCES business_fields(field_id),
                    field_value TEXT NOT NULL,
                    PRIMARY KEY (product_id, field_id)
                )
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_unique_payment_ref
                ON sales (business_id, payment_reference)
                WHERE payment_reference IS NOT NULL AND BTRIM(payment_reference) <> ''
            """)
            cursor.execute("""
                CREATE OR REPLACE VIEW daily_sales_view AS
                SELECT
                    s.sale_id,
                    s.business_id,
                    s.sale_date::date AS sale_day,
                    s.sale_date,
                    p.product_name,
                    si.quantity,
                    si.unit_price,
                    p.buying_price,
                    si.quantity * si.unit_price AS total,
                    si.quantity * (si.unit_price - COALESCE(p.buying_price, 0))
                        AS estimated_profit,
                    s.payment_method,
                    s.payment_reference
                FROM sales s
                JOIN sale_items si ON s.sale_id = si.sale_id
                JOIN products p ON si.product_id = p.product_id
            """)
            cursor.execute("""
                CREATE OR REPLACE VIEW daily_business_summary AS
                SELECT
                    b.business_id,
                    b.owner_email,
                    b.business_name,
                    COUNT(DISTINCT s.sale_id) AS total_transactions,
                    SUM(s.total_amount) AS total_revenue,
                    (SELECT SUM(e.amount) FROM expenses e
                     WHERE e.business_id = b.business_id) AS total_expenses,
                    (SELECT SUM(p.total_cost) FROM purchases p
                     WHERE p.business_id = b.business_id) AS total_restock_cost
                FROM businesses b
                LEFT JOIN sales s ON s.business_id = b.business_id
                GROUP BY b.business_id, b.owner_email, b.business_name
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
