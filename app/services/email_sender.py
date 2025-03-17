import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

import aiosmtplib

from app.core.config import settings


async def send_email_async(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: str,
    smtp_config: Dict[str, any],
    sender_name: str,
    sender_email: str,
    tracking_id: Optional[str] = None,
) -> bool:
    """
    Send an email asynchronously.
    """
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender_email}>"
    message["To"] = recipient_email
    
    # Add text part
    text_part = MIMEText(body_text, "plain")
    message.attach(text_part)
    
    # Add HTML part with tracking pixel if tracking_id is provided
    if tracking_id:
        # Add tracking pixel
        tracking_url = f"{settings.API_V1_STR}/emails/tracking/{tracking_id}"
        tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" />'
        html_with_tracking = body_html + tracking_pixel
        html_part = MIMEText(html_with_tracking, "html")
    else:
        html_part = MIMEText(body_html, "html")
    
    message.attach(html_part)
    
    # Send email
    try:
        smtp = aiosmtplib.SMTP(
            hostname=smtp_config["host"],
            port=smtp_config["port"],
            use_tls=smtp_config["use_tls"],
        )
        
        await smtp.connect()
        await smtp.login(smtp_config["username"], smtp_config["password"])
        await smtp.send_message(message)
        await smtp.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def send_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: str,
    smtp_config: Dict[str, any],
    sender_name: str,
    sender_email: str,
    tracking_id: Optional[str] = None,
) -> bool:
    """
    Send an email synchronously by running the async function in a new event loop.
    """
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            send_email_async(
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                smtp_config=smtp_config,
                sender_name=sender_name,
                sender_email=sender_email,
                tracking_id=tracking_id,
            )
        )
        return result
    finally:
        loop.close() 