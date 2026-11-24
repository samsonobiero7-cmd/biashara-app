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
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom Mobile App Icon & PWA Manifest Links ----------
st.markdown("""
    <link rel="manifest" href="/app/static/manifest.json">
    <link rel="icon" type="image/png" href="/app/static/icon-192.png">
    <link rel="apple-touch-icon" href="/app/static/icon-192.png">
""", unsafe_allow_html=True)

# ---------- Forest-Green & Clean Card Styling (Light/Dark Mode Compatible) ----------
st.markdown("""
<style>
:root { --green:#16764a; }
.block-container { padding-top:1.5rem; padding-bottom:3rem; max-width:1500px; }
div[data-testid="stMetric"] {
  border:1px solid rgba(128, 128, 128, 0.25); padding:16px;
  border-radius:14px;
}
.stButton > button, .stFormSubmitButton > button {
  border-radius:10px; min-height:42px; font-weight:600;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background:#16764a !important; border-color:#16764a !important; color:white !important;
}
/* Ensure button labels remain crisp white in both light and dark mode */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    background-color: #0E763F !important;
    color: #FFFFFF !important;
    border: none !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #0B5D32 !important;
    color: #FFFFFF !important;
}
.stButton > button p,
[data-testid="stFormSubmitButton"] > button p {
    color: #FFFFFF !important;
}
.small-muted { color:#718078 !important; font-size:0.88rem; }
div[data-testid="stDataFrame"] { border-radius:12px; }
</style>
""", unsafe_allow_html=True)

