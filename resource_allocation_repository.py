
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.resource_allocation import ResourceAllocation
from core.constants import ResourceAllocationStatus


class ResourceAllocationRepository:

    @staticmethod
    def create(db: Session, allocation: ResourceAllocation):
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def get(db: Session, allocation_id: UUID):
        return db.scalar(
            select(ResourceAllocation).where(
                ResourceAllocation.id == allocation_id
            )
        )

    @staticmethod
    def has_overlap(
        db: Session,
        resource_column,
        resource_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: UUID | None = None,
    ):
        query = select(ResourceAllocation).where(
            resource_column == resource_id,
            ResourceAllocation.status.in_(
                [
                    ResourceAllocationStatus.SCHEDULED,
                    ResourceAllocationStatus.ACTIVE,
                ]
            ),
            ResourceAllocation.starts_at < ends_at,
            ResourceAllocation.ends_at > starts_at,
        )

        if exclude_id:
            query = query.where(ResourceAllocation.id != exclude_id)

        return db.scalar(query) is not None

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        flight_id: UUID | None = None,
        resource_type=None,
        status=None,
        starts_from: datetime | None = None,
        starts_to: datetime | None = None,
    ):
        query = select(ResourceAllocation)

        if flight_id:
            query = query.where(ResourceAllocation.flight_id == flight_id)

        if resource_type:
            query = query.where(
                ResourceAllocation.resource_type == resource_type
            )

        if status:
            query = query.where(ResourceAllocation.status == status)

        if starts_from:
            query = query.where(
                ResourceAllocation.starts_at >= starts_from
            )

        if starts_to:
            query = query.where(
                ResourceAllocation.starts_at <= starts_to
            )

        query = (
            query
            .order_by(ResourceAllocation.starts_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    @staticmethod
    def save(db: Session, allocation: ResourceAllocation):
        db.commit()
        db.refresh(allocation)
        return allocation
