import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

BOT_COLUMNS = [
    "timestamp_iso",
    "sender",
    "normalized_sender",
    "message_text",
    "command",
    "result",
    "submission_id"
]

COLUMNS = [
    "timestamp_iso",
    "submission_id",
    "validation_status",
    "rejection_reasons_joined",
    "posted_status",
    "posted_at_iso",
    "override_used",
    "missing_fields_joined",
    "whatsapp_message_id",
    "raw_payload_json",
    "llm_extracted_json",
]

WEBHOOK_COLUMNS = [
    "timestamp_iso",
    "whatsapp_message_id",
    "recipient_id",
    "status",
    "raw_payload_json"
]

class SheetsClient:
    def __init__(self):
        self.spreadsheet_id = settings.google_sheet_id
        self.tab_name = settings.google_sheet_tab
        self.webhook_tab_name = settings.google_sheet_webhook_tab
        self.bot_tab_name = settings.bot_log_sheet_tab
        self.json_path = settings.google_service_account_json_path
        self.service = None
        
        self._authenticate()

    def _authenticate(self):
        try:
            # Try loading from ENV VAR first (for Cloud Hosting)
            env_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_DATA")
            
            if env_creds:
                logger.info("Authenticating with Google Service Account from Environment Variable")
                creds_dict = json.loads(env_creds)
                credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            elif self.json_path and os.path.exists(self.json_path):
                logger.info(f"Authenticating with Google Service Account from file: {self.json_path}")
                credentials = service_account.Credentials.from_service_account_file(self.json_path, scopes=SCOPES)
            else:
                logger.error("No Google Service Account credentials found (no file and no GOOGLE_SERVICE_ACCOUNT_JSON_DATA env var)")
                return

            self.service = build('sheets', 'v4', credentials=credentials)
            self._ensure_tabs_exist()
        except Exception as e:
            logger.exception(f"Failed to authenticate with Google Sheets API: {e}")

    def _ensure_tabs_exist(self):
        if not self.service or not self.spreadsheet_id:
            return
            
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            existing_tabs = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', [])]
            
            required_tabs = [self.tab_name, self.webhook_tab_name, self.bot_tab_name]
            for tab in required_tabs:
                if not tab: continue
                if tab not in existing_tabs:
                    logger.info(f"Tab '{tab}' not found. Attempting to create it...")
                    batch_update_request_body = {
                        'requests': [
                            {
                                'addSheet': {
                                    'properties': {
                                        'title': tab
                                    }
                                }
                            }
                        ]
                    }
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body=batch_update_request_body
                    ).execute()
                    logger.info(f"Successfully created tab '{tab}'.")
                else:
                    logger.info(f"Verified existence of tab '{tab}'.")
        except Exception as e:
            logger.error(f"Error while verifying/creating tabs: {e}")

    def append_bot_log(self, row_data: Dict[str, Any]):
        if not self.service or not self.spreadsheet_id:
            return False
            
        values = []
        for col in BOT_COLUMNS:
            val = row_data.get(col, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(str(val))
            
        body = { 'values': [values] }
        
        try:
            append_range = f"'{self.bot_tab_name}'!A1:G1"
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=append_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to append bot log row: {e}")
            return False

    def append_webhook_log(self, row_data: Dict[str, Any]):
        if not self.service or not self.spreadsheet_id:
            return False
            
        values = []
        for col in WEBHOOK_COLUMNS:
            val = row_data.get(col, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(str(val))
            
        body = { 'values': [values] }
        
        try:
            append_range = f"'{self.webhook_tab_name}'!A1:E1"
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=append_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to append webhook log row: {e}")
            return False

    def append_submission(self, row_data: Dict[str, Any]):
        if not self.service or not self.spreadsheet_id:
            return False
            
        values = []
        for col in COLUMNS:
            val = row_data.get(col, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(str(val))
            
        body = { 'values': [values] }
        
        try:
            append_range = f"'{self.tab_name}'!A1:K1"
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=append_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to append submission row: {e}")
            return False

sheets_client = SheetsClient()
