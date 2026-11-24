# Biashara Manager

Biashara Manager uses Google OpenID Connect for sign-in and Supabase
PostgreSQL for persistent business records.

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

