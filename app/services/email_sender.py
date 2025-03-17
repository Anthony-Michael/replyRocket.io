import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

import aiosmtplib

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)


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
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        body_text: Plain text email body
        body_html: HTML email body
        smtp_config: SMTP configuration dictionary
        sender_name: Name of the sender
        sender_email: Email address of the sender
        tracking_id: Optional tracking ID for open tracking
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    # Create the email message
    message = create_email_message(
        recipient_email=recipient_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sender_name=sender_name,
        sender_email=sender_email,
        tracking_id=tracking_id
    )
    
    # Send the email
    return await send_smtp_message(message, smtp_config)


def create_email_message(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: str,
    sender_name: str,
    sender_email: str,
    tracking_id: Optional[str] = None,
) -> MIMEMultipart:
    """
    Create an email message with text and HTML parts.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        body_text: Plain text email body
        body_html: HTML email body
        sender_name: Name of the sender
        sender_email: Email address of the sender
        tracking_id: Optional tracking ID for open tracking
        
    Returns:
        MIME message ready to be sent
    """
    # Create message container
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender_email}>"
    message["To"] = recipient_email
    
    # Add text part
    text_part = MIMEText(body_text, "plain")
    message.attach(text_part)
    
    # Add HTML part with tracking pixel if needed
    html_content = add_tracking_pixel(body_html, tracking_id) if tracking_id else body_html
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    return message


def add_tracking_pixel(html_content: str, tracking_id: str) -> str:
    """
    Add a tracking pixel to HTML content.
    
    Args:
        html_content: Original HTML content
        tracking_id: Tracking ID for the pixel URL
        
    Returns:
        HTML content with tracking pixel added
    """
    tracking_url = f"{settings.API_V1_STR}/emails/tracking/{tracking_id}"
    tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" />'
    return html_content + tracking_pixel


async def send_smtp_message(message: MIMEMultipart, smtp_config: Dict[str, any]) -> bool:
    """
    Send a message using SMTP.
    
    Args:
        message: MIME message to send
        smtp_config: SMTP configuration dictionary
        
    Returns:
        True if email was sent successfully, False otherwise
    """
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
        
        logger.info(f"Email sent successfully to {message['To']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
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
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        body_text: Plain text email body
        body_html: HTML email body
        smtp_config: SMTP configuration dictionary
        sender_name: Name of the sender
        sender_email: Email address of the sender
        tracking_id: Optional tracking ID for open tracking
        
    Returns:
        True if email was sent successfully, False otherwise
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