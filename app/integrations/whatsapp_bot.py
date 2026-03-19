import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

import app.db as db
from app.config import settings
from app.integrations.whatsapp import wa_client
from app.integrations.sheets import sheets_client
import app.integrations.job_ops as job_ops

logger = logging.getLogger(__name__)

def normalize_phone(phone: str) -> str:
    """
    Normalizes a phone number by removing all non-digit characters.
    Example: '+1 (302) 772-8945' -> '13027728945'
    """
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)

def is_admin(normalized_sender: str) -> bool:
    """
    Checks if the normalized sender is in the WHATSAPP_ADMIN_ALLOWLIST.
    """
    allowlist = [normalize_phone(n.strip()) for n in settings.whatsapp_admin_allowlist.split(",") if n.strip()]
    return normalized_sender in allowlist

def get_submission_summary(submission: Dict[str, Any]) -> str:
    """
    Generates a concise summary for a submission.
    """
    llm_data = json.loads(submission.get("llm_extracted_json", "{}"))
    return (
        f"ID: {submission['submission_id']}\n"
        f"Role: {llm_data.get('job_title', 'N/A')}\n"
        f"Location: {llm_data.get('location', 'N/A')}\n"
        f"Status: {submission['approval_status']}"
    )

async def handle_command(sender: str, text: str) -> str:
    """
    Parses and executes an inbound command from a WhatsApp admin.
    Returns the response message to be sent back.
    """
    normalized_sender = normalize_phone(sender)
    
    # Security Check
    if not is_admin(normalized_sender):
        logger.warning(f"Unauthorized command attempt from {sender} (Normalized: {normalized_sender})")
        # Log unauthorized attempt
        db.insert_bot_log(sender, normalized_sender, text, "UNAUTHORIZED", "Rejected: Not in allowlist")
        if settings.enable_sheets_log:
            sheets_client.append_bot_log({
                "timestamp_iso": datetime.now(timezone.utc).isoformat(),
                "sender": sender,
                "normalized_sender": normalized_sender,
                "message_text": text,
                "command": "UNAUTHORIZED",
                "result": "Rejected: Not in allowlist",
                "submission_id": ""
            })
        return "Unauthorized: Your number is not in the admin allowlist."

    # Parse Command
    parts = text.strip().split()
    if not parts:
        return "No command received. Type HELP for supported commands."

    cmd = parts[0].upper()
    args = parts[1:]
    
    result_text = ""
    submission_id = args[0] if args else None
    parsed_cmd = cmd

    if cmd == "HELP":
        result_text = (
            "Supported commands:\n"
            "APPROVE <submission_id>\n"
            "REJECT <submission_id>\n"
            "STATUS <submission_id>\n"
            "RESEND <submission_id>\n"
            "LIST PENDING\n"
            "HELP"
        )
    
    elif cmd == "LIST" and args and args[0].upper() == "PENDING":
        parsed_cmd = "LIST PENDING"
        pending = db.get_pending_submissions(limit=10)
        if not pending:
            result_text = "No pending submissions found."
        else:
            lines = ["Pending Submissions:"]
            for p in pending:
                llm_data = json.loads(p.get("llm_extracted_json", "{}"))
                lines.append(f"- {p['submission_id']} | {llm_data.get('job_title', 'N/A')}")
            result_text = "\n".join(lines)
            
    elif cmd in ["APPROVE", "REJECT", "STATUS", "RESEND"]:
        if not submission_id:
            result_text = f"Error: {cmd} requires a <submission_id>."
        else:
            submission = db.get_submission(submission_id)
            if not submission:
                result_text = f"Error: Submission {submission_id} not found."
            else:
                if cmd == "STATUS":
                    llm_data = json.loads(submission.get("llm_extracted_json", "{}"))
                    result_text = (
                        f"Submission: {submission['submission_id']}\n"
                        f"Validation: {submission['validation_status']}\n"
                        f"Posting Status: {submission['approval_status']}\n"
                        f"WhatsApp Status: {submission.get('posted_status', 'N/A')}\n"
                        f"Role: {llm_data.get('job_title', 'N/A')}\n"
                        f"Location: {llm_data.get('location', 'N/A')}"
                    )
                
                elif cmd == "APPROVE":
                    if submission["approval_status"] == "APPROVED":
                        result_text = f"Submission {submission_id} is already APPROVED."
                    elif submission["approval_status"] != "PENDING":
                        result_text = f"Submission {submission_id} is in {submission['approval_status']} state and cannot be approved."
                    else:
                        # Call existing approval logic from main or trigger it here
                        # We will simulate the call to keep logic consistent
                        try:
                            result = await job_ops.approve_job_logic(submission_id)
                            if result.get("status_code") == 200:
                                result_text = f"Submission {submission_id} approved.\nWhatsApp send triggered."
                            else:
                                result_text = f"Error: {result.get('error')}"
                        except Exception as e:
                            result_text = f"Error during approval: {str(e)}"
                
                elif cmd == "REJECT":
                    db.update_submission_status(submission_id, approval_status="REJECTED")
                    result_text = f"Submission {submission_id} rejected successfully."
                
                elif cmd == "RESEND":
                    if submission["approval_status"] != "APPROVED":
                        result_text = f"Error: Can only resend APPROVED submissions. Current status: {submission['approval_status']}"
                    elif submission.get("posted_status") != "FAILED":
                        result_text = f"Error: Can only resend FAILED WhatsApp attempts. Current status: {submission.get('posted_status')}"
                    else:
                        try:
                            result = await job_ops.retry_job_logic(submission_id)
                            if result.get("status_code") == 200:
                                result_text = f"Retry triggered for submission {submission_id}."
                            else:
                                result_text = f"Error: {result.get('error')}"
                        except Exception as e:
                            result_text = f"Error during resend: {str(e)}"
    else:
        result_text = f"Unknown command: {cmd}. Type HELP for options."

    # Log Bot Activity
    db.insert_bot_log(sender, normalized_sender, text, parsed_cmd, result_text, submission_id)
    if settings.bot_log_to_sheets:
        sheets_client.append_bot_log({
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "sender": sender,
            "normalized_sender": normalized_sender,
            "message_text": text,
            "command": parsed_cmd,
            "result": result_text,
            "submission_id": submission_id or ""
        })

    return result_text

async def check_service_window(normalized_sender: str) -> bool:
    """
    Checks if a customer service window is open for this admin.
    Rule: Received an inbound message in the last 24 hours.
    """
    last_ts = db.get_last_admin_interaction(normalized_sender)
    if not last_ts:
        return False
    
    last_interaction = datetime.fromisoformat(last_ts)
    if last_interaction.tzinfo is None:
        last_interaction = last_interaction.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    return now - last_interaction < timedelta(hours=24)
