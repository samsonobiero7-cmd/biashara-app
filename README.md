# Biashara Manager

Track your small business's products, sales, stock, and expenses in one place.

## Deployment configuration

1. Create a Supabase project. In **Connect**, copy the **Session pooler**
   connection URI; keep it private.
2. In Google Cloud, create an OAuth client with application type **Web
   application**. Add your deployed Streamlit app's callback URL to its
   authorized redirect URIs:
   `https://YOUR_APP_URL/oauth2callback`
3. In Streamlit Community Cloud, open the app's **Settings → Secrets** and
   copy the structure from `.streamlit/secrets.toml.example`. Replace the
   placeholders with the full Supabase URI, the Google client ID and secret,
   your deployed callback URL, and a long random `cookie_secret`.
4. Save the secrets and redeploy. Database tables are created by the app on
   startup. Every signed-in user's businesses and records are scoped to their
   verified Google email.

Never put the real connection URI, OAuth client secret, or cookie secret in
GitHub, source files, screenshots, or chat. Do not share the Supabase database
password.

The current SQLite database is test data and is not imported into Supabase.
The app's backup download is scoped to the signed-in owner's businesses.

## Experimental offline checkout

The offline sales page is a separate, installable test page at
`/app/static/offline/index.html`. Each device must sign in and open the online
Sales page first so its business and full product list are saved locally. While
offline, the page can record sales and add products with their opening stock,
buying price, selling price, and reorder level. Each pack size should be a
separate product with its own stock and price. New offline products sync before
sales that use them when the user signs in again and opens the online Sales
page. Open the offline page once while online so its files are cached; then it
can record sales and products without a connection.

Keep `OFFLINE_CHECKOUT_ENABLED` unset or `false` on the live deployment. Only
enable it on a separate test deployment connected to a separate test database;
offline test sales sync into whichever database that deployment uses.

Offline products and sales stay in that device's browser until the user signs in
again and opens the online Sales page. Do not clear the browser's site data or
uninstall the offline page until all pending records have synced. An offline
product with a name that already exists in the business must be resolved by
refreshing the catalog and using the existing product. If several devices record
sales while disconnected, synced sales are kept and stock that falls below zero
must be checked by the business owner. Use a device protected with a screen lock;
offline products and pending sales are stored locally in that browser.

