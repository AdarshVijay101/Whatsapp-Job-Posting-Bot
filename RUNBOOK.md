# System Workflow & Runbook

This document details the critical architectural decisions guiding the Job Poster constraints and outlines how best to manage the distribution flow.

---

## Why WhatsApp Groups & Communities are Constrained

In native business scenarios, organizers often want automated systems to push broadcasts directly into massive WhatsApp Support Groups or open Communities. **We deliberately avoid unofficial Group posting paths (e.g., Selenium network scraping, Baileys reverse-engineering) in this PoC.**

1. **Meta's Official Stance:** The official Meta WhatsApp Cloud API (Graph) absolutely does not support sending texts generically into public user groups or community clusters purely via standard tokens. 
2. **Ban Risks:** Relying on unofficial UI-automating puppeteer scripts to push jobs leads to near-immediate "shadow bans" on the underlying generic phone number.
3. **Loss of Service Integrity:** Reversing API binaries breaks frequently against Meta UI updates, causing downtime.

---

## The Solution: Admin-Moderated Architecture

Instead of broadcasting blindly to groups, this PoC leverages a reliable **Admin-Moderated Flow**.

- Submissions enter the system via Tally webhooks.
- Guardrails scrape out low-effort spam and structure the message cleanly.
- The Meta Cloud API dispatches the polished template strictly to a predefined **Admin Number** (`WA_ADMIN_NUMBER`).
- The Administrator natively receives the message, briefly reviews it on their local device, and taps "Forward" organically to pass the post flawlessly into their respective locked Groups or Communities.

### The `wa.me` Prefill Fallback
Every successful validation returns a formatted `wa_prefill_link` (e.g. `https://wa.me/?text=[escaped_post]`) regardless of backend `ENABLE_WHATSAPP_SEND` settings. This is useful for potential frontend UI overlays where a recruiter can manually trigger the final dispatch if backend infrastructure scales down.

---

## Future Extensions & Modifications

**Approval Queue UI:**
If message volumes exceed Admin bandwidth, the Google Sheets logging base can natively function as a generic Database. A lightweight frontend can be appended allowing Admins to click "Approve" which systematically targets the WhatsApp Cloud API payload retroactively.

**Multi-Admin Rotations:**
The `.env` constraint restricting WhatsApp delivery to a singular `WA_ADMIN_NUMBER` can be expanded smoothly into a comma-delineated list, round-robining daily payloads to localized moderators to maintain continuous 24/7 moderation availability.

**Delivery Webhooks:**
Meta offers native inbound webhooks covering Status Updates. This can be attached later to parse exact `read`/`delivered` receipts seamlessly into the Google Sheet.
