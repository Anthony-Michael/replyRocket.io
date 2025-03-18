"""
Base service for ReplyRocket.io

This module contains base service functionality for database operations,
replacing the CRUDBase class to align with the service-oriented architecture.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import Base
from app.utils.error_handling import handle_db_error

# Type definitions
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# Set up logger
logger = logging.getLogger(__name__)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base service with default methods for CRUD operations.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize the base service.
        
        Args:
            model: A SQLAlchemy model class
        """
        self.model = model
    
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: ID of the record
            
        Returns:
            Record with the specified ID or None if not found
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__} with ID {id}: {str(e)}")
            handle_db_error(e)
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        try:
            return db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving multiple {self.model.__name__} records: {str(e)}")
            handle_db_error(e)
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Data for creating the record
            
        Returns:
            Created record
        """
        try:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)  # type: ignore
            
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            logger.info(f"Created {self.model.__name__} with ID {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            handle_db_error(e)
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db: Database session
            db_obj: Record to update
            obj_in: Data for updating the record
            
        Returns:
            Updated record
        """
        try:
            obj_data = jsonable_encoder(db_obj)
            
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)
                
            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])
                    
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            logger.info(f"Updated {self.model.__name__} with ID {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__} with ID {db_obj.id}: {str(e)}")
            handle_db_error(e)
    
    def remove(self, db: Session, *, id: Any) -> ModelType:
        """
        Remove a record.
        
        Args:
            db: Database session
            id: ID of the record to remove
            
        Returns:
            Removed record
        """
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                logger.error(f"{self.model.__name__} with ID {id} not found")
                return None
                
            db.delete(obj)
            db.commit()
            
            logger.info(f"Removed {self.model.__name__} with ID {id}")
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error removing {self.model.__name__} with ID {id}: {str(e)}")
            handle_db_error(e) 