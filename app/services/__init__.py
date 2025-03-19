"""
Service module for ReplyRocket.io

This module provides service-layer functionality for the application,
separating business logic from data access and API handlers.
"""

from app.services.base_service import BaseService
from app.services.user_service import (
    authenticate_user,
    create_user,
    update_user,
    get_user,
    get_user_by_email,
    update_smtp_config,
    delete_user,
    is_active_user,
    is_superuser,
)
from app.services.campaign_service import (
    create_campaign,
    get_campaign,
    get_campaigns,
    get_active_campaigns,
    update_campaign,
    delete_campaign,
    update_campaign_stats,
    configure_ab_testing,
)
from app.services.email_service import (
    create_email,
    get_email,
    get_email_by_tracking_id,
    mark_as_sent,
    mark_as_opened,
    mark_as_replied,
    mark_as_converted,
    get_pending_follow_ups,
    create_follow_up,
    get_emails_by_campaign,
    delete_email,
)
from app.services.email_sender_service import send_email
from app.services.ai_email_generator_service import generate_email, generate_follow_up

# Import service modules
from app.services import campaign_service
from app.services import email_service
from app.services import user_service
from app.services import stats_service
from app.services import follow_up_service

# Services package for AI email generation and email sending 