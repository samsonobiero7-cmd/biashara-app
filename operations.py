import json
import math
from datetime import datetime, timezone
from uuid import UUID

from database import get_db_connection


def _normalized_email(owner_email):
    normalized = (owner_email or "").strip().lower()
    if not normalized:
        raise ValueError("A signed-in owner email is required.")
    return normalized


def _assert_business_owner(cursor, business_id, owner_email):
    cursor.execute(
        """
        SELECT 1
        FROM businesses
        WHERE business_id = %s AND owner_email = %s
        """,
        (business_id, owner_email),
    )
    if cursor.fetchone() is None:
        raise PermissionError("Business not found or access denied.")


def register_business(business_name, business_type, owner_email, lang="en"):
    owner_email = _normalized_email(owner_email)
    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO businesses (owner_email, business_name, business_type)
                    VALUES (%s, %s, %s)
                    RETURNING business_id
                    """,
                    (owner_email, business_name.strip(), business_type),
                )
                business_id = cursor.fetchone()["business_id"]
        return business_id
    finally:
        conn.close()


def register_business_fields(business_id, field_names, owner_email):
    owner_email = _normalized_email(owner_email)
    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                for name in field_names:
                    field_name = name.strip()
                    if field_name:
                        cursor.execute(
                            """
                            INSERT INTO business_fields (business_id, field_name)
                            VALUES (%s, %s)
                            ON CONFLICT (business_id, field_name)
                            DO NOTHING
                            """,
                            (business_id, field_name),
                        )
    finally:
        conn.close()


def add_product_with_custom_fields(
    business_id,
    product_name,
    buying_price,
    selling_price,
    stock_quantity,
    owner_email,
    supplier_id=None,
    reorder_level=5.0,
    custom_fields=None,
):
    owner_email = _normalized_email(owner_email)
    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                cursor.execute(
                    """
                    INSERT INTO products (
                        business_id, product_name, buying_price, selling_price,
                        stock_quantity, reorder_level
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING product_id
                    """,
                    (
                        business_id,
                        product_name.strip(),
                        buying_price,
                        selling_price,
                        stock_quantity,
                        reorder_level,
                    ),
                )
                product_id = cursor.fetchone()["product_id"]

                for field_name, value in (custom_fields or {}).items():
                    field_name = field_name.strip()
                    if not field_name:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO business_fields (business_id, field_name)
                        VALUES (%s, %s)
                        ON CONFLICT (business_id, field_name)
                        DO UPDATE SET field_name = EXCLUDED.field_name
                        RETURNING field_id
                        """,
                        (business_id, field_name),
                    )
                    field_id = cursor.fetchone()["field_id"]
                    cursor.execute(
                        """
                        INSERT INTO product_field_values (product_id, field_id, field_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (product_id, field_id)
                        DO UPDATE SET field_value = EXCLUDED.field_value
                        """,
                        (product_id, field_id, str(value)),
                    )
        return product_id
    finally:
        conn.close()


def add_offline_product(
    business_id,
    product_name,
    buying_price,
    selling_price,
    stock_quantity,
    owner_email,
    offline_product_id,
    reorder_level=5.0,
):
    owner_email = _normalized_email(owner_email)
    try:
        offline_product_id = UUID(str(offline_product_id))
        product_name = str(product_name or "").strip()
        buying_price = float(buying_price)
        selling_price = float(selling_price)
        stock_quantity = float(stock_quantity)
        reorder_level = float(reorder_level)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("Offline product details are invalid.") from error

    if not product_name:
        raise ValueError("Offline product name is required.")
    if any(
        not math.isfinite(value) or value < 0
        for value in (buying_price, selling_price, stock_quantity, reorder_level)
    ):
        raise ValueError("Offline product values must be finite and zero or greater.")

    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                cursor.execute(
                    """
                    SELECT product_id, business_id
                    FROM products
                    WHERE offline_product_id = %s
                    """,
                    (offline_product_id,),
                )
                existing_product = cursor.fetchone()
                if existing_product is not None:
                    if existing_product["business_id"] != business_id:
                        raise PermissionError(
                            "Offline product ID is already used by another business."
                        )
                    return existing_product["product_id"]

                cursor.execute(
                    """
                    SELECT 1
                    FROM products
                    WHERE business_id = %s
                      AND LOWER(BTRIM(product_name)) = LOWER(%s)
                    LIMIT 1
                    """,
                    (business_id, product_name),
                )
                if cursor.fetchone() is not None:
                    raise ValueError(
                        "A product with this name already exists. Refresh the "
                        "offline catalog and select the existing product."
                    )

                cursor.execute(
                    """
                    INSERT INTO products (
                        business_id, product_name, buying_price, selling_price,
                        stock_quantity, reorder_level, offline_product_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (offline_product_id)
                        WHERE offline_product_id IS NOT NULL
                    DO NOTHING
                    RETURNING product_id
                    """,
                    (
                        business_id,
                        product_name,
                        buying_price,
                        selling_price,
                        stock_quantity,
                        reorder_level,
                        offline_product_id,
                    ),
                )
                inserted_product = cursor.fetchone()
                if inserted_product is not None:
                    return inserted_product["product_id"]

                cursor.execute(
                    """
                    SELECT product_id, business_id
                    FROM products
                    WHERE offline_product_id = %s
                    """,
                    (offline_product_id,),
                )
                existing_product = cursor.fetchone()
                if existing_product is None:
                    raise RuntimeError(
                        "Offline product could not be found after a duplicate insert."
                    )
                if existing_product["business_id"] != business_id:
                    raise PermissionError(
                        "Offline product ID is already used by another business."
                    )
                return existing_product["product_id"]
    finally:
        conn.close()