# ---------- Bilingual Translation Helper ----------
UI_STRINGS = {
    "en": {
        "tagline": "Your business, made simpler.",
        "current_biz": "CURRENT BUSINESS",
        "add_first_biz": "Add your first business to get started.",
        "sidebar_footer_1": "Simple tools for everyday business.",
        "sidebar_footer_2": "Biashara • Connected to SQLite",
        "nav_overview": "🏠  Overview",
        "nav_businesses": "🏪  My businesses",
        "nav_products": "📦  Products & stock",
        "nav_sales": "🛒  Record a sale",
        "nav_expenses": "💸  Expenses",
        "nav_restocks": "📦  Supplier restocks",
        "nav_daily": "📅  Daily records",
        "nav_reports": "📊  Reports",
        "warn_no_biz": "Add your first business using **🏪 My businesses** in the sidebar.",
        "overview_title": "Good morning 👋",
        "overview_sub": "Here's what's happening at {biz} today.",
        "todays_sales": "Today's sales",
        "todays_expenses": "Today's expenses",
        "products_count": "Products",
        "low_stock_items": "Low-stock items",
        "recent_sales": "Recent sales",
        "no_sales_yet": "No sales recorded yet. Use **🛒 Record a sale** in the sidebar to log your first transaction.",
        "stock_to_check": "Stock to check",
        "all_caught_up": "You're all caught up. No low-stock alerts.",
        "biz_title": "My businesses",
        "biz_sub": "Manage all the businesses connected to your Biashara database.",
        "your_businesses": "Your businesses",
        "no_biz_yet": "You haven't added a business yet.",
        "add_a_biz": "Add a business",
        "biz_name_lbl": "Business name",
        "biz_cat_lbl": "Business category",
        "add_biz_btn": "＋ Add business",
        "biz_caption": "Each business maintains its own separate inventory, sales, and expense records in SQLite.",
        "prod_title": "Products & stock",
        "prod_sub": "Keep track of what {biz} sells.",
        "tab_prod_list": "📦 Product list",
        "tab_add_prod": "＋ Add product",
        "tab_custom_attr": "🏷️ Custom attributes",
        "no_prods_yet": "No products yet. Add your first product in the **＋ Add product** tab.",
        "prod_name_lbl": "Product name",
        "opening_stock": "Opening stock",
        "low_stock_at": "Low-stock alert at",
        "buying_price": "Buying price (KSh)",
        "selling_price": "Selling price (KSh)",
        "save_prod_btn": "Save product",
        "sales_title": "Record a sale",
        "sales_sub": "Log a sale quickly, select payment method, and keep stock updated.",
        "new_sale_entry": "New sale entry",
        "what_did_you_sell": "What did you sell?",
        "qty_sold": "Quantity sold",
        "unit_price_lbl": "Selling price per unit (KSh)",
        "confirm_sale_btn": "Confirm sale",
        "exp_title": "Expenses",
        "exp_sub": "Keep an eye on the money going out.",
        "add_an_exp": "Add an expense",
        "exp_for_lbl": "What was the expense for?",
        "exp_cat_lbl": "Expense category",
        "amount_lbl": "Amount (KSh)",
        "save_exp_btn": "Save expense",
        "exp_history": "Expense history",
        "total_rec_exp": "Total recorded expenses",
        "restock_title": "Supplier restocks",
        "restock_sub": "Record incoming stock deliveries to replenish inventory.",
        "select_prod_restock": "Select product restocked",
        "qty_received": "Quantity received",
        "delivery_note": "Supplier or delivery note",
        "confirm_restock_btn": "Confirm restock",
        "daily_title": "Daily records",
        "daily_sub": "Review a specific day's sales, expenses, and overall ledger summary.",
        "choose_date": "Choose a date",
        "sales_on_date": "Sales on date",
        "exp_on_date": "Expenses on date",
        "sales_less_exp": "Sales less expenses",
        "reports_title": "Reports & insights",
        "reports_sub": "Overall performance for {biz}.",
        "total_sales_rev": "Total sales revenue",
        "est_gross_profit": "Estimated gross profit",
        "total_expenses": "Total expenses",
        "net_cash_pos": "Net cash position",
        "footer_caption": "Biashara • Built for everyday businesses",
    },
    "sw": {
        "tagline": "Biashara yako, imerahisishwa.",
        "current_biz": "BIASHARA YA SASA",
        "add_first_biz": "Ongeza biashara yako ya kwanza ili kuanza.",
        "sidebar_footer_1": "Zana rahisi kwa biashara ya kila siku.",
        "sidebar_footer_2": "Biashara • Imeunganishwa na SQLite",
        "nav_overview": "🏠  Muhtasari",
        "nav_businesses": "🏪  Biashara zangu",
        "nav_products": "📦  Bidhaa na stoo",
        "nav_sales": "🛒  Rekodi mauzo",
        "nav_expenses": "💸  Matumizi",
        "nav_restocks": "📦  Kuongeza stoo",
        "nav_daily": "📅  Rekodi za kila siku",
        "nav_reports": "📊  Ripoti",
        "warn_no_biz": "Ongeza biashara yako ya kwanza kupitia **🏪 Biashara zangu** pembeni.",
        "overview_title": "Habari za asubuhi 👋",
        "overview_sub": "Haya ndiyo yanayoendelea katika {biz} leo.",
        "todays_sales": "Mauzo ya leo",
        "todays_expenses": "Matumizi ya leo",
        "products_count": "Bidhaa",
        "low_stock_items": "Bidhaa zinazokaribia kuisha",
        "recent_sales": "Mauzo ya hivi karibuni",
        "no_sales_yet": "Hakuna mauzo yaliyorekodiwa bado. Tumia **🛒 Rekodi mauzo** kurekodi muamala wako wa kwanza.",
        "stock_to_check": "Stoo ya kukagua",
        "all_caught_up": "Kila kitu kiko sawa. Hakuna tahadhari za upungufu wa stoo.",
        "biz_title": "Biashara zangu",
        "biz_sub": "Simamia biashara zote zilizounganishwa kwenye mfumo wako wa Biashara.",
        "your_businesses": "Biashara zako",
        "no_biz_yet": "Bado hujaongeza biashara yoyote.",
        "add_a_biz": "Ongeza biashara",
        "biz_name_lbl": "Jina la biashara",
        "biz_cat_lbl": "Aina ya biashara",
        "add_biz_btn": "＋ Ongeza biashara",
        "biz_caption": "Kila biashara ina stoo, mauzo, na rekodi zake za matumizi kipekee katika SQLite.",
        "prod_title": "Bidhaa na stoo",
        "prod_sub": "Fuatilia bidhaa zinazouzwa na {biz}.",
        "tab_prod_list": "📦 Orodha ya bidhaa",
        "tab_add_prod": "＋ Ongeza bidhaa",
        "tab_custom_attr": "🏷️ Sifa maalum",
        "no_prods_yet": "Hakuna bidhaa bado. Ongeza bidhaa yako ya kwanza katika **＋ Ongeza bidhaa**.",
        "prod_name_lbl": "Jina la bidhaa",
        "opening_stock": "Stoo ya kuanzia",
        "low_stock_at": "Tahadhari stoo ikifikia",
        "buying_price": "Bei ya kununulia (KSh)",
        "selling_price": "Bei ya kuuzia (KSh)",
        "save_prod_btn": "Hifadhi bidhaa",
        "sales_title": "Rekodi mauzo",
        "sales_sub": "Rekodi mauzo haraka, chagua njia ya malipo, na usasishe stoo.",
        "new_sale_entry": "Ingiza mauzo mapya",
        "what_did_you_sell": "Umeuza nini?",
        "qty_sold": "Idadi iliyouzwa",
        "unit_price_lbl": "Bei ya kuuzia kwa moja (KSh)",
        "confirm_sale_btn": "Thibitisha mauzo",
        "exp_title": "Matumizi",
        "exp_sub": "Fuatilia pesa zinazotoka nje ya biashara.",
        "add_an_exp": "Ongeza matumizi",
        "exp_for_lbl": "Matumizi yalikuwa ya nini?",
        "exp_cat_lbl": "Kundi la matumizi",
        "amount_lbl": "Kiasi (KSh)",
        "save_exp_btn": "Hifadhi matumizi",
        "exp_history": "Historia ya matumizi",
        "total_rec_exp": "Jumla ya matumizi yaliyorekodiwa",
        "restock_title": "Kuongeza stoo",
        "restock_sub": "Rekodi mizigo mipya iliyoingia kuongeza stoo.",
        "select_prod_restock": "Chagua bidhaa iliyoongezwa",
        "qty_received": "Idadi iliyopokelewa",
        "delivery_note": "Maelezo ya msambazaji au mzigo",
        "confirm_restock_btn": "Thibitisha mzigo",
        "daily_title": "Rekodi za kila siku",
        "daily_sub": "Kagua mauzo, matumizi, na muhtasari wa siku mahususi.",
        "choose_date": "Chagua tarehe",
        "sales_on_date": "Mauzo ya tarehe hii",
        "exp_on_date": "Matumizi ya tarehe hii",
        "sales_less_exp": "Mauzo baada ya matumizi",
        "reports_title": "Ripoti na takwimu",
        "reports_sub": "Utendaji wa jumla wa {biz}.",
        "total_sales_rev": "Jumla ya mapato ya mauzo",
        "est_gross_profit": "Makadirio ya faida ghafi",
        "total_expenses": "Jumla ya matumizi",
        "net_cash_pos": "Salio halisi la fedha",
        "footer_caption": "Biashara • Imejengwa kwa ajili ya biashara za kila siku",
    }
}


