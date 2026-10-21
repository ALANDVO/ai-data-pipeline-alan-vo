"""SQLAlchemy database models for persistent storage."""
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, Boolean, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PipelineModel(Base):
    """Persistent pipeline model."""
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    nodes: Mapped[str] = mapped_column(Text, default="[]")
    edges: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)
    created_by: Mapped[str] = mapped_column(String(255), default="")
    last_run_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Relationships
    jobs: Mapped[List["JobModel"]] = relationship("JobModel", back_populates="pipeline", cascade="all, delete-orphan")

    def get_nodes(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.nodes) if self.nodes else []
        except json.JSONDecodeError:
            return []

    def get_edges(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.edges) if self.edges else []
        except json.JSONDecodeError:
            return []

    def set_nodes(self, nodes: List[Dict[str, Any]]):
        self.nodes = json.dumps(nodes)

    def set_edges(self, edges: List[Dict[str, Any]]):
        self.edges = json.dumps(edges)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "status": self.status, "nodes": self.get_nodes(), "edges": self.get_edges(),
            "created_at": self.created_at, "updated_at": self.updated_at,
            "created_by": self.created_by,
            "last_run_at": self.last_run_at, "last_status": self.last_status,
        }


class JobModel(Base):
    """Persistent job model."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    triggered_by: Mapped[str] = mapped_column(String(255), default="")
    started_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    pipeline: Mapped["PipelineModel"] = relationship("PipelineModel", back_populates="jobs")
    tasks: Mapped[List["TaskModel"]] = relationship("TaskModel", back_populates="job", cascade="all, delete-orphan")


class TaskModel(Base):
    """Persistent task model."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[str] = mapped_column(Text, default="{}")

    # Relationships
    job: Mapped["JobModel"] = relationship("JobModel", back_populates="tasks")

    def get_output(self) -> Dict[str, Any]:
        try:
            return json.loads(self.output) if self.output else {}
        except json.JSONDecodeError:
            return {}

    def set_output(self, output: Dict[str, Any]):
        self.output = json.dumps(output)


class QualityScoreModel(Base):
    """Persistent quality score model."""
    __tablename__ = "quality_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    completeness: Mapped[float] = mapped_column(Float, default=0)
    validity: Mapped[float] = mapped_column(Float, default=0)
    consistency: Mapped[float] = mapped_column(Float, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    timeliness: Mapped[float] = mapped_column(Float, default=0)
    overall: Mapped[float] = mapped_column(Float, default=0)
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    __table_args__ = (Index("ix_quality_pipeline_created", "pipeline_id", "created_at"),)

    def get_details(self) -> Dict[str, Any]:
        try:
            return json.loads(self.details) if self.details else {}
        except json.JSONDecodeError:
            return {}

    def set_details(self, details: Dict[str, Any]):
        self.details = json.dumps(details)


class LogEntryModel(Base):
    """Persistent log entry model."""
    __tablename__ = "log_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    pipeline_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)

    __table_args__ = (
        Index("ix_logs_job_created", "job_id", "created_at"),
        Index("ix_logs_pipeline_created", "pipeline_id", "created_at"),
    )

    def get_context(self) -> Dict[str, Any]:
        try:
            return json.loads(self.context) if self.context else {}
        except json.JSONDecodeError:
            return {}

    def set_context(self, context: Dict[str, Any]):
        self.context = json.dumps(context)


# Type annotations for mypy
PipelineModel.nodes: Mapped[str]
PipelineModel.edges: Mapped[str]
TaskModel.output: Mapped[str]
QualityScoreModel.details: Mapped[str]
LogEntryModel.context: Mapped[str]