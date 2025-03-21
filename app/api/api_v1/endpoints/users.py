from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=schemas.User)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    password: str = Body(None),
    full_name: str = Body(None),
    company_name: str = Body(None),
    email: EmailStr = Body(None),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    current_user_data = jsonable_encoder(current_user)
    user_in = schemas.UserUpdate(**current_user_data)
    
    if password is not None:
        user_in.password = password
    if full_name is not None:
        user_in.full_name = full_name
    if company_name is not None:
        user_in.company_name = company_name
    if email is not None:
        user_in.email = email
    
    user = user_service.update_user(db, current_user.id, user_in)
    return user


@router.post("/smtp-config", response_model=schemas.User)
def update_smtp_config(
    *,
    db: Session = Depends(deps.get_db),
    smtp_config: schemas.SMTPConfig,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update SMTP configuration for the current user.
    """
    user = user_service.update_smtp_config(
        db=db,
        user_id=current_user.id,
        smtp_config={
            "smtp_host": smtp_config.smtp_host,
            "smtp_port": str(smtp_config.smtp_port),
            "smtp_user": smtp_config.smtp_user,
            "smtp_password": smtp_config.smtp_password,
            "smtp_use_tls": smtp_config.smtp_use_tls,
        },
    )
    return user


# Admin endpoints

@router.get("", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve users. Admin only.
    """
    # Get users through the service layer
    users = user_service.get_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new user. Admin only.
    """
    # Create user through the service layer
    user = user_service.create_user(db, user_in)
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = user_service.get_user(db, user_id)
    
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update a user. Admin only.
    """
    # Update user through the service layer
    user = user_service.update_user(db, user_id, user_in)
    return user 