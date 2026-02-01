from typing import Generic, TypeVar, Type
from sqlalchemy.orm import Session

from app.core.exceptions import OHSRemoteException

ModelType = TypeVar("ModelType")


class RepositoryException(OHSRemoteException):
    pass


class RecordNotFoundError(RepositoryException):
    pass


class DuplicateRecordError(RepositoryException):
    pass


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, record_id: int) -> ModelType | None:
        if not record_id:
            raise ValueError("record_id is required")
        
        return self.db.query(self.model).filter(self.model.id == record_id).first()

    def get_by_id_or_fail(self, record_id: int) -> ModelType:
        record = self.get_by_id(record_id)
        if not record:
            raise RecordNotFoundError(f"{self.model.__name__} with id {record_id} not found")
        return record

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        if skip < 0:
            raise ValueError("skip must be non-negative")
        
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, entity: ModelType) -> ModelType:
        if not entity:
            raise ValueError("entity cannot be None")
        
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: ModelType) -> ModelType:
        if not entity:
            raise ValueError("entity cannot be None")
        
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, record_id: int) -> None:
        if not record_id:
            raise ValueError("record_id is required")
        
        record = self.get_by_id_or_fail(record_id)
        self.db.delete(record)
        self.db.commit()

    def exists(self, record_id: int) -> bool:
        if not record_id:
            raise ValueError("record_id is required")
        
        return self.db.query(self.model).filter(self.model.id == record_id).first() is not None

    def count(self) -> int:
        return self.db.query(self.model).count()