def record_sale_secure(
    business_id,
    sale_items_list,
    owner_email,
    payment_method="Cash",
    payment_reference=None,
    lang="en",
    offline_sale_id=None,
    offline_sale_date=None,
):
    owner_email = _normalized_email(owner_email)
    if not sale_items_list:
        raise ValueError("A sale must contain at least one item.")
    if any(
        not math.isfinite(float(item["quantity"])) or float(item["quantity"]) <= 0
        for item in sale_items_list
    ):
        raise ValueError("Sale quantities must be greater than zero.")
    if any(
        not math.isfinite(float(item["unit_price"])) or float(item["unit_price"]) < 0
        for item in sale_items_list
    ):
        raise ValueError("Sale prices must be zero or greater.")
    if offline_sale_id is not None:
        try:
            offline_sale_id = UUID(str(offline_sale_id))
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError("Offline sale ID must be a valid UUID.") from error
        if offline_sale_date is not None:
            try:
                offline_sale_date = datetime.fromisoformat(
                    str(offline_sale_date).replace("Z", "+00:00")
                )
            except ValueError as error:
                raise ValueError("Offline sale date must be a valid ISO timestamp.") from error
            if offline_sale_date.tzinfo is None:
                offline_sale_date = offline_sale_date.replace(tzinfo=timezone.utc)

    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                if offline_sale_id is not None:
                    cursor.execute(
                        """
                        SELECT sale_id, business_id
                        FROM sales
                        WHERE offline_sale_id = %s
                        """,
                        (offline_sale_id,),
                    )
                    existing_sale = cursor.fetchone()
                    if existing_sale is not None:
                        if existing_sale["business_id"] != business_id:
                            raise PermissionError(
                                "Offline sale ID is already used by another business."
                            )
                        return existing_sale["sale_id"]

                quantities_by_product = {}
                for item in sale_items_list:
                    product_id = item["product_id"]
                    quantities_by_product[product_id] = (
                        quantities_by_product.get(product_id, 0)
                        + float(item["quantity"])
                    )

                for product_id, quantity in quantities_by_product.items():
                    cursor.execute(
                        """
                        SELECT stock_quantity
                        FROM products
                        WHERE product_id = %s AND business_id = %s
                        FOR UPDATE
                        """,
                        (product_id, business_id),
                    )
                    product = cursor.fetchone()
                    if product is None or (
                        offline_sale_id is None
                        and quantity > product["stock_quantity"]
                    ):
                        return None

                total_amount = sum(
                    float(item["quantity"]) * float(item["unit_price"])
                    for item in sale_items_list
                )
                if not math.isfinite(total_amount):
                    raise ValueError("Sale total must be a finite amount.")
                clean_reference = (
                    payment_reference.strip().upper() if payment_reference else None
                )
                if offline_sale_id is None:
                    cursor.execute(
                        """
                        INSERT INTO sales (
                            business_id, total_amount, payment_method, payment_reference
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING sale_id
                        """,
                        (business_id, total_amount, payment_method, clean_reference),
                    )
                    sale_id = cursor.fetchone()["sale_id"]
                else:
                    cursor.execute(
                        """
                        INSERT INTO sales (
                            business_id, total_amount, payment_method,
                            payment_reference, offline_sale_id, sale_date
                        )
                        VALUES (%s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
                        ON CONFLICT (offline_sale_id)
                            WHERE offline_sale_id IS NOT NULL
                        DO NOTHING
                        RETURNING sale_id
                        """,
                        (
                            business_id,
                            total_amount,
                            payment_method,
                            clean_reference,
                            offline_sale_id,
                            offline_sale_date,
                        ),
                    )
                    inserted_sale = cursor.fetchone()
                    if inserted_sale is None:
                        cursor.execute(
                            """
                            SELECT sale_id, business_id
                            FROM sales
                            WHERE offline_sale_id = %s
                            """,
                            (offline_sale_id,),
                        )
                        existing_sale = cursor.fetchone()
                        if existing_sale is None:
                            raise RuntimeError(
                                "Offline sale could not be found after a duplicate insert."
                            )
                        if existing_sale["business_id"] != business_id:
                            raise PermissionError(
                                "Offline sale ID is already used by another business."
                            )
                        return existing_sale["sale_id"]
                    sale_id = inserted_sale["sale_id"]

                for item in sale_items_list:
                    quantity = float(item["quantity"])
                    cursor.execute(
                        """
                        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (sale_id, item["product_id"], quantity, item["unit_price"]),
                    )
                    cursor.execute(
                        """
                        UPDATE products
                        SET stock_quantity = stock_quantity - %s
                        WHERE product_id = %s AND business_id = %s
                        """,
                        (quantity, item["product_id"], business_id),
                    )
        return sale_id
    finally:
        conn.close()


def record_expense(business_id, category, amount, description, owner_email):
    owner_email = _normalized_email(owner_email)
    if float(amount) <= 0:
        raise ValueError("Expense amount must be greater than zero.")
    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                cursor.execute(
                    """
                    INSERT INTO expenses (business_id, category, amount, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING expense_id
                    """,
                    (business_id, category, amount, description),
                )
                return cursor.fetchone()["expense_id"]
    finally:
        conn.close()


def record_purchase(
    business_id,
    purchase_items_list,
    owner_email,
    supplier_id=None,
    notes=None,
    lang="en",
):
    owner_email = _normalized_email(owner_email)
    if not purchase_items_list:
        raise ValueError("A purchase must contain at least one item.")
    if any(float(item["quantity_added"]) <= 0 for item in purchase_items_list):
        raise ValueError("Restock quantities must be greater than zero.")

    conn = get_db_connection()
    try:
        with conn.transaction():
            with conn.cursor() as cursor:
                _assert_business_owner(cursor, business_id, owner_email)
                for item in purchase_items_list:
                    cursor.execute(
                        """
                        SELECT 1 FROM products
                        WHERE product_id = %s AND business_id = %s
                        FOR UPDATE
                        """,
                        (item["product_id"], business_id),
                    )
                    if cursor.fetchone() is None:
                        raise PermissionError("Product not found in this business.")

                total_cost = sum(
                    float(item["quantity_added"])
                    * float(item["unit_buying_price"])
                    for item in purchase_items_list
                )
                cursor.execute(
                    """
                    INSERT INTO purchases (business_id, total_cost, notes)
                    VALUES (%s, %s, %s)
                    RETURNING purchase_id
                    """,
                    (business_id, total_cost, notes),
                )
                purchase_id = cursor.fetchone()["purchase_id"]

                for item in purchase_items_list:
                    quantity = float(item["quantity_added"])
                    cursor.execute(
                        """
                        INSERT INTO purchase_items (
                            purchase_id, product_id, quantity_added,
                            unit_buying_price
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            purchase_id,
                            item["product_id"],
                            quantity,
                            item["unit_buying_price"],
                        ),
                    )
                    cursor.execute(
                        """
                        UPDATE products
                        SET stock_quantity = stock_quantity + %s,
                            buying_price = %s
                        WHERE product_id = %s AND business_id = %s
                        """,
                        (
                            quantity,
                            item["unit_buying_price"],
                            item["product_id"],
                            business_id,
                        ),
                    )
        return purchase_id
    finally:
        conn.close()


def get_owner_backup(owner_email):
    owner_email = _normalized_email(owner_email)
    table_queries = {
        "businesses": """
            SELECT business_id, owner_email, business_name, business_type, created_at
            FROM businesses WHERE owner_email = %s ORDER BY business_id
        """,
        "products": """
            SELECT p.* FROM products p
            JOIN businesses b ON b.business_id = p.business_id
            WHERE b.owner_email = %s ORDER BY p.product_id
        """,
        "sales": """
            SELECT s.* FROM sales s
            JOIN businesses b ON b.business_id = s.business_id
            WHERE b.owner_email = %s ORDER BY s.sale_id
        """,
        "sale_items": """
            SELECT si.* FROM sale_items si
            JOIN sales s ON s.sale_id = si.sale_id
            JOIN businesses b ON b.business_id = s.business_id
            WHERE b.owner_email = %s ORDER BY si.sale_item_id
        """,
        "expenses": """
            SELECT e.* FROM expenses e
            JOIN businesses b ON b.business_id = e.business_id
            WHERE b.owner_email = %s ORDER BY e.expense_id
        """,
        "purchases": """
            SELECT p.* FROM purchases p
            JOIN businesses b ON b.business_id = p.business_id
            WHERE b.owner_email = %s ORDER BY p.purchase_id
        """,
        "purchase_items": """
            SELECT pi.* FROM purchase_items pi
            JOIN purchases p ON p.purchase_id = pi.purchase_id
            JOIN businesses b ON b.business_id = p.business_id
            WHERE b.owner_email = %s ORDER BY pi.purchase_item_id
        """,
        "business_fields": """
            SELECT bf.* FROM business_fields bf
            JOIN businesses b ON b.business_id = bf.business_id
            WHERE b.owner_email = %s ORDER BY bf.field_id
        """,
        "product_field_values": """
            SELECT pfv.* FROM product_field_values pfv
            JOIN products p ON p.product_id = pfv.product_id
            JOIN businesses b ON b.business_id = p.business_id
            WHERE b.owner_email = %s ORDER BY pfv.product_id, pfv.field_id
        """,
    }

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            backup = {}
            for table, query in table_queries.items():
                cursor.execute(query, (owner_email,))
                backup[table] = cursor.fetchall()
        backup_data = {
            "format_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "owner_email": owner_email,
            "tables": backup,
        }
        return json.dumps(backup_data, default=str, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )
    finally:
        conn.close()
