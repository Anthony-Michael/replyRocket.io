# Service Layer for ReplyRocket.io

This directory contains service modules that implement business logic for the ReplyRocket.io application. The service layer follows the principles of separation of concerns and single responsibility, keeping business logic separate from data access operations.

## Service Modules

- **ai_email_generator.py**: Handles AI-powered email content generation using OpenAI's API
- **email_sender.py**: Manages the actual sending of emails via SMTP
- **campaign_service.py**: Business logic for campaign management
- **email_service.py**: Business logic for email operations
- **user_service.py**: Business logic for user authentication and management

## Design Principles

The service layer follows these design principles:

1. **Separation of Concerns**: Services handle business logic, while CRUD modules handle data access
2. **Single Responsibility**: Each function has a clear, focused purpose
3. **Error Handling**: Consistent error handling with appropriate logging
4. **Validation**: Input validation is performed at the service layer
5. **Transaction Management**: Database transactions are managed at the service layer

## Usage Guidelines

When adding new functionality to the application:

1. Place database operations in the appropriate CRUD module
2. Place business logic in the appropriate service module
3. Keep API endpoints thin, delegating to services for business logic
4. Handle errors consistently using the error handling utilities
5. Log important events at the appropriate level

## Example

```python
# In an API endpoint
@router.post("/campaigns", response_model=schemas.Campaign)
def create_campaign(
    db: Session = Depends(deps.get_db),
    campaign_in: schemas.CampaignCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    # Delegate to the service layer
    return campaign_service.create_campaign(db, campaign_in, current_user.id)

# In the service layer
def create_campaign(db: Session, campaign_in: schemas.CampaignCreate, user_id: UUID) -> models.EmailCampaign:
    try:
        # Business logic here
        logger.info(f"Creating campaign '{campaign_in.name}' for user {user_id}")
        
        # Delegate to CRUD for data access
        return crud.campaign.create_with_user(db, obj_in=campaign_in, user_id=user_id)
    except SQLAlchemyError as e:
        # Error handling
        logger.error(f"Database error creating campaign: {str(e)}")
        handle_db_error(e, "Error creating campaign") 