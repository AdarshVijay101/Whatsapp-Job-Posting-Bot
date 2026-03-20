import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.validators.guardrails import JobSubmission, ParsedJobData
from app.integrations.openai_parser import parse_job_description
from app.integrations.whatsapp import wa_client
from app.integrations.sheets import sheets_client
import app.integrations.whatsapp_bot as whatsapp_bot
import app.integrations.job_ops as job_ops
import app.db as db

from fastapi.middleware.cors import CORSMiddleware
import time
import hashlib

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("api")

app = FastAPI(title="WhatsApp Job Poster POC")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory cache for validation results
# Key: sha256(job_description), Value: (timestamp, ParsedJobData)
validation_cache = {}

# Simple rate limiting for /validate-job
# Key: client_ip, Value: last_request_time
rate_limit_store = {}


@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "wa_configured": bool(settings.whatsapp_access_token),
        "sheets_configured": sheets_client.is_functional(),
        "openai_configured": bool(settings.openai_api_key),
        "server_time": datetime.now(timezone.utc).isoformat()
    }

@app.get("/tally-health")
def tally_health_check(request: Request):
    """
    Lightweight endpoint for Tally (or user) to verify tunnel connectivity.
    """
    return {
        "status": "online",
        "endpoint": "/ingest",
        "method": "POST",
        "auth_header_required": "X-Tally-Secret",
        "public_url_hint": str(request.base_url)
    }

@app.post("/validate-job")
async def validate_job(request: Request):
    """
    Validates a job description using OpenAI extraction without logging or sending messages.
    Includes caching and basic rate limiting.
    """
    client_host = request.client.host if request.client else "unknown"
    
    # Basic rate limiting (1 request per 2 seconds per IP)
    now = time.time()
    if client_host in rate_limit_store:
        if now - rate_limit_store[client_host] < 2:
            return JSONResponse(status_code=429, content={"error": "too_many_requests", "detail": "Please wait between validation requests."})
    rate_limit_store[client_host] = now

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid_json"})

    job_description = payload.get("job_description", "").strip()
    submitter_name = payload.get("submitter_name", "Anonymous")

    if len(job_description) < 180:
        return JSONResponse(status_code=400, content={"error": "too_short", "detail": "Job description must be at least 180 characters."})

    # Normalize and Hash
    normalized_desc = " ".join(job_description.split())
    job_hash = hashlib.sha256(normalized_desc.encode()).hexdigest()

    # Cache Check
    if job_hash in validation_cache:
        cached_ts, cached_data = validation_cache[job_hash]
        if now - cached_ts < settings.validation_cache_ttl:
            logger.info(f"[CACHE HIT] Returning cached result for hash {job_hash[:8]}")
            return cached_data

    # Perform Extraction
    try:
        # Mocking a JobSubmission object for the parser
        # We only care about job_description and submitter_name for the LLM part
        mock_submission = JobSubmission(
            submitter_name=submitter_name,
            recruiter_email="placeholder@example.com",
            job_description=job_description
        )
        
        parsed_llm_data = await parse_job_description(mock_submission)
        
        result = {
            "missing_fields": parsed_llm_data.missing_fields,
            "extracted_data": parsed_llm_data.model_dump(),
            "status": "success" if not parsed_llm_data.missing_fields else "missing_info"
        }
        
        # Cache the result
        validation_cache[job_hash] = (now, result)
        
        return result
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return JSONResponse(status_code=500, content={"error": "parsing_failed", "detail": str(e)})

