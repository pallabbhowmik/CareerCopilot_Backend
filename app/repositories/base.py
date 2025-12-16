"""
Base Repository

Abstract base class for all repositories with common CRUD operations.
Implements soft delete and audit trail support.
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.models import Base, SoftDeleteMixin


T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository providing common data access patterns.
    
    Features:
    - Generic CRUD operations
    - Soft delete support
    - Pagination
    - Filtering
    - Audit trails
    """
    
    def __init__(self, db: Session, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
    
    # =========================================================================
    # CREATE
    # =========================================================================
    
    def create(self, entity_data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            entity_data: Dictionary of entity attributes
            
        Returns:
            Created entity instance
        """
        entity = self.model_class(**entity_data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def create_batch(self, entities_data: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple entities in a single transaction.
        
        Args:
            entities_data: List of dictionaries with entity attributes
            
        Returns:
            List of created entity instances
        """
        entities = [self.model_class(**data) for data in entities_data]
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities
    
    # =========================================================================
    # READ
    # =========================================================================
    
    def get_by_id(self, entity_id: int, include_deleted: bool = False) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Primary key ID
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            Entity instance or None
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.id == entity_id
        )
        
        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query.first()
    
    def get_by_uuid(self, uuid_str: str, include_deleted: bool = False) -> Optional[T]:
        """
        Get entity by UUID.
        
        Args:
            uuid_str: UUID string
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            Entity instance or None
        """
        if not hasattr(self.model_class, 'uuid'):
            raise AttributeError(f"{self.model_class.__name__} does not have a uuid field")
        
        query = self.db.query(self.model_class).filter(
            self.model_class.uuid == uuid_str
        )
        
        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query.first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            List of entity instances
        """
        query = self.db.query(self.model_class)
        
        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_filter(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[T]:
        """
        Get entities matching filter criteria.
        
        Args:
            filters: Dictionary of field:value pairs
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            List of matching entity instances
        """
        query = self.db.query(self.model_class)
        
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                if isinstance(value, list):
                    query = query.filter(getattr(self.model_class, field).in_(value))
                else:
                    query = query.filter(getattr(self.model_class, field) == value)
        
        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, filters: Optional[Dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """
        Count entities matching optional filters.
        
        Args:
            filters: Optional dictionary of field:value pairs
            include_deleted: Whether to count soft-deleted entities
            
        Returns:
            Count of matching entities
        """
        query = self.db.query(self.model_class)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) == value)
        
        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query.count()
    
    def exists(self, entity_id: int, include_deleted: bool = False) -> bool:
        """Check if entity exists by ID"""
        return self.get_by_id(entity_id, include_deleted) is not None
    
    # =========================================================================
    # UPDATE
    # =========================================================================
    
    def update(self, entity_id: int, update_data: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity.
        
        Args:
            entity_id: Primary key ID
            update_data: Dictionary of fields to update
            
        Returns:
            Updated entity instance or None if not found
        """
        entity = self.get_by_id(entity_id)
        if not entity:
            return None
        
        for field, value in update_data.items():
            if hasattr(entity, field) and field not in ['id', 'uuid', 'created_at']:
                setattr(entity, field, value)
        
        # Update timestamp if available
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update_batch(self, updates: List[Dict[str, Any]]) -> List[T]:
        """
        Update multiple entities.
        
        Args:
            updates: List of dicts with 'id' and update fields
            
        Returns:
            List of updated entities
        """
        updated = []
        for update_item in updates:
            entity_id = update_item.pop('id', None)
            if entity_id:
                entity = self.update(entity_id, update_item)
                if entity:
                    updated.append(entity)
        return updated
    
    # =========================================================================
    # DELETE
    # =========================================================================
    
    def delete(self, entity_id: int, soft: bool = True) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: Primary key ID
            soft: If True, perform soft delete; if False, hard delete
            
        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(entity_id, include_deleted=not soft)
        if not entity:
            return False
        
        if soft and hasattr(entity, 'is_deleted'):
            entity.is_deleted = True
            entity.deleted_at = datetime.utcnow()
            self.db.commit()
        else:
            self.db.delete(entity)
            self.db.commit()
        
        return True
    
    def restore(self, entity_id: int) -> Optional[T]:
        """
        Restore a soft-deleted entity.
        
        Args:
            entity_id: Primary key ID
            
        Returns:
            Restored entity or None if not found
        """
        entity = self.get_by_id(entity_id, include_deleted=True)
        if not entity or not hasattr(entity, 'is_deleted'):
            return None
        
        entity.is_deleted = False
        entity.deleted_at = None
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def refresh(self, entity: T) -> T:
        """Refresh entity from database"""
        self.db.refresh(entity)
        return entity
    
    def commit(self):
        """Commit current transaction"""
        self.db.commit()
    
    def rollback(self):
        """Rollback current transaction"""
        self.db.rollback()
