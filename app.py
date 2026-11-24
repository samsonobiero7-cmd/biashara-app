import streamlit as st
import pandas as pd
from datetime import date
import os
from pathlib import Path
import psycopg
import setup_biashara
import operations
from translations import get_text
from streamlit.errors import StreamlitSecretNotFoundError

# ------------------------------------------------------------
# BIASHARA — PostgreSQL-Backed Business Manager & POS
# ------------------------------------------------------------
st.set_page_config(
    page_title="Biashara | Business Manager",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom Mobile App Icon & PWA Manifest Links ----------
st.markdown("""
    <link rel="manifest" href="/app/static/manifest.json?v=2">
    <link rel="icon" type="image/png" href="/app/static/logo.png?v=2">
    <link rel="apple-touch-icon" sizes="180x180" href="/app/static/apple-touch-icon.png?v=2">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Biashara">
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
[data-testid="stToolbarActions"] { display:none !important; }
[data-testid="stFooter"], [data-testid="stStatusWidget"] { display:none !important; }
footer { display:none !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Bilingual Translation Helper ----------
UI_STRINGS = {
    "en": {
        "tagline": "Your business, made simpler.",
        "current_biz": "CURRENT BUSINESS",
        "add_first_biz": "Add your first business to get started.",
        "sidebar_footer_1": "Simple tools for everyday business.",
        "sidebar_footer_2": "Biashara • Connected to Supabase",
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
        "biz_caption": "Each business maintains its own separate inventory, sales, and expense records in Supabase.",
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
        "sales_col_date": "Date",
        "sales_col_product": "Product",
        "sales_col_quantity": "Qty",
        "sales_col_unit_price": "Unit Price",
        "sales_col_total": "Total (KSh)",
        "sales_col_payment": "Payment",
        "sales_col_payment_reference": "Reference / Code",
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
        "sidebar_footer_2": "Biashara • Imeunganishwa na Supabase",
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
        "biz_caption": "Kila biashara ina stoo, mauzo, na rekodi zake za matumizi kipekee katika Supabase.",
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
        "sales_col_date": "Tarehe",
        "sales_col_product": "Bidhaa",
        "sales_col_quantity": "Idadi",
        "sales_col_unit_price": "Bei",
        "sales_col_total": "Jumla (KSh)",
        "sales_col_payment": "Malipo",
        "sales_col_payment_reference": "Kumbukumbu",
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


def offline_checkout_enabled():
    enabled = os.getenv("OFFLINE_CHECKOUT_ENABLED")
    if enabled is None:
        try:
            enabled = st.secrets.get("OFFLINE_CHECKOUT_ENABLED", "false")
        except (KeyError, StreamlitSecretNotFoundError):
            enabled = "false"
    return str(enabled).strip().lower() in {"1", "true", "yes"}


OFFLINE_SYNC_COMPONENT = st.components.v2.component(
    "biashara_offline_sync",
    html="<div aria-hidden='true'></div>",
    js=(Path(__file__).parent / "static" / "offline" / "bridge.js").read_text(
        encoding="utf-8"
    ),
)

def require_signed_in_owner():
    required_settings = {
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    }
    try:
        auth_settings = st.secrets["auth"]
    except (KeyError, StreamlitSecretNotFoundError):
        auth_settings = None

    if not auth_settings or any(
        not str(auth_settings.get(key, "")).strip() for key in required_settings
    ):
        st.error(
            "Google sign-in is not configured. Add the [auth] settings from "
            ".streamlit/secrets.toml.example to Streamlit Cloud Secrets."
        )
        st.stop()

    if not st.user.is_logged_in:
        st.title("Biashara Manager")
        st.write("Sign in with Google to access your business records.")
        st.button("Continue with Google", on_click=st.login, type="primary")
        st.stop()

    owner_email = str(st.user.get("email", "")).strip().lower()
    if not owner_email or not st.user.get("email_verified", False):
        st.error("Sign in with a Google account that has a verified email address.")
        st.stop()
    return owner_email


owner_email = require_signed_in_owner()


@st.cache_resource
def initialize_biashara_database():
    setup_biashara.create_biashara_database()


try:
    initialize_biashara_database()
except RuntimeError as error:
    st.error(str(error))
    st.stop()

if "custom_attributes" not in st.session_state:
    st.session_state.custom_attributes = {}


def get_conn():
    return operations.get_db_connection()


def is_duplicate_reference(payment_ref: str, owner_email: str) -> bool:
    if not payment_ref:
        return False
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM sales s
            JOIN businesses b ON b.business_id = s.business_id
            WHERE b.owner_email = %s
              AND UPPER(TRIM(s.payment_reference)) = %s
            LIMIT 1
            """,
            (owner_email, payment_ref.strip().upper()),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def money(value):
    return f"KSh {float(value or 0):,.2f}"


# ---------- Database Helper Queries ----------
def get_all_businesses(owner_email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT business_id, business_name, business_type
            FROM businesses
            WHERE owner_email = %s
            ORDER BY business_id ASC
            """,
            (owner_email,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_business_products(bid, owner_email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_id, p.product_name, p.buying_price, p.selling_price,
                   p.stock_quantity, p.reorder_level
            FROM products p
            JOIN businesses b ON b.business_id = p.business_id
            WHERE p.business_id = %s AND b.owner_email = %s
            ORDER BY p.product_name ASC
        """, (bid, owner_email))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def sync_offline_sales(business, products, lang):
    bid = int(business["business_id"])
    ack_ids = set(st.session_state.get("offline_ack_ids", []))
    component_key = f"offline-sync-{bid}"
    component_state = st.session_state.get(component_key, {})
    pending_signature = component_state.get("pending_signature", "[]")
    result = OFFLINE_SYNC_COMPONENT(
        data={
            "owner_email": owner_email,
            "business_id": bid,
            "business_name": business["business_name"],
            "products": products,
            "ack_ids": sorted(ack_ids),
            "pending_signature": pending_signature,
        },
        default={
            "catalog_ready": component_state.get("catalog_ready", False),
            "pending_sales": component_state.get("pending_sales", []),
            "pending_signature": pending_signature,
            "bridge_error": component_state.get("bridge_error"),
        },
        on_catalog_ready_change=lambda: None,
        on_pending_sales_change=lambda: None,
        on_pending_signature_change=lambda: None,
        on_bridge_error_change=lambda: None,
        key=component_key,
    )

    notice = st.session_state.pop("offline_sync_notice", None)
    if notice:
        if notice["stock_conflict"]:
            st.warning(
                f"Synced {notice['count']} offline sale(s). Some stock is now below zero; "
                "please check the stock levels."
                if lang == "en"
                else f"Mauzo {notice['count']} ya nje ya mtandao yamesawazishwa. "
                "Baadhi ya stoo iko chini ya sifuri; tafadhali kagua viwango vya stoo."
            )
        else:
            st.success(
                f"Synced {notice['count']} offline sale(s)."
                if lang == "en"
                else f"Mauzo {notice['count']} ya nje ya mtandao yamesawazishwa."
            )

    bridge_error = getattr(result, "bridge_error", None)
    if bridge_error:
        st.error(f"Offline storage error: {bridge_error}")
        return
    if getattr(result, "catalog_ready", False):
        st.caption(
            "This device's product list is saved for offline checkout."
            if lang == "en"
            else "Orodha ya bidhaa ya kifaa hiki imehifadhiwa kwa mauzo ya nje ya mtandao."
        )

    pending_sales = getattr(result, "pending_sales", None)
    if pending_sales is None:
        return
    if not isinstance(pending_sales, list):
        st.error("Offline sales could not be read. They remain saved on this device.")
        return

    if not pending_sales:
        st.session_state["offline_ack_ids"] = []
        return

    accepted_ids = set()
    errors = []
    for sale in pending_sales:
        if not isinstance(sale, dict):
            errors.append("An offline sale has an invalid format.")
            continue
        client_sale_id = sale.get("client_sale_id")
        if not isinstance(client_sale_id, str):
            errors.append("An offline sale has an invalid ID.")
            continue
        if client_sale_id in ack_ids:
            continue
        if sale.get("owner_email") != owner_email:
            errors.append("An offline sale belongs to a different signed-in account.")
            continue
        try:
            sale_business_id = int(sale.get("business_id", -1))
        except (TypeError, ValueError):
            errors.append("An offline sale has an invalid business ID.")
            continue
        if sale_business_id != bid:
            errors.append("An offline sale belongs to a different business.")
            continue

        raw_items = sale.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            errors.append("An offline sale has no products and was not synced.")
            continue

        sale_items = []
        try:
            for item in raw_items:
                product_id = int(item["product_id"])
                quantity = float(item["quantity"])
                unit_price = float(item["unit_price"])
                if product_id <= 0 or quantity <= 0 or unit_price < 0:
                    raise ValueError
                sale_items.append(
                    {
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                    }
                )
        except (KeyError, TypeError, ValueError):
            errors.append("An offline sale has invalid product details.")
            continue

        payment_method = sale.get("payment_method", "Cash")
        if payment_method not in ["Cash", "M-Pesa", "Visa / Card", "Bank Transfer"]:
            errors.append("An offline sale has an unsupported payment method.")
            continue
        payment_reference = sale.get("payment_reference")
        if payment_reference:
            payment_reference = str(payment_reference).strip().upper()
        else:
            payment_reference = None
        if payment_method != "Cash" and not payment_reference:
            errors.append(
                f"Add a payment reference to the offline {payment_method} sale."
            )
            continue

        try:
            sale_id = operations.record_sale_secure(
                business_id=bid,
                sale_items_list=sale_items,
                owner_email=owner_email,
                payment_method=payment_method,
                payment_reference=payment_reference,
                lang=lang,
                offline_sale_id=client_sale_id,
                offline_sale_date=sale.get("created_at"),
            )
        except (PermissionError, ValueError) as error:
            errors.append(str(error))
            continue
        except psycopg.errors.UniqueViolation:
            errors.append(
                "An offline sale has a duplicate payment reference and remains saved "
                "on this device."
            )
            continue

        if sale_id is None:
            errors.append(
                "An offline sale refers to a product that no longer exists in this business."
            )
            continue
        accepted_ids.add(client_sale_id)

    if accepted_ids:
        st.session_state["offline_ack_ids"] = sorted(ack_ids | accepted_ids)
        refreshed_products = get_business_products(bid, owner_email)
        has_negative_stock = any(
            float(product["stock_quantity"]) < 0 for product in refreshed_products
        )
        st.session_state["offline_sync_notice"] = {
            "count": len(accepted_ids),
            "stock_conflict": has_negative_stock,
        }
        st.rerun()

    if errors:
        st.error("Offline sales need attention: " + " ".join(errors))


def get_business_sales(bid, owner_email, day_str=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if day_str:
            cur.execute("""
                SELECT sale_id, sale_day, sale_date, product_name, quantity,
                       unit_price, buying_price, total, estimated_profit,
                       payment_method, payment_reference
                FROM daily_sales_view v
                JOIN businesses b ON b.business_id = v.business_id
                WHERE v.business_id = %s AND b.owner_email = %s AND v.sale_day = %s
                ORDER BY sale_date DESC
            """, (bid, owner_email, date.fromisoformat(day_str)))
        else:
            cur.execute("""
                SELECT sale_id, sale_day, sale_date, product_name, quantity,
                       unit_price, buying_price, total, estimated_profit,
                       payment_method, payment_reference
                FROM daily_sales_view v
                JOIN businesses b ON b.business_id = v.business_id
                WHERE v.business_id = %s AND b.owner_email = %s
                ORDER BY sale_date DESC
            """, (bid, owner_email))
        rows = [dict(row) for row in cur.fetchall()]
        for row in rows:
            row["sale_day"] = row["sale_day"].isoformat()
        return rows
    finally:
        conn.close()


def get_business_expenses(bid, owner_email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.expense_id, e.expense_date::date AS expense_day,
                   e.expense_date, e.category, e.amount, e.description
            FROM expenses e
            JOIN businesses b ON b.business_id = e.business_id
            WHERE e.business_id = %s AND b.owner_email = %s
            ORDER BY e.expense_date DESC
        """, (bid, owner_email))
        rows = [dict(row) for row in cur.fetchall()]
        for row in rows:
            row["expense_day"] = row["expense_day"].isoformat()
        return rows
    finally:
        conn.close()


def get_business_summary(bid, owner_email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM daily_business_summary
            WHERE business_id = %s AND owner_email = %s
            """,
            (bid, owner_email),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------- Sidebar ----------
businesses = get_all_businesses(owner_email)
with st.sidebar:
    logo_col, title_col = st.columns([1, 4])
    with logo_col:
        st.image("logo.png", width=40)
    with title_col:
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
    st.download_button(
        "Download my data backup",
        data=lambda: operations.get_owner_backup(owner_email),
        file_name=f"biashara-backup-{date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.button("Sign out", on_click=st.logout, use_container_width=True)

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
    all_sales = get_business_sales(biz["business_id"], owner_email)
    all_expenses = get_business_expenses(biz["business_id"], owner_email)
    products = get_business_products(biz["business_id"], owner_email)
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
                    new_id = operations.register_business(
                        business_name=name.strip(),
                        business_type=kind,
                        owner_email=owner_email,
                    )
                    st.session_state.active_business = name.strip()
                    st.success(f"{name.strip()} has been added (ID: {new_id})." if lang == "en" else f"{name.strip()} imeongezwa (ID: {new_id}).")
                    st.rerun()
    st.caption(t("biz_caption", lang))

# ============================================================
# 3. PRODUCTS & STOCK
# ============================================================
elif page == "Products":
    page_header(t("prod_title", lang), t("prod_sub", lang, biz=biz["business_name"]))
    products = get_business_products(biz["business_id"], owner_email)
    tab1, tab2, tab3 = st.tabs([t("tab_prod_list", lang), t("tab_add_prod", lang), t("tab_custom_attr", lang)])
    with tab1:
        if products:
            df = pd.DataFrame(products).rename(columns={
                "product_id": "ID",
                "product_name": "Product" if lang == "en" else "Bidhaa",
                "buying_price": "Buying price (KSh)" if lang == "en" else "Bei ya kununua (KSh)",
                "selling_price": "Selling price (KSh)" if lang == "en" else "Bei ya kuuza (KSh)",
                "stock_quantity": "In stock" if lang == "en" else "Stoo",
                "reorder_level": "Alert below" if lang == "en" else "Tahadhari chini ya"
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(t("no_prods_yet", lang))
    with tab2:
        with st.form("add_product", clear_on_submit=True):
            name = st.text_input(t("prod_name_lbl", lang), placeholder="e.g. Sugar 2kg")
            col1, col2 = st.columns(2)
            qty = col1.number_input(t("opening_stock", lang), min_value=0.0, step=1.0, value=10.0)
            reorder = col2.number_input(t("low_stock_at", lang), min_value=0.0, step=1.0, value=5.0)
            col3, col4 = st.columns(2)
            buy = col3.number_input(t("buying_price", lang), min_value=0.0, step=1.0)
            sell = col4.number_input(t("selling_price", lang), min_value=0.0, step=1.0)
            extra_fields = st.session_state.custom_attributes.get(str(biz["business_id"]), [])
            extras = {}
            if extra_fields:
                st.markdown("**Business-specific details**" if lang == "en" else "**Maelezo maalum ya biashara**")
                cols = st.columns(2)
                for i, attr in enumerate(extra_fields):
                    val = cols[i % 2].text_input(attr)
                    if val.strip():
                        extras[attr] = val.strip()
            save = st.form_submit_button(t("save_prod_btn", lang), type="primary", use_container_width=True)
            if save:
                if not name.strip():
                    st.error("Please enter a product name." if lang == "en" else "Tafadhali weka jina la bidhaa.")
                else:
                    if sell < buy:
                        st.warning("Note: Selling price is lower than buying price." if lang == "en" else "Angalizo: Bei ya kuuza ni ndogo kuliko bei ya kununua.")
                    operations.add_product_with_custom_fields(
                        business_id=biz["business_id"],
                        product_name=name.strip(),
                        buying_price=buy,
                        selling_price=sell,
                        stock_quantity=qty,
                        owner_email=owner_email,
                        reorder_level=reorder,
                        custom_fields=extras if extras else None
                    )
                    st.success(f"'{name.strip()}' saved to database." if lang == "en" else f"'{name.strip()}' imehifadhiwa.")
                    st.rerun()
    with tab3:
        st.markdown("### Give this business its own product fields" if lang == "en" else "### Weka sifa maalum za bidhaa")
        st.caption("For example: brand, size, wattage, grain variety, colour or model." if lang == "en" else "Kwa mfano: kampuni, ukubwa, rangi au aina.")
        current = st.session_state.custom_attributes.get(str(biz["business_id"]), [])
        if current:
            st.write(("Current attributes: **" if lang == "en" else "Sifa za sasa: **") + ", ".join(current) + "**")
        else:
            st.info("No custom attributes added yet for this shop." if lang == "en" else "Hakuna sifa maalum zilizoongezwa bado.")
        with st.form("add_attribute", clear_on_submit=True):
            attr = st.text_input("New attribute" if lang == "en" else "Sifa mpya", placeholder="e.g. Brand")
            add = st.form_submit_button("＋ Add attribute" if lang == "en" else "＋ Ongeza sifa", type="primary")
            if add:
                if not attr.strip():
                    st.error("Enter an attribute name." if lang == "en" else "Weka jina la sifa.")
                elif attr.strip().lower() in [x.lower() for x in current]:
                    st.warning("That attribute already exists." if lang == "en" else "Sifa hiyo tayari ipo.")
                else:
                    st.session_state.custom_attributes[str(biz["business_id"])] = current + [attr.strip()]
                    st.success(f"'{attr.strip()}' will now appear when adding products." if lang == "en" else f"'{attr.strip()}' itaonekana sasa ukiongeza bidhaa.")
                    st.rerun()

# ============================================================
# 4. RECORD A SALE
# ============================================================
elif page == "Sales":
    page_header(t("sales_title", lang), t("sales_sub", lang))
    products = get_business_products(biz["business_id"], owner_email)
    if offline_checkout_enabled():
        st.caption(
            "Offline sales save on this device. Open this page while online to keep its "
            "product list up to date. Open offline checkout once while online to prepare "
            "the page for a connection drop."
            if lang == "en"
            else "Mauzo ya nje ya mtandao huhifadhiwa kwenye kifaa hiki. Fungua ukurasa huu "
            "ukiwa mtandaoni kusasisha bidhaa. Fungua mauzo ya nje ya mtandao mara moja "
            "ukiwa mtandaoni ili kuandaa ukurasa intaneti ikikatika."
        )
        st.link_button(
            "Open offline checkout" if lang == "en" else "Fungua mauzo ya nje ya mtandao",
            "./app/static/offline/index.html",
            width="stretch",
        )
        sync_offline_sales(biz, products, lang)
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown(f"### {t('new_sale_entry', lang)}")
        if not products:
            st.info("Add products under **📦 Products & stock** before recording sales." if lang == "en" else "Ongeza bidhaa chini ya **📦 Bidhaa na stoo** kwanza.")
        else:
            product_map = {p["product_name"]: p for p in products}
            chosen_name = st.selectbox(t("what_did_you_sell", lang), list(product_map.keys()))
            chosen_product = product_map[chosen_name]
            if lang == "en":
                st.caption(
                    f"Available: **{chosen_product['stock_quantity']:g} units** • "
                    f"Standard price: **{money(chosen_product['selling_price'])}** each"
                )
            else:
                st.caption(
                    f"Zilizopo: **{chosen_product['stock_quantity']:g}** • "
                    f"Bei ya kawaida: **{money(chosen_product['selling_price'])}** kila moja"
                )
            with st.form("record_sale_form", clear_on_submit=True):
                qty = st.number_input(t("qty_sold", lang), min_value=0.1, value=1.0, step=1.0)
                unit_price = st.number_input(
                    t("unit_price_lbl", lang),
                    min_value=0.0,
                    value=float(chosen_product["selling_price"]),
                    step=1.0
                )
                payment_options = ["Cash", "M-Pesa", "Visa / Card", "Bank Transfer"]
                payment_method = st.selectbox(get_text("payment_method", lang=lang), payment_options)
                payment_reference = st.text_input(
                    get_text("payment_ref", lang=lang),
                    placeholder="e.g., QGH87XYZ12 (Required for M-Pesa/Card)"
                )
                total = qty * unit_price
                if lang == "en":
                    st.info(f"Sale total: **{money(total)}** | Paid via: **{payment_method}**")
                else:
                    st.info(f"Jumla ya mauzo: **{money(total)}** | Malipo: **{payment_method}**")
                clean_ref = payment_reference.strip().upper() if payment_reference else ""
                submit = st.form_submit_button(t("confirm_sale_btn", lang), type="primary", use_container_width=True)
                if submit:
                    if qty > chosen_product["stock_quantity"]:
                        st.error(f"Insufficient stock. Only {chosen_product['stock_quantity']:g} units available." if lang == "en" else f"Stoo haitoshi. Zimebaki {chosen_product['stock_quantity']:g} pekee.")
                    elif payment_method in ["M-Pesa", "Visa / Card", "Bank Transfer"] and not clean_ref:
                        st.error(f"Please provide a transaction reference code for {payment_method}." if lang == "en" else f"Tafadhali weka nambari ya muamala kwa {payment_method}.")
                    elif clean_ref and is_duplicate_reference(clean_ref, owner_email):
                        st.warning(f"Duplicate payment reference '{clean_ref}' already exists." if lang == "en" else f"Nambari ya muamala '{clean_ref}' tayari imetumika.")
                    else:
                        sale_items = [{
                            "product_id": chosen_product["product_id"],
                            "quantity": qty,
                            "unit_price": unit_price
                        }]
                        sale_id = operations.record_sale_secure(
                            business_id=biz["business_id"],
                            sale_items_list=sale_items,
                            owner_email=owner_email,
                            payment_method=payment_method,
                            payment_reference=clean_ref or None,
                            lang=lang
                        )
                        if sale_id:
                            st.success(f"Sale #{sale_id} recorded successfully! Total: {money(total)} ({payment_method})" if lang == "en" else f"Mauzo #{sale_id} yamerekodiwa! Jumla: {money(total)} ({payment_method})")
                            st.rerun()
                        else:
                            st.error("Could not record sale. Please verify stock levels." if lang == "en" else "Imeshindikana kurekodi mauzo. Hakikisha stoo ipo.")
    with right:
        st.markdown(f"### {t('recent_sales', lang)}")
        sales = get_business_sales(biz["business_id"], owner_email)
        if sales:
            df_sales = pd.DataFrame(sales)[[
                "sale_day", "product_name", "quantity", "unit_price", "total", "payment_method", "payment_reference"
            ]].rename(
                columns={
                    "sale_day": "Date" if lang == "en" else "Tarehe",
                    "product_name": "Product" if lang == "en" else "Bidhaa",
                    "quantity": "Qty" if lang == "en" else "Idadi",
                    "unit_price": "Unit Price" if lang == "en" else "Bei",
                    "total": "Total (KSh)" if lang == "en" else "Jumla (KSh)",
                    "payment_method": "Payment" if lang == "en" else "Malipo",
                    "payment_reference": "Reference / Code" if lang == "en" else "Kumbukumbu"
                }
            )
            st.dataframe(df_sales, use_container_width=True, hide_index=True)
        else:
            st.info("Your recorded sales will appear here." if lang == "en" else "Mauzo yako yaliyorekodiwa yataonekana hapa.")

# ============================================================
# 5. EXPENSES
# ============================================================
elif page == "Expenses":
    page_header(t("exp_title", lang), t("exp_sub", lang))
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown(f"### {t('add_an_exp', lang)}")
        with st.form("add_expense", clear_on_submit=True):
            description = st.text_input(t("exp_for_lbl", lang), placeholder="e.g. Delivery boda boda")
            category = st.selectbox(
                t("exp_cat_lbl", lang),
                ["Transport", "Rent", "Wages", "Utilities", "Packaging", "Other"]
            )
            amount = st.number_input(t("amount_lbl", lang), min_value=0.0, step=50.0)
            submit = st.form_submit_button(t("save_exp_btn", lang), type="primary", use_container_width=True)
            if submit:
                if not description.strip() or amount <= 0:
                    st.error("Enter a description and an amount greater than zero." if lang == "en" else "Weka maelezo na kiasi zaidi ya sifuri.")
                else:
                    operations.record_expense(
                        business_id=biz["business_id"],
                        category=category,
                        amount=amount,
                        description=description.strip(),
                        owner_email=owner_email,
                    )
                    st.success("Expense saved." if lang == "en" else "Matumizi yamehifadhiwa.")
                    st.rerun()
    with right:
        expenses = get_business_expenses(biz["business_id"], owner_email)
        st.markdown(f"### {t('exp_history', lang)}")
        if expenses:
            st.metric(t("total_rec_exp", lang), money(sum(e["amount"] for e in expenses)))
            df_exp = pd.DataFrame(expenses)[["expense_day", "description", "category", "amount"]].rename(
                columns={
                    "expense_day": "Date" if lang == "en" else "Tarehe",
                    "description": "Description" if lang == "en" else "Maelezo",
                    "category": "Category" if lang == "en" else "Kundi",
                    "amount": "Amount (KSh)" if lang == "en" else "Kiasi (KSh)"
                }
            )
            st.dataframe(df_exp, use_container_width=True, hide_index=True)
        else:
            st.info("No expenses recorded yet." if lang == "en" else "Hakuna matumizi yaliyorekodiwa bado.")

# ============================================================
# 6. SUPPLIER RESTOCKS
# ============================================================
elif page == "Restocks":
    page_header(t("restock_title", lang), t("restock_sub", lang))
    products = get_business_products(biz["business_id"], owner_email)
    if not products:
        st.info("Add products under **📦 Products & stock** before recording restocks." if lang == "en" else "Ongeza bidhaa chini ya **📦 Bidhaa na stoo** kwanza.")
    else:
        product_map = {p["product_name"]: p for p in products}
        chosen_name = st.selectbox(t("select_prod_restock", lang), list(product_map.keys()))
        chosen_p = product_map[chosen_name]
        with st.form("restock_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            qty_added = c1.number_input(t("qty_received", lang), min_value=1.0, value=10.0, step=1.0)
            buy_cost = c2.number_input(
                t("buying_price", lang),
                min_value=0.0,
                value=float(chosen_p["buying_price"]),
                step=1.0
            )
            notes = st.text_input(t("delivery_note", lang), placeholder="e.g. Wholesale delivery")
            submit = st.form_submit_button(t("confirm_restock_btn", lang), type="primary")
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
                    owner_email=owner_email,
                    lang=lang
                )
                st.success(f"Added {qty_added:g} units of {chosen_name} to stock." if lang == "en" else f"Zimeongezwa {qty_added:g} za {chosen_name} kwenye stoo.")
                st.rerun()

# ============================================================
# 7. DAILY RECORDS
# ============================================================
elif page == "Daily records":
    page_header(t("daily_title", lang), t("daily_sub", lang))
    chosen_date = st.date_input(t("choose_date", lang), value=date.today())
    ds = chosen_date.isoformat()
    sales = get_business_sales(biz["business_id"], owner_email, day_str=ds)
    expenses = [e for e in get_business_expenses(biz["business_id"], owner_email) if e["expense_day"] == ds]
    sales_sum = sum(s["total"] for s in sales)
    exp_sum = sum(e["amount"] for e in expenses)
    a, b, c = st.columns(3)
    a.metric(t("sales_on_date", lang), money(sales_sum))
    b.metric(t("exp_on_date", lang), money(exp_sum))
    c.metric(t("sales_less_exp", lang), money(sales_sum - exp_sum))
    st.caption("This is a daily cashflow summary. Inventory restock costs and credit balances are tracked separately." if lang == "en" else "Huu ni muhtasari wa mtiririko wa fedha wa siku.")
    with st.expander("See sales for this date" if lang == "en" else "Angalia mauzo ya tarehe hii", expanded=True):
        if sales:
            sales_df = pd.DataFrame(sales)[
                ["sale_date", "product_name", "quantity", "unit_price", "total", "payment_method", "payment_reference"]
            ].rename(
                columns={
                    "sale_date": t("sales_col_date", lang),
                    "product_name": t("sales_col_product", lang),
                    "quantity": t("sales_col_quantity", lang),
                    "unit_price": t("sales_col_unit_price", lang),
                    "total": t("sales_col_total", lang),
                    "payment_method": t("sales_col_payment", lang),
                    "payment_reference": t("sales_col_payment_reference", lang),
                }
            )
            st.dataframe(
                sales_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No sales recorded on this date." if lang == "en" else "Hakuna mauzo yaliyorekodiwa tarehe hii.")
    with st.expander("See expenses for this date" if lang == "en" else "Angalia matumizi ya tarehe hii", expanded=True):
        if expenses:
            st.dataframe(
                pd.DataFrame(expenses)[["expense_date", "category", "description", "amount"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No expenses recorded on this date." if lang == "en" else "Hakuna matumizi yaliyorekodiwa tarehe hii.")

# ============================================================
# 8. REPORTS
# ============================================================
elif page == "Reports":
    page_header(t("reports_title", lang), t("reports_sub", lang, biz=biz["business_name"]))
    summary = get_business_summary(biz["business_id"], owner_email)
    sales = get_business_sales(biz["business_id"], owner_email)
    expenses = get_business_expenses(biz["business_id"], owner_email)
    total_sales = summary.get("total_revenue", 0.0) if summary else sum(s["total"] for s in sales)
    total_expenses = summary.get("total_expenses", 0.0) if summary else sum(e["amount"] for e in expenses)
    total_restocks = summary.get("total_restock_cost", 0.0) if summary else 0.0
    total_sales = total_sales if total_sales is not None else 0.0
    total_expenses = total_expenses if total_expenses is not None else 0.0
    total_restocks = total_restocks if total_restocks is not None else 0.0
    total_profit = sum(s["estimated_profit"] for s in sales) if sales else 0.0
    a, b, c, d = st.columns(4)
    a.metric(t("total_sales_rev", lang), money(total_sales))
    b.metric(t("est_gross_profit", lang), money(total_profit))
    c.metric(t("total_expenses", lang), money(total_expenses))
    d.metric(t("net_cash_pos", lang), money(total_sales - total_expenses - total_restocks))
    if sales:
        st.markdown("### Daily sales trend" if lang == "en" else "### Mwenendo wa mauzo ya kila siku")
        daily = pd.DataFrame(sales).groupby("sale_day", as_index=False)["total"].sum()
        st.line_chart(daily.set_index("sale_day"))
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### Top selling products" if lang == "en" else "### Bidhaa zinazouzwa zaidi")
            top_prods = pd.DataFrame(sales).groupby("product_name", as_index=False)["total"].sum().sort_values("total", ascending=False)
            st.bar_chart(top_prods.set_index("product_name"))
        with col_r:
            st.markdown("### Sales by Payment Method" if lang == "en" else "### Mauzo kwa njia ya malipo")
            pay_methods = pd.DataFrame(sales).groupby("payment_method", as_index=False)["total"].sum()
            st.bar_chart(pay_methods.set_index("payment_method"))
    else:
        st.info("Once you record sales, your charts and insights will appear here." if lang == "en" else "Ukirekodi mauzo, chati na takwimu zitaonekana hapa.")
    if expenses:
        st.markdown("### Expenses by category" if lang == "en" else "### Matumizi kwa makundi")
        expdf = pd.DataFrame(expenses).groupby("category", as_index=False)["amount"].sum()
        st.bar_chart(expdf.set_index("category"))

st.divider()
st.caption(t("footer_caption", lang))