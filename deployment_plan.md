# Permanent Hosting Deployment Plan

This guide outlines how to host your FastAPI backend permanently on **Render**, providing a stable public URL for your Tally and WhatsApp integrations.

## 1. Prerequisites
- A **GitHub** account with your code pushed to a repository.
- A **Render** account (linked to GitHub).

## 2. Infrastructure Architecture
- **Web Service**: Runs your FastAPI app.
- **Database**: Managed PostgreSQL (replaces local `jobs.db` for cloud persistence).
- **Domain**: Automated SSL and custom DNS management.

## 3. Step-by-Step Deployment

### Step A: Push to GitHub
1. Create a new repository on GitHub.
2. Initialize and push your local code:
   ```bash
   git init
   git add .
   git commit -m "chore: initial deployment commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

### Step B: Setup on Render
1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Click **New** > **Blueprint**.
3. Select your repository.
4. Render will automatically detect the `render.yaml` file I've provided.
5. Review the plan and click **Apply**.

### Step C: Configure Secrets
In the Render dashboard, go to your Web Service > **Environment** and ensure these are set:
- `TALLY_WEBHOOK_SECRET`: (Your Tally secret)
- `WHATSAPP_ACCESS_TOKEN`: (Your Meta access token)
- `WHATSAPP_PHONE_NUMBER_ID`: `944751125397273`
- `WA_ADMIN_NUMBER`: `13027728945`
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: `tillian_ai_secure_token_2024`
- `OPENAI_API_KEY`: (Your OpenAI key)
- `GOOGLE_SERVICE_ACCOUNT_JSON`: (Paste the entire content of `credentials.json`)
- `DATABASE_URL`: (Render will auto-generate this if using the Blueprint)

### Step D: Custom Domains
1. Go to **Settings** > **Custom Domains**.
2. Add `api.tillianai.com`.
3. Follow the DNS instructions to point your CNAME record to Render.

## 4. Final Public URLs
Once deployed, update your configurations with these stable links:

- **Tally Webhook**: `https://api.tillianai.com/ingest`
- **WhatsApp Webhook**: `https://api.tillianai.com/webhook`
- **WABA Configuration**: Use `tillian_ai_secure_token_2024` as the Verify Token.

## 5. Persistence Note
I recommend migrating from SQLite to **PostgreSQL** for cloud production. The provided `render.yaml` includes a managed PostgreSQL instance. Your `app/db.py` can be easily updated to use `DATABASE_URL` instead of `jobs.db`.
