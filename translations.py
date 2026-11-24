TEXTS = {
    "en": {
        "biz_registered": "Business '{name}' registered successfully with ID {id}.",
        "no_activity": "No activity recorded yet in Biashara.",
        "summary_title": "=== BIASHARA DAILY SUMMARY ===",
        "shop_label": "Biashara",
        "date_label": "Date",
        "no_activity_date": "No Activity",
        "transactions_label": "Transactions",
        "revenue_label": "Revenue",
        "expenses_label": "Expenses",
        "restock_label": "Restock Cost",
        # --- New Payment & Checkout Keys ---
        "payment_method": "Payment Method",
        "payment_ref": "Payment Reference / Code (e.g., M-Pesa Code)",
        "cash": "Cash",
        "mpesa": "M-Pesa",
        "visa_card": "Visa / Card",
        "bank_transfer": "Bank Transfer",
        "sale_success": "Sale recorded successfully! ID: {id} | Total: KES {total} | Paid via: {method}",
        "duplicate_payment_ref": "Duplicate payment reference '{ref}' already exists.",
    },
    "sw": {
        "biz_registered": (
            "Biashara '{name}' imesajiliwa kwa mafanikio na namba {id}."
        ),
        "no_activity": "Hakuna shughuli iliyorekodiwa bado kwenye Biashara.",
        "summary_title": "=== RIPOTI YA KILA SIKU YA BIASHARA ===",
        "shop_label": "Biashara",
        "date_label": "Tarehe",
        "no_activity_date": "Hakuna Shughuli",
        "transactions_label": "Mauzo",
        "revenue_label": "Mapato",
        "expenses_label": "Matumizi",
        "restock_label": "Gharama za Bidhaa",
        # --- New Payment & Checkout Keys (Kiswahili) ---
        "payment_method": "Njia ya Malipo",
        "payment_ref": "Nambari ya Rejea ya Malipo / Nambari ya M-Pesa",
        "cash": "Fedha Taslimu",
        "mpesa": "M-Pesa",
        "visa_card": "Kadi ya Benki / Visa",
        "bank_transfer": "Uhamisho wa Benki",
        "sale_success": "Mauzo yamerekodiwa vizuri! Nambari: {id} | Jumla: KES {total} | Imelipwa kwa: {method}",
        "duplicate_payment_ref": "Nambari ya muamala '{ref}' tayari imetumika.",
    },
}


def get_text(key, lang="en", **kwargs):
    """Fetches the translated text and injects any dynamic variables."""
    lang_dict = TEXTS.get(lang, TEXTS["en"])
    text = lang_dict.get(key, key)
    return text.format(**kwargs)