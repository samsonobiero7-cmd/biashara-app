import streamlit as st
import pandas as pd
from datetime import date
import setup_biashara
import operations
from translations import get_text

# ------------------------------------------------------------
# BIASHARA — SQLite-Backed Business Manager & POS
# ------------------------------------------------------------

st.set_page_config(
    page_title="Biashara | Business Manager",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Forest-Green & Clean Card Styling (Forced High Contrast) ----------
st.markdown("""
<style>
:root { --green:#16764a; }
.stApp { background:#ffffff !important; color:#172b22 !important; }
[data-testid="stSidebar"] { background:#102c22 !important; }
[data-testid="stSidebar"] * { color:#f3f8f5 !important; }
.block-container { padding-top:1.5rem; padding-bottom:3rem; max-width:1500px; }
h1, h2, h3, h4, h5, h6, span, p, label { color:#172b22 !important; }
div[data-testid="stMetric"] {
  background:#ffffff; border:1px solid #e5ece8; padding:16px;
  border-radius:14px;
}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {
  color:#172b22 !important;
}
.stButton > button, .stFormSubmitButton > button {
  border-radius:10px; min-height:42px; font-weight:600;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background:#16764a !important; border-color:#16764a !important; color:white !important;
}
.small-muted { color:#718078 !important; font-size:0.88rem; }
div[data-testid="stDataFrame"] { border-radius:12px; }
</style>
""", unsafe_allow_html=True)

# ---------- Initialize SQLite Database ----------
setup_biashara.create_biashara_database()
conn = operations.get_db_connection()

if "custom_attributes" not in st.session_state:
    st.session_state.custom_attributes = {}

# Default language setting
lang = "en"

def money(value):
    return f"KSh {float(value or 0):,.2f}"

# ---------- Database Helper Queries ----------
def get_all_businesses():
    cur = conn.cursor()
    cur.execute("SELECT business_id, business_name, business_type FROM businesses ORDER BY business_id ASC")
    return [dict(row) for row in cur.fetchall()]

def get_business_products(bid):
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id, product_name, buying_price, selling_price, stock_quantity, reorder_level
        FROM products WHERE business_id = ? ORDER BY product_name ASC
    """, (bid,))
    return [dict(row) for row in cur.fetchall()]

def get_business_sales(bid):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.sale_id, DATE(s.sale_date) AS sale_day, s.sale_date,
               p.product_name, si.quantity, si.unit_price, p.buying_price,
               (si.quantity * si.unit_price) AS total,
               (si.quantity * (si.unit_price - COALESCE(p.buying_price, 0))) AS estimated_profit,
               s.payment_method, s.payment_reference
        FROM sales s
        JOIN sale_items si ON s.sale_id = si.sale_id
        JOIN products p ON si.product_id = p.product_id
        WHERE s.business_id = ?
        ORDER BY s.sale_date DESC
    """, (bid,))
    return [dict(row) for row in cur.fetchall()]

def get_business_expenses(bid):
    cur = conn.cursor()
    cur.execute("""
        SELECT expense_id, DATE(expense_date) AS expense_day, expense_date,
               category, amount, description
        FROM expenses
        WHERE business_id = ?
        ORDER BY expense_date DESC
    """, (bid,))
    return [dict(row) for row in cur.fetchall()]

def get_business_summary(bid):
    cur = conn.cursor()
    cur.execute("SELECT * FROM daily_business_summary WHERE business_id = ?", (bid,))
    row = cur.fetchone()
    return dict(row) if row else None

# ---------- Sidebar ----------
businesses = get_all_businesses()

with st.sidebar:
    st.markdown("# 🟢 Biashara")
    st.caption("Your business, made simpler.")
    st.divider()

    if businesses:
        biz_map = {b["business_name"]: b for b in businesses}
        names = list(biz_map.keys())
        default_idx = names.index(st.session_state["active_business"]) if st.session_state.get("active_business") in names else 0
        chosen_name = st.selectbox("CURRENT BUSINESS", names, index=default_idx)
        st.session_state.active_business = chosen_name
        biz = biz_map[chosen_name]
    else:
        biz = None
        st.info("Add your first business to get started.")

    st.divider()
    pages = {
        "🏠  Overview": "Overview",
        "🏪  My businesses": "Businesses",
        "📦  Products & stock": "Products",
        "🛒  Record a sale": "Sales",
        "💸  Expenses": "Expenses",
        "📦  Supplier restocks": "Restocks",
        "📅  Daily records": "Daily records",
        "📊  Reports": "Reports",
    }
    page_label = st.radio("MENU", list(pages.keys()), label_visibility="collapsed")
    page = pages[page_label]
    st.divider()
    st.caption("Simple tools for everyday business.")
    st.caption("Biashara • Connected to SQLite")

if not biz and page != "Businesses":
    st.warning("Add your first business using **🏪 My businesses** in the sidebar.")
    st.stop()

# ---------- Header Helper ----------
def page_header(title, subtitle):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.title(title)
        st.caption(subtitle)
    with c2:
        st.write("")
        st.write(f"**{date.today().strftime('%d %b %Y')}**")
    st.divider()

# ============================================================
# 1. OVERVIEW
# ============================================================
if page == "Overview":
    page_header("Good morning 👋", f"Here's what's happening at {biz['business_name']} today.")

    today_str = date.today().isoformat()
    all_sales = get_business_sales(biz["business_id"])
    all_expenses = get_business_expenses(biz["business_id"])
    products = get_business_products(biz["business_id"])

    todays_sales = [s for s in all_sales if s["sale_day"] == today_str]
    todays_expenses = [e for e in all_expenses if e["expense_day"] == today_str]
    low_stock = [p for p in products if p["stock_quantity"] <= p["reorder_level"]]

    a, b, c, d = st.columns(4)
    a.metric("Today's sales", money(sum(s["total"] for s in todays_sales)))
    b.metric("Today's expenses", money(sum(e["amount"] for e in todays_expenses)))
    c.metric("Products", len(products))
    d.metric("Low-stock items", len(low_stock))

    st.write("")
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown("### Recent sales")
        if all_sales:
            df_recent = pd.DataFrame(all_sales[:8])[[
                "sale_day", "product_name", "quantity", "unit_price", "total", "payment_method"
            ]].rename(
                columns={
                    "sale_day": "Date",
                    "product_name": "Product",
                    "quantity": "Qty",
                    "unit_price": "Unit Price",
                    "total": "Total (KSh)",
                    "payment_method": "Paid Via"
                }
            )
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("No sales recorded yet. Use **🛒 Record a sale** in the sidebar to log your first transaction.")

    with right:
        st.markdown("### Stock to check")
        if low_stock:
            for p in low_stock[:6]:
                st.warning(f"**{p['product_name']}** — {p['stock_quantity']:g} units left (Alert below {p['reorder_level']:g})")
        else:
            st.success("You're all caught up. No low-stock alerts.")

