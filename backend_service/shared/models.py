"""Database models for the video subtitle generation system."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


class MediaType(enum.Enum):
    """Media type enumeration."""
    MOVIE = "movie"
    TV = "tv"


class ExistenceStatus(enum.Enum):
    """Media existence status."""
    EXISTS = "exists"
    DELETED = "deleted"


class TaskStatus(enum.Enum):
    """Task processing status."""
    PENDING = "pending"
    METADATA_FETCHING = "metadata_fetching"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HistoryStatus(enum.Enum):
    """Processing history status."""
    SUCCESS = "success"
    FAILED = "failed"


class MediaLibrary(Base):
    """Media library table storing discovered media metadata."""

    __tablename__ = "media_library"

    # Primary key
    media_id = Column(Integer, primary_key=True, autoincrement=True)

    # Media identifiers
    tmdb_id = Column(String(50), nullable=True, index=True)
    imdb_id = Column(String(50), nullable=True, index=True)

    # Media type and metadata
    media_type = Column(Enum(MediaType), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    overview = Column(Text, nullable=True)
    cast = Column(Text, nullable=True)  # JSON array stored as text

    # TV show specific fields
    season = Column(Integer, nullable=True)
    episode = Column(Integer, nullable=True)
    episode_overview = Column(Text, nullable=True)

    # File paths
    nfo_file_path = Column(String(1000), nullable=False, unique=True, index=True)
    video_file_path = Column(String(1000), nullable=False, index=True)
    subtitle_file_path = Column(String(1000), nullable=True)
    poster_path = Column(String(1000), nullable=True)
    directory_path = Column(String(1000), nullable=False, index=True)

    # Status
    existence_status = Column(
        Enum(ExistenceStatus),
        nullable=False,
        default=ExistenceStatus.EXISTS,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("TaskQueue", back_populates="media", cascade="all, delete-orphan")
    history = relationship("ProcessingHistory", back_populates="media", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_media_type_status', 'media_type', 'existence_status'),
        Index('idx_tv_show_season_episode', 'title', 'season', 'episode'),
    )


class TaskQueue(Base):
    """Task queue table tracking items pending or in-progress processing."""

    __tablename__ = "task_queue"

    # Primary key
    task_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to media
    media_id = Column(Integer, ForeignKey('media_library.media_id', ondelete='CASCADE'), nullable=False, index=True)

    # File paths (denormalized for quick access)
    nfo_file_path = Column(String(1000), nullable=False, index=True)
    video_file_path = Column(String(1000), nullable=False)

    # Status and processing info
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    failure_reason = Column(Text, nullable=True)

    # Worker assignment
    worker_assignment = Column(String(100), nullable=True, index=True)

    # Timing information
    queued_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_time = Column(DateTime, nullable=True)
    timeout_deadline = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    media = relationship("MediaLibrary", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_media_status', 'media_id', 'status'),
    )


class ProcessingHistory(Base):
    """Processing history table for immutable audit log."""

    __tablename__ = "processing_history"

    # Primary key
    history_id = Column(Integer, primary_key=True, autoincrement=True)

    # References
    task_id = Column(Integer, nullable=False, index=True)
    media_id = Column(Integer, ForeignKey('media_library.media_id', ondelete='CASCADE'), nullable=False, index=True)

    # Status and results
    status = Column(Enum(HistoryStatus), nullable=False, index=True)
    processing_duration_seconds = Column(Integer, nullable=True)
    failure_reason = Column(String(200), nullable=True)
    error_details = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    media = relationship("MediaLibrary", back_populates="history")

    # Indexes
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_media_status', 'media_id', 'status'),
    )