def t(key, lang="en", **kwargs):
    text = UI_STRINGS.get(lang, UI_STRINGS["en"]).get(key)
    if text is None:
        text = get_text(key, lang=lang)
    return text.format(**kwargs) if kwargs else text


# ---------- Initialize SQLite Database ----------
setup_biashara.create_biashara_database()
if "custom_attributes" not in st.session_state:
    st.session_state.custom_attributes = {}


def get_conn():
    return operations.get_db_connection()


def is_duplicate_reference(payment_ref: str) -> bool:
    if not payment_ref:
        return False
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM sales WHERE UPPER(TRIM(payment_reference)) = ? LIMIT 1",
            (payment_ref.strip().upper(),),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def money(value):
    return f"KSh {float(value or 0):,.2f}"


# ---------- Database Helper Queries ----------
def get_all_businesses():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT business_id, business_name, business_type FROM businesses ORDER BY business_id ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_business_products(bid):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT product_id, product_name, buying_price, selling_price, stock_quantity, reorder_level
            FROM products WHERE business_id = ? ORDER BY product_name ASC
        """, (bid,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_business_sales(bid, day_str=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if day_str:
            cur.execute("""
                SELECT sale_id, sale_day, sale_date, product_name, quantity,
                       unit_price, buying_price, total, estimated_profit,
                       payment_method, payment_reference
                FROM daily_sales_view
                WHERE business_id = ? AND sale_day = ?
                ORDER BY sale_date DESC
            """, (bid, day_str))
        else:
            cur.execute("""
                SELECT sale_id, sale_day, sale_date, product_name, quantity,
                       unit_price, buying_price, total, estimated_profit,
                       payment_method, payment_reference
                FROM daily_sales_view
                WHERE business_id = ?
                ORDER BY sale_date DESC
            """, (bid,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_business_expenses(bid):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT expense_id, DATE(expense_date) AS expense_day, expense_date,
                   category, amount, description
            FROM expenses
            WHERE business_id = ?
            ORDER BY expense_date DESC
        """, (bid,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_business_summary(bid):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM daily_business_summary WHERE business_id = ?", (bid,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------- Sidebar ----------
businesses = get_all_businesses()
with st.sidebar:
    col_logo, col_title = st.columns([1, 4], vertical_alignment="center")
    with col_logo:
        st.image("logo.png", width=36)
    with col_title:
        st.markdown("## Biashara")

    lang_choice = st.selectbox(
        "Language / Lugha",
        ["English", "Kiswahili"],
        index=0 if st.session_state.get("lang", "en") == "en" else 1,
        label_visibility="collapsed"
    )
    lang = "en" if lang_choice == "English" else "sw"
    st.session_state.lang = lang

    st.caption(t("tagline", lang))
    st.divider()
    if businesses:
        biz_map = {b["business_name"]: b for b in businesses}
        names = list(biz_map.keys())
        default_idx = names.index(st.session_state["active_business"]) if st.session_state.get("active_business") in names else 0
        chosen_name = st.selectbox(t("current_biz", lang), names, index=default_idx)
        st.session_state.active_business = chosen_name
        biz = biz_map[chosen_name]
    else:
        biz = None
        st.info(t("add_first_biz", lang))
    st.divider()
    pages = {
        t("nav_overview", lang): "Overview",
        t("nav_businesses", lang): "Businesses",
        t("nav_products", lang): "Products",
        t("nav_sales", lang): "Sales",
        t("nav_expenses", lang): "Expenses",
        t("nav_restocks", lang): "Restocks",
        t("nav_daily", lang): "Daily records",
        t("nav_reports", lang): "Reports",
    }
    page_label = st.radio("MENU", list(pages.keys()), label_visibility="collapsed")
    page = pages[page_label]
    st.divider()
    st.caption(t("sidebar_footer_1", lang))
    st.caption(t("sidebar_footer_2", lang))

if not biz and page != "Businesses":
    st.warning(t("warn_no_biz", lang))
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
    page_header(t("overview_title", lang), t("overview_sub", lang, biz=biz["business_name"]))
    today_str = date.today().isoformat()
    all_sales = get_business_sales(biz["business_id"])
    all_expenses = get_business_expenses(biz["business_id"])
    products = get_business_products(biz["business_id"])
    todays_sales = [s for s in all_sales if s["sale_day"] == today_str]
    todays_expenses = [e for e in all_expenses if e["expense_day"] == today_str]
    low_stock = [p for p in products if p["stock_quantity"] <= p["reorder_level"]]
    a, b, c, d = st.columns(4)
    a.metric(t("todays_sales", lang), money(sum(s["total"] for s in todays_sales)))
    b.metric(t("todays_expenses", lang), money(sum(e["amount"] for e in todays_expenses)))
    c.metric(t("products_count", lang), len(products))
    d.metric(t("low_stock_items", lang), len(low_stock))
    st.write("")
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown(f"### {t('recent_sales', lang)}")
        if all_sales:
            df_recent = pd.DataFrame(all_sales[:8])[[
                "sale_day", "product_name", "quantity", "unit_price", "total", "payment_method"
            ]].rename(
                columns={
                    "sale_day": "Date" if lang == "en" else "Tarehe",
                    "product_name": "Product" if lang == "en" else "Bidhaa",
                    "quantity": "Qty" if lang == "en" else "Idadi",
                    "unit_price": "Unit Price" if lang == "en" else "Bei",
                    "total": "Total (KSh)" if lang == "en" else "Jumla (KSh)",
                    "payment_method": "Paid Via" if lang == "en" else "Malipo"
                }
            )
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info(t("no_sales_yet", lang))
    with right:
        st.markdown(f"### {t('stock_to_check', lang)}")
        if low_stock:
            for p in low_stock[:6]:
                if lang == "en":
                    st.warning(f"**{p['product_name']}** — {p['stock_quantity']:g} units left (Alert below {p['reorder_level']:g})")
                else:
                    st.warning(f"**{p['product_name']}** — Zimebaki {p['stock_quantity']:g} (Tahadhari chini ya {p['reorder_level']:g})")
        else:
            st.success(t("all_caught_up", lang))

# ============================================================
# 2. MY BUSINESSES
# ============================================================
elif page == "Businesses":
    page_header(t("biz_title", lang), t("biz_sub", lang))
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(f"### {t('your_businesses', lang)}")
        if businesses:
            df_biz = pd.DataFrame(businesses)[["business_id", "business_name", "business_type"]].rename(
                columns={
                    "business_id": "ID",
                    "business_name": "Business Name" if lang == "en" else "Jina la Biashara",
                    "business_type": "Sector" if lang == "en" else "Sekta"
                }
            )
            st.dataframe(df_biz, use_container_width=True, hide_index=True)
        else:
            st.info(t("no_biz_yet", lang))
    with right:
        st.markdown(f"### {t('add_a_biz', lang)}")
        with st.form("add_business", clear_on_submit=True):
            name = st.text_input(t("biz_name_lbl", lang), placeholder="e.g. Mama Njeri's Shop")
            kind = st.selectbox(
                t("biz_cat_lbl", lang),
                ["Grocery", "Hardware", "Electrical", "Cereal", "Retail shop", "Other"]
            )
            submitted = st.form_submit_button(t("add_biz_btn", lang), type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("Please enter a business name." if lang == "en" else "Tafadhali weka jina la biashara.")
                else:
                    new_id = operations.register_business(business_name=name.strip(), business_type=kind)
                    st.session_state.active_business = name.strip()
                    st.success(f"{name.strip()} has been added (ID: {new_id})." if lang == "en" else f"{name.strip()} imeongezwa (ID: {new_id}).")
                    st.rerun()
    st.caption(t("biz_caption", lang))

# ============================================================
# 3. PRODUCTS & STOCK
# ============================================================
elif page == "Products":
    page_header(t("prod_title", lang), t("prod_sub", lang, biz=biz["business_name"]))
    products = get_business_products(biz["business_id"])
    tab1, tab2, tab3 = st.tabs([t("tab_prod_list", lang), t("tab_add_prod", lang), t("tab_custom_attr", lang)])
    with tab1:
        if products:
            df = pd.DataFrame(products).rename(columns={
                "product_id": "ID",
                "product_name": "Product" if lang == "en" else "Bidhaa",
                "buying_price": "Buying price (KSh)" if lang ==