# ============================================================
# 2. MY BUSINESSES
# ============================================================
elif page == "Businesses":
    page_header("My businesses", "Manage all the businesses connected to your Biashara database.")
    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown("### Your businesses")
        if businesses:
            df_biz = pd.DataFrame(businesses)[["business_id", "business_name", "business_type"]].rename(
                columns={"business_id": "ID", "business_name": "Business Name", "business_type": "Sector"}
            )
            st.dataframe(df_biz, use_container_width=True, hide_index=True)
        else:
            st.info("You haven't added a business yet.")

    with right:
        st.markdown("### Add a business")
        with st.form("add_business", clear_on_submit=True):
            name = st.text_input("Business name", placeholder="e.g. Mama Njeri's Shop")
            kind = st.selectbox(
                "Business category",
                ["Grocery", "Hardware", "Electrical", "Cereal", "Retail shop", "Other"]
            )
            submitted = st.form_submit_button("＋ Add business", type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("Please enter a business name.")
                else:
                    new_id = operations.register_business(business_name=name.strip(), business_type=kind)
                    st.session_state.active_business = name.strip()
                    st.success(f"{name.strip()} has been added (ID: {new_id}).")
                    st.rerun()
    st.caption("Each business maintains its own separate inventory, sales, and expense records in SQLite.")

# ============================================================
# 3. PRODUCTS & STOCK
# ============================================================
elif page == "Products":
    page_header("Products & stock", f"Keep track of what {biz['business_name']} sells.")
    products = get_business_products(biz["business_id"])
    tab1, tab2, tab3 = st.tabs(["📦 Product list", "＋ Add product", "🏷️ Custom attributes"])

    with tab1:
        if products:
            df = pd.DataFrame(products).rename(columns={
                "product_id": "ID",
                "product_name": "Product",
                "buying_price": "Buying price (KSh)",
                "selling_price": "Selling price (KSh)",
                "stock_quantity": "In stock",
                "reorder_level": "Alert below"
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No products yet. Add your first product in the **＋ Add product** tab.")

    with tab2:
        with st.form("add_product", clear_on_submit=True):
            name = st.text_input("Product name", placeholder="e.g. Sugar 2kg")
            col1, col2 = st.columns(2)
            qty = col1.number_input("Opening stock", min_value=0.0, step=1.0, value=10.0)
            reorder = col2.number_input("Low-stock alert at", min_value=0.0, step=1.0, value=5.0)
            col3, col4 = st.columns(2)
            buy = col3.number_input("Buying price (KSh)", min_value=0.0, step=1.0)
            sell = col4.number_input("Selling price (KSh)", min_value=0.0, step=1.0)

            extra_fields = st.session_state.custom_attributes.get(str(biz["business_id"]), [])
            extras = {}
            if extra_fields:
                st.markdown("**Business-specific details**")
                cols = st.columns(2)
                for i, attr in enumerate(extra_fields):
                    val = cols[i % 2].text_input(attr)
                    if val.strip():
                        extras[attr] = val.strip()

            save = st.form_submit_button("Save product", type="primary", use_container_width=True)
            if save:
                if not name.strip():
                    st.error("Please enter a product name.")
                else:
                    if sell < buy:
                        st.warning("Note: Selling price is lower than buying price.")
                    operations.add_product_with_custom_fields(
                        business_id=biz["business_id"],
                        product_name=name.strip(),
                        buying_price=buy,
                        selling_price=sell,
                        stock_quantity=qty,
                        reorder_level=reorder,
                        custom_fields=extras if extras else None
                    )
                    st.success(f"'{name.strip()}' saved to database.")
                    st.rerun()

    with tab3:
        st.markdown("### Give this business its own product fields")
        st.caption("For example: brand, size, wattage, grain variety, colour or model.")
        current = st.session_state.custom_attributes.get(str(biz["business_id"]), [])
        if current:
            st.write("Current attributes: **" + ", ".join(current) + "**")
        else:
            st.info("No custom attributes added yet for this shop.")

        with st.form("add_attribute", clear_on_submit=True):
            attr = st.text_input("New attribute", placeholder="e.g. Brand")
            add = st.form_submit_button("＋ Add attribute", type="primary")
            if add:
                if not attr.strip():
                    st.error("Enter an attribute name.")
                elif attr.strip().lower() in [x.lower() for x in current]:
                    st.warning("That attribute already exists.")
                else:
                    st.session_state.custom_attributes[str(biz["business_id"])] = current + [attr.strip()]
                    st.success(f"'{attr.strip()}' will now appear when adding products.")
                    st.rerun()

# ============================================================
# 4. RECORD A SALE (UPDATED WITH PAYMENT METHODS & REFERENCES)
# ============================================================
elif page == "Sales":
    page_header("Record a sale", "Log a sale quickly, select payment method, and keep stock updated.")
    products = get_business_products(biz["business_id"])
    left, right = st.columns([1, 1.15], gap="large")

    with left:
        st.markdown("### New sale entry")
        if not products:
            st.info("Add products under **📦 Products & stock** before recording sales.")
        else:
            product_map = {p["product_name"]: p for p in products}
            chosen_name = st.selectbox("What did you sell?", list(product_map.keys()))
            chosen_product = product_map[chosen_name]

            st.caption(
                f"Available: **{chosen_product['stock_quantity']:g} units** • "
                f"Standard price: **{money(chosen_product['selling_price'])}** each"
            )

            with st.form("record_sale_form", clear_on_submit=True):
                qty = st.number_input("Quantity sold", min_value=0.1, value=1.0, step=1.0)
                unit_price = st.number_input(
                    "Selling price per unit (KSh)",
                    min_value=0.0,
                    value=float(chosen_product["selling_price"]),
                    step=1.0
                )
                
                # --- Payment Method Selector & Reference Input ---
                payment_options = ["Cash", "M-Pesa", "Visa / Card", "Bank Transfer"]
                payment_method = st.selectbox(get_text("payment_method", lang=lang), payment_options)
                
                payment_reference = st.text_input(
                    get_text("payment_ref", lang=lang),
                    placeholder="e.g., QGH87XYZ12 (Required for M-Pesa/Card)"
                )

                total = qty * unit_price
                st.info(f"Sale total: **{money(total)}** | Paid via: **{payment_method}**")

                submit = st.form_submit_button("Confirm sale", type="primary", use_container_width=True)
                if submit:
                    if qty > chosen_product["stock_quantity"]:
                        st.error(f"Insufficient stock. Only {chosen_product['stock_quantity']:g} units available.")
                    elif payment_method in ["M-Pesa", "Visa / Card", "Bank Transfer"] and not payment_reference.strip():
                        st.error(f"Please provide a transaction reference code for {payment_method}.")
                    else:
                        sale_items = [{
                            "product_id": chosen_product["product_id"],
                            "quantity": qty,
                            "unit_price": unit_price
                        }]
                        sale_id = operations.record_sale_secure(
                            business_id=biz["business_id"],
                            sale_items_list=sale_items,
                            payment_method=payment_method,
                            payment_reference=payment_reference.strip() if payment_reference else None,
                            lang=lang
                        )
                        if sale_id:
                            st.success(f"Sale #{sale_id} recorded successfully! Total: {money(total)} ({payment_method})")
                            st.rerun()
                        else:
                            st.error("Could not record sale. Please verify stock levels.")

    with right:
        st.markdown("### Recent sales")
        sales = get_business_sales(biz["business_id"])
        if sales:
            df_sales = pd.DataFrame(sales)[[
                "sale_day", "product_name", "quantity", "unit_price", "total", "payment_method", "payment_reference"
            ]].rename(
                columns={
                    "sale_day": "Date",
                    "product_name": "Product",
                    "quantity": "Qty",
                    "unit_price": "Unit Price",
                    "total": "Total (KSh)",
                    "payment_method": "Payment",
                    "payment_reference": "Reference / Code"
                }
            )
            st.dataframe(df_sales, use_container_width=True, hide_index=True)
        else:
            st.info("Your recorded sales will appear here.")

# ============================================================
# 5. EXPENSES
# ============================================================
elif page == "Expenses":
    page_header("Expenses", "Keep an eye on the money going out.")
    left, right = st.columns([1, 1.15], gap="large")

    with left:
        st.markdown("### Add an expense")
        with st.form("add_expense", clear_on_submit=True):
            description = st.text_input("What was the expense for?", placeholder="e.g. Delivery boda boda")
            category = st.selectbox(
                "Expense category",
                ["Transport", "Rent", "Wages", "Utilities", "Packaging", "Other"]
            )
            amount = st.number_input("Amount (KSh)", min_value=0.0, step=50.0)
            submit = st.form_submit_button("Save expense", type="primary", use_container_width=True)
            if submit:
                if not description.strip() or amount <= 0:
                    st.error("Enter a description and an amount greater than zero.")
                else:
                    operations.record_expense(
                        business_id=biz["business_id"],
                        category=category,
                        amount=amount,
                        description=description.strip()
                    )
                    st.success("Expense saved.")
                    st.rerun()

    with right:
        expenses = get_business_expenses(biz["business_id"])
        st.markdown("### Expense history")
        if expenses:
            st.metric("Total recorded expenses", money(sum(e["amount"] for e in expenses)))
            df_exp = pd.DataFrame(expenses)[["expense_day", "description", "category", "amount"]].rename(
                columns={
                    "expense_day": "Date",
                    "description": "Description",
                    "category": "Category",
                    "amount": "Amount (KSh)"
                }
            )
            st.dataframe(df_exp, use_container_width=True, hide_index=True)
        else:
            st.info("No expenses recorded yet.")

# ============================================================
# 6. SUPPLIER RESTOCKS
# ============================================================
elif page == "Restocks":
    page_header("Supplier restocks", "Record incoming stock deliveries to replenish inventory.")
    products = get_business_products(biz["business_id"])

    if not products:
        st.info("Add products under **📦 Products & stock** before recording restocks.")
    else:
        product_map = {p["product_name"]: p for p in products}
        chosen_name = st.selectbox("Select product restocked", list(product_map.keys()))
        chosen_p = product_map[chosen_name]

        with st.form("restock_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            qty_added = c1.number_input("Quantity received", min_value=1.0, value=10.0, step=1.0)
            buy_cost = c2.number_input(
                "Unit buying price (KSh)",
                min_value=0.0,
                value=float(chosen_p["buying_price"]),
                step=1.0
            )
            notes = st.text_input("Supplier or delivery note", placeholder="e.g. Wholesale delivery")
            submit = st.form_submit_button("Confirm restock", type="primary")
            if submit:
                operations.record_purchase(
                    business_id=biz["business_id"],
                    supplier_id=None,
                    purchase_items_list=[{
                        "product_id": chosen_p["product_id"],
                        "quantity_added": qty_added,
                        "unit_buying_price": buy_cost
                    }],
                    notes=notes.strip(),
                    lang=lang
                )
                st.success(f"Added {qty_added:g} units of {chosen_name} to stock.")
                st.rerun()

# ============================================================
# 7. DAILY RECORDS
# ============================================================
elif page == "Daily records":
    page_header("Daily records", "Review a specific day's sales, expenses, and overall ledger summary.")
    chosen_date = st.date_input("Choose a date", value=date.today())
    ds = chosen_date.isoformat()

    sales = [s for s in get_business_sales(biz["business_id"]) if s["sale_day"] == ds]
    expenses = [e for e in get_business_expenses(biz["business_id"]) if e["expense_day"] == ds]

    sales_sum = sum(s["total"] for s in sales)
    exp_sum = sum(e["amount"] for e in expenses)

    a, b, c = st.columns(3)
    a.metric("Sales on date", money(sales_sum))
    b.metric("Expenses on date", money(exp_sum))
    c.metric("Sales less expenses", money(sales_sum - exp_sum))

    st.caption("This is a daily cashflow summary. Inventory restock costs and credit balances are tracked separately.")

    with st.expander("See sales for this date", expanded=True):
        if sales:
            st.dataframe(
                pd.DataFrame(sales)[["sale_date", "product_name", "quantity", "unit_price", "total", "payment_method"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No sales recorded on this date.")

    with st.expander("See expenses for this date", expanded=True):
        if expenses:
            st.dataframe(
                pd.DataFrame(expenses)[["expense_date", "category", "description", "amount"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No expenses recorded on this date.")

# ============================================================
# 8. REPORTS
# ============================================================
elif page == "Reports":
    page_header("Reports & insights", f"Overall performance for {biz['business_name']}.")
    summary = get_business_summary(biz["business_id"])
    sales = get_business_sales(biz["business_id"])
    expenses = get_business_expenses(biz["business_id"])

    # Safe fallbacks preventing NoneType errors
    total_sales = summary.get("total_revenue", 0.0) if summary else sum(s["total"] for s in sales)
    total_expenses = summary.get("total_expenses", 0.0) if summary else sum(e["amount"] for e in expenses)
    total_restocks = summary.get("total_restock_cost", 0.0) if summary else 0.0
    
    total_sales = total_sales if total_sales is not None else 0.0
    total_expenses = total_expenses if total_expenses is not None else 0.0
    total_restocks = total_restocks if total_restocks is not None else 0.0
    total_profit = sum(s["estimated_profit"] for s in sales) if sales else 0.0

    a, b, c, d = st.columns(4)
    a.metric("Total sales revenue", money(total_sales))
    b.metric("Estimated gross profit", money(total_profit))
    c.metric("Total expenses", money(total_expenses))
    d.metric("Net cash position", money(total_sales - total_expenses - total_restocks))

    if sales:
        st.markdown("### Daily sales trend")
        daily = pd.DataFrame(sales).groupby("sale_day", as_index=False)["total"].sum()
        st.line_chart(daily.set_index("sale_day"))

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### Top selling products")
            top_prods = pd.DataFrame(sales).groupby("product_name", as_index=False)["total"].sum().sort_values("total", ascending=False)
            st.bar_chart(top_prods.set_index("product_name"))
        with col_r:
            st.markdown("### Sales by Payment Method")
            pay_methods = pd.DataFrame(sales).groupby("payment_method", as_index=False)["total"].sum()
            st.bar_chart(pay_methods.set_index("payment_method"))
    else:
        st.info("Once you record sales, your charts and insights will appear here.")

    if expenses:
        st.markdown("### Expenses by category")
        expdf = pd.DataFrame(expenses).groupby("category", as_index=False)["amount"].sum()
        st.bar_chart(expdf.set_index("category"))

st.divider()
st.caption("Biashara • Built for everyday businesses")
conn.close()