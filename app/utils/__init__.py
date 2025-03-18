"""
Utility modules for the ReplyRocket application.

This package contains various utility functions and helpers
used throughout the application to reduce code duplication
and improve maintainability.
"""

from app.utils.validation import (
    validate_campaign_access,
    validate_email_access,
    validate_user_password,
    validate_user_exists
)

from app.utils.error_handling import (
    handle_db_error,
    handle_entity_not_found,
    handle_permission_error,
    create_error_response
)

from app.utils.auth import (
    authenticate_user,
    generate_access_token,
    create_token_response,
    validate_registration_data,
    check_email_not_taken,
    validate_password_strength,
    create_user
)

from app.utils.email import (
    validate_email_content,
    validate_email_request,
    create_email_record,
    schedule_email_sending,
    get_smtp_config,
    create_email_response,
    send_email_in_background,
    update_records_after_sending,
    validate_smtp_config
)

from app.utils.campaign import (
    validate_ab_test_config,
    configure_campaign_ab_testing,
    get_user_campaigns,
    get_active_campaigns,
    create_user_campaign,
    update_user_campaign,
    delete_user_campaign
) 