@app.post("/ingest")
async def ingest_job(request: Request):
    """
    Ingests a raw payload from Tally webhook.
    Validates signature, attempts parsing & guardrails, formats, sends to WA, and logs to Sheets.
    """
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"--- Incoming Webhook Request from {client_host} ---")

    # Security check: TALLY_WEBHOOK_SECRET
    tally_secret_header = request.headers.get("X-Tally-Secret")
    expected_secret = settings.tally_webhook_secret
    
    # Debug logging (safe version)
    received_part = (tally_secret_header[:4] + "****") if tally_secret_header else "MISSING"
    expected_part = (expected_secret[:4] + "****") if expected_secret else "MISSING_IN_CONFIG"
    
    if not tally_secret_header:
        logger.warning(f"[AUTH FAILED] X-Tally-Secret header is missing from {client_host}")
        return JSONResponse(status_code=401, content={"error": "unauthorized", "detail": "X-Tally-Secret header is missing"})

    if tally_secret_header != expected_secret:
        logger.warning(f"[AUTH FAILED] Secret mismatch. Received: {received_part}, Expected: {expected_part}")
        return JSONResponse(status_code=401, content={"error": "unauthorized", "detail": "Invalid X-Tally-Secret value"})
    
    logger.info(f"[AUTH SUCCESS] Header matched ({received_part})")

    try:
        raw_payload = await request.json()
    except Exception:
        logger.error("Failed to parse JSON body from webhook")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON", "detail": "The request body must be valid JSON"})

    # Validate high-level Tally shape
    if "data" not in raw_payload or "fields" not in raw_payload["data"]:
        logger.error(f"Invalid Tally payload shape: {json.dumps(raw_payload)[:200]}...")
        return JSONResponse(status_code=400, content={
            "error": "invalid_payload", 
            "detail": "Tally payload is missing 'data.fields' structure. Ensure this is a standard Tally webhook."
        })

    submission_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Received submission {submission_id}")

    # Parse Tally structure
    parsed_data, seen_labels = job_ops.parse_tally_payload(raw_payload)
    mapped_keys = list(parsed_data.keys())

    # Step 1: Validate Payload with Guardrails
    validation_status = "PASSED"
    rejection_reasons = []
    job_data = None
    parsed_llm_data = None
    job_hash = None
    override_used = 0
    missing_fields_joined = ""
    llm_json_str = ""
    
    try:
        job_data = JobSubmission(**parsed_data)
        job_hash = job_data.generate_hash()
        
        if db.check_duplicate_hash(job_hash):
            validation_status = "REJECTED"
            rejection_reasons.append("Duplicate job submission detected (same submitter and description snippet).")
            job_data = None
            
    except ValidationError as e:
        validation_status = "REJECTED"
        for error in e.errors():
            loc = ".".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "")
            rejection_reasons.append(f"{loc}: {msg}")
            
    # Step 2: OpenAI Structured Extraction
    if validation_status == "PASSED" and job_data:
        try:
            parsed_llm_data = await parse_job_description(job_data)
            llm_json_str = parsed_llm_data.model_dump_json()
            
            # Missing fields check logic
            if parsed_llm_data.missing_fields:
                missing_fields_joined = ", ".join(parsed_llm_data.missing_fields)
                if not job_data.force_send_even_if_missing:
                    validation_status = "REJECTED_MISSING_FIELDS"
                    rejection_reasons.append(f"Missing required extraction fields: {missing_fields_joined}")
                else:
                    validation_status = "PASSED_WITH_OVERRIDE"
                    override_used = 1
                    # Fill missing
                    for mf in parsed_llm_data.missing_fields:
                        if hasattr(parsed_llm_data, mf):
                            setattr(parsed_llm_data, mf, "N/A")
                            
                    # Re-dump to capture the overrides
                    llm_json_str = parsed_llm_data.model_dump_json()

            # --- VERIFICATION LOGS ---
            logger.info(f"[VERIFY] Raw Parsed Tally: {json.dumps(parsed_data)}")
            logger.info(f"[VERIFY] OpenAI Extracted JSON: {llm_json_str}")
            logger.info(f"[VERIFY] Missing Fields: {parsed_llm_data.missing_fields}")
            
            # Preview WhatsApp params
            preview_params = [
                parsed_llm_data.job_title, parsed_llm_data.location, 
                parsed_llm_data.salary, parsed_llm_data.work_authorization,
                job_data.submitter_name, parsed_llm_data.job_summary, 
                parsed_llm_data.application_link
            ]
            logger.info(f"[VERIFY] Preview WhatsApp Params Order: {preview_params}")
            # -------------------------
                    
        except Exception as e:
            logger.error(f"LLM Parsing Failed: {e}")
            validation_status = "REJECTED_PARSING_FAILED"
            rejection_reasons.append(str(e))

    # Step 3: Save to Database
    posted_status = "SKIPPED"
    posted_at = ""
    wa_message_id = ""
    wa_prefill_link = ""
    
    if validation_status in ["PASSED", "PASSED_WITH_OVERRIDE"]:
        posted_status = "PENDING"
        # Optional: We no longer build a prefill link the old way. 
        # But we must satisfy the return payload which expects wa_prefill_link.
        wa_prefill_link = "Omitted in OpenAI refactor flow"
        
    db.insert_submission(
        submission_id=submission_id,
        validation_status=validation_status,
        approval_status=posted_status,
        raw_payload_json=json.dumps(raw_payload),
        timestamp_iso=timestamp,
        job_hash=job_hash,
        llm_extracted_json=llm_json_str,
        override_used=override_used,
        missing_fields_joined=missing_fields_joined
    )

    # Step 4: Log to Sheets
    if settings.enable_sheets_log:
        row_data = {
            "timestamp_iso": timestamp,
            "submission_id": submission_id,
            "validation_status": validation_status,
            "rejection_reasons_joined": " | ".join(rejection_reasons),
            "posted_status": posted_status,
            "posted_at_iso": posted_at,
            "override_used": override_used,
            "missing_fields_joined": missing_fields_joined,
            "whatsapp_message_id": wa_message_id,
            "raw_payload_json": json.dumps(raw_payload),
            "llm_extracted_json": llm_json_str
        }
        success = sheets_client.append_row(row_data)
        logger.info(f"[VERIFY] Google Sheets Append Result: {'SUCCESS' if success else 'FAILED'}")

    # Step 4: Return JSON response
    response_data = {
        "submission_id": submission_id,
        "validation_status": validation_status,
    }

    # Optional Bot Notification (if window open)
    if validation_status == "PASSED" and settings.enable_whatsapp_bot and settings.enable_bot_pending_notification:
        admin_number = settings.wa_admin_number
        norm_admin = whatsapp_bot.normalize_phone(admin_number)
        if await whatsapp_bot.check_service_window(norm_admin):
            notification_text = (
                f"🔔 *New Job Pending Approval*\n"
                f"ID: {submission_id}\n"
                f"Submitter: {job_data.submitter_name}\n"
                f"Role: {parsed_llm_data.job_title}\n\n"
                f"Reply with: APPROVE {submission_id}"
            )
            await wa_client.send_text_message(admin_number, notification_text)
            logger.info(f"[BOT] Proactive notification sent to admin {admin_number}")

    if settings.debug_tally_mapping:
        response_data["debug"] = {
            "seen_labels": seen_labels,
            "mapped_keys": mapped_keys
        }
    
    if validation_status.startswith("REJECTED"):
        logger.error(f"Payload validation/parsing failed: {rejection_reasons}")
        response_data["rejection_reasons"] = rejection_reasons
        if "missing_fields" in missing_fields_joined:
            response_data["missing_fields"] = parsed_llm_data.missing_fields if parsed_llm_data else []
        return JSONResponse(status_code=400, content=response_data)
        
    response_data["posted_status"] = posted_status
    if wa_message_id:
        response_data["whatsapp_message_id"] = wa_message_id
    response_data["wa_prefill_link"] = wa_prefill_link
    
    return JSONResponse(status_code=200, content=response_data)

