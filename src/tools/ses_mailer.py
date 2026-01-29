from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

DATA_SERIES_PATH = Path("data/output/data_series.json")

def broadcast_risk_alert_ses(
    target_date: str,
    aws_access_key: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_region: str = os.getenv("AWS_REGION", "us-east-1"),
    sender_email: str = "ysun258@wisc.edu",
    placeholder_recipient: str = "zshzbg@gmail.com"
) -> str:
    """
    Scans the processed data for a specific date, identifies high-risk regions,
    and sends alerts via AWS SES V2.
    """
    
    # 1. Load Data
    if not DATA_SERIES_PATH.exists():
        return f"Error: Processed data file not found at {DATA_SERIES_PATH}. Please run 'demo' first."
    
    try:
        with open(DATA_SERIES_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        return f"Error reading data file: {e}"

    if target_date not in data:
        return f"No data found for date: {target_date}. Available dates: {list(data.keys())[:3]}..."

    # 2. Filter High Risk
    daily_records = data[target_date]
    high_risk_events = [
        item for item in daily_records 
        if item.get("riskLevel", "").lower() == "high"
    ]

    if not high_risk_events:
        return f"No 'high' risk events detected for {target_date}. Operations normal."

    # 3. Initialize SES Client
    # If keys are not provided, boto3 will look for env vars or ~/.aws/credentials
    try:
        ses_client = boto3.client(
            'sesv2',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
         return f"Failed to initialize AWS SES Client: {e}"

    sent_count = 0
    errors = []

    # 4. Aggregate and Send Single Email
    if not high_risk_events:
        return f"No 'high' risk events detected for {target_date}. Operations normal."

    # Build the list of affected areas
    affected_areas_text = ""
    for event in high_risk_events:
        county = event.get("nameFull", "Unknown County")
        state = event.get("state", "US")
        risk_type = event.get("riskType", "General Risk")
        affected_areas_text += f"- {county}, {state} (Risk: {risk_type})\n"

    count = len(high_risk_events)
    subject = f"🚨 URGENT: High Supply Chain Risk Detected in {count} Regions ({target_date})"
    
    body_text = (
        f"SUPPLY CHAIN ALERT REPORT\n"
        f"Date: {target_date}\n"
        f"Severity: HIGH\n\n"
        f"The AI Control Tower has detected critical risk levels in the following {count} regions:\n\n"
        f"{affected_areas_text}\n"
        f"IMMEDIATE ACTION REQUIRED:\n"
        f"1. Review inventory buffers for affected regions.\n"
        f"2. Contact suppliers in these counties.\n"
        f"3. Monitor real-time status on the dashboard.\n\n"
        f"🔗 Access Live Control Tower: https://oact-sepia.vercel.app/\n\n"
        f"--\n"
        f"AI Control Tower | System Automated Alert"
    )

    try:
        response = ses_client.send_email(
            FromEmailAddress=sender_email,
            Destination={
                'ToAddresses': [placeholder_recipient]
            },
            Content={
                'Simple': {
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': body_text,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            }
        )
        
        # Log to Dashboard File
        try:
            alert_log_path = Path("data/output/alerts.json")
            new_entry = {
                "timestamp": target_date,
                "location": f"{count} Regions (Consolidated)",
                "score": "HIGH",
                "recipient": placeholder_recipient,
                "status": "SENT (SES V2)"
            }
            
            existing_alerts = []
            if alert_log_path.exists():
                with open(alert_log_path, "r") as f:
                    existing_alerts = json.load(f)
            
            existing_alerts.insert(0, new_entry)
            
            with open(alert_log_path, "w") as f:
                json.dump(existing_alerts[:20], f, indent=2)
        except Exception as log_err:
            print(f"Dashboard logging failed: {log_err}")

        return f"✅ Consolidated alert sent to {placeholder_recipient} covering {count} high-risk regions."

    except NoCredentialsError:
            return "AWS Credentials not found. Please configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
    except ClientError as e:
        return f"❌ SES Error: {e.response['Error']['Message']}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

