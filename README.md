# WhatsApp Job Poster POC

A production-ready FastAPI backend that securely ingests job postings from Tally Forms, validates them using OpenAI Structured Extraction, manages an approval queue, and interacts with administrators via a WhatsApp Bot.

---

## 🚀 Key Features
- **OpenAI Extraction**: Smartly extracts `job_title`, `location`, `salary`, `work_authorization`, and `job_summary` from unstructured text.
- **WhatsApp Admin Bot**: Full command-line control over submissions (`APPROVE`, `REJECT`, `LIST PENDING`, `STATUS`) directly via WhatsApp chat.
- **Persistence & Logging**: Dual-layer logging to **SQLite** (local persistence) and **Google Sheets** (centralized observability).
- **Service Window Intelligence**: Outbound notifications respect the WhatsApp 24-hour service window policy.
- **Production Grade**: Ready for deployment on **Render** with custom domains (`api.tillianai.com`) and secure credential handling.

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
- Python 3.9+
- OpenAI API Key
- Meta WhatsApp Cloud API credentials
- Google Service Account JSON (for Sheets logging)

### 2. Setup
```bash
# Clone and install
git clone <repo-url>
cd <repo-dir>
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Fill in your secrets in .env
```

### 3. Run Locally
```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Start a tunnel (e.g., ngrok)
ngrok http 8000
```
*Your public URL: `https://<tunnel-id>.ngrok-free.app`*

---

## 📝 Tally Integration

### 1. Form Setup
Your Tally form should have these exact labels (or synonyms defined in `app/tally_mapping.py`):
- **Submitter Name** (Short text)
- **Job Description** (Long text, >200 chars)
- **Force Send Even If Missing** (Checkbox/Radio)

### 2. Webhook Settings
- **URL**: `https://<public-url>/ingest`
- **Method**: `POST`
- **Custom Header**: `X-Tally-Secret` = `<your_tally_webhook_secret>`

---

## 🤖 WhatsApp Admin Bot Usage

The bot allows authorized administrators (defined in `WHATSAPP_ADMIN_ALLOWLIST`) to manage the system via chat.

| Command | Description | Example |
| :--- | :--- | :--- |
| `HELP` | List available commands | `HELP` |
| `LIST PENDING` | Show recent pending jobs | `LIST PENDING` |
| `APPROVE <id>` | Post job to WhatsApp | `APPROVE abc-123` |
| `REJECT <id>` | Reject job | `REJECT abc-123` |
| `STATUS <id>` | Check job status | `STATUS abc-123` |
| `RESEND <id>` | Retry failed send | `RESEND abc-123` |

---

## 🌐 Production Deployment (Render)

### 1. GitHub Deploy
- Push your repository to GitHub.
- Create a new **Web Service** on Render and connect your repository.

### 2. Render Configuration
- **Start Command**: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`
- **Build Command**: `pip install -r requirements.txt`
- **Environment Variables**: Add all `.env` variables. 
- **Google Credentials**: Securely paste your service account JSON into `GOOGLE_SERVICE_ACCOUNT_JSON_DATA`.

### 3. Custom Domain
- Point `api.tillianai.com` (CNAME) to your Render internal URL (`your-app.onrender.com`).

---

## ⚙️ Configuration (.env Reference)

```env
# SECURITY
TALLY_WEBHOOK_SECRET=...
WHATSAPP_WEBHOOK_VERIFY_TOKEN=...

# WHATSAPP API
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_TEMPLATE_NAME=job_post_notification
WHATSAPP_TEMPLATE_LANG=en
WA_ADMIN_NUMBER=...

# BOT SETTINGS
ENABLE_WHATSAPP_BOT=true
WHATSAPP_ADMIN_ALLOWLIST=... # Comma-separated numbers (e.g., 13027728945)

# GOOGLE SHEETS
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON_DATA=... # JSON string for production

# OPENAI
OPENAI_API_KEY=...
ENABLE_OPENAI_PARSE=true
```

---

## ✅ Final Production Verification Checklist
1. [ ] Server responds at `https://api.tillianai.com/tally-health`
2. [ ] Tally `/ingest` returns 200 and logs to `Submissions` tab.
3. [ ] WhatsApp Bot responds to `HELP` from authorized number.
4. [ ] `BotLog` and `DeliveryLog` tabs are correctly populated in Sheets.