@app.post("/approve/{submission_id}")
async def approve_job(submission_id: str):
    """
    Approves a PENDING job submission and triggers the WhatsApp template.
    """
    result = await job_ops.approve_job_logic(submission_id)
    status_code = result.pop("status_code", 200)
    return JSONResponse(status_code=status_code, content=result)

@app.post("/retry/{submission_id}")
async def retry_job(submission_id: str):
    """
    Retries sending a WhatsApp template for a job that previously failed.
    """
    result = await job_ops.retry_job_logic(submission_id)
    status_code = result.pop("status_code", 200)
    return JSONResponse(status_code=status_code, content=result)

from fastapi import FastAPI, Request, Query, HTTPException, Response

@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Endpoint for Meta API webhook verification.
    """
    logger.info(f"--- Webhook Verification Request ---")
    logger.info(f"Mode: {hub_mode}")
    logger.info(f"Challenge: {hub_challenge}")
    
    # Token check
    if hub_mode == "subscribe" and hub_verify_token == "12345":
        logger.info("[SUCCESS] Webhook token matched.")
        # Meta expects the challenge to be returned as a plain text string
        return Response(content=str(hub_challenge), media_type="text/plain")
    
    logger.warning(f"[FAILED] Token mismatch or invalid mode. Mode: {hub_mode}")
    return Response(content="Forbidden", status_code=403)
    return Response(content="Verification failed", status_code=403)

@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Endpoint for receiving WhatsApp status callbacks and inbound messages.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    logger.info("="*50)
    logger.info(f"[WHATSAPP WEBHOOK RECEIVED]")
    logger.info(json.dumps(payload, indent=2))
    logger.info("="*50)
    
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # --- TYPE 1: STATUS CALLBACKS ---
                statuses = value.get("statuses", [])
                for status in statuses:
                    wa_message_id = status.get("id")
                    status_val = status.get("status")
                    timestamp = status.get("timestamp")
                    recipient_id = status.get("recipient_id")
                    errors = status.get("errors")
                    
                    status_upper = str(status_val).upper()
                    
                    logger.info(f">>> [WEBHOOK_STATUS_EVENT] ID: {wa_message_id} | Status: {status_upper} | To: {recipient_id}")
                    if errors:
                        logger.error(f">>> [WA_ERROR] {json.dumps(errors)}")
                    
                    if wa_message_id:
                        db.update_submission_by_wa_id(wa_message_id, status_upper)
                    
                    if settings.enable_sheets_log and wa_message_id:
                        try:
                            ts_int = int(timestamp)
                            timestamp_iso = datetime.fromtimestamp(ts_int, timezone.utc).isoformat()
                        except (TypeError, ValueError):
                            timestamp_iso = datetime.now(timezone.utc).isoformat()
                            
                        sheets_client.append_webhook_log({
                            "timestamp_iso": timestamp_iso,
                            "whatsapp_message_id": wa_message_id,
                            "recipient_id": recipient_id,
                            "status": status_val,
                            "raw_payload_json": json.dumps(status)
                        })

                # --- TYPE 2: INBOUND MESSAGES (BOT) ---
                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from")
                    text = msg.get("text", {}).get("body", "").strip()
                    msg_id = msg.get("id")
                    
                    logger.info(f">>> [WEBHOOK_INBOUND_MESSAGE] From: {sender} | Text: {text}")
                    
                    if settings.enable_whatsapp_bot and text:
                        # Process Command
                        reply_text = await whatsapp_bot.handle_command(sender, text)
                        
                        # Send Reply (if allowed)
                        if settings.enable_bot_freeform_reply:
                            await wa_client.send_text_message(sender, reply_text)
                            logger.info(f"[BOT] Sent reply to {sender}")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        
    return JSONResponse(status_code=200, content={"status": "received"})

# Startup Diagnostics
@app.on_event("startup")
async def startup_event():
    logger.info("="*50)
    logger.info("🚀 WHATSAPP JOB POSTER BACKEND STARTING")
    logger.info("="*50)
    logger.info(f"LOCAL ENDPOINT: http://localhost:8000/ingest")
    logger.info(f"TALLY WEBHOOK URL: <Your-Public-Tunnel-URL>/ingest")
    logger.info(f"TALLY HEALTH CHECK: <Your-Public-Tunnel-URL>/tally-health")
    logger.info(f"EXPECTED HEADER: X-Tally-Secret: {settings.tally_webhook_secret[:4]}****")
    logger.info("="*50)
