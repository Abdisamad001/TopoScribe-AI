import os

from sqlalchemy import Boolean, Column, DateTime, Text, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"connect_timeout": 10})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class Design(Base):
    __tablename__ = "designs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    topology = Column(JSONB, nullable=False)
    is_favourite = Column(Boolean, nullable=False, server_default=text("false"), index=True)
    is_template = Column(Boolean, nullable=False, server_default=text("false"), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    last_opened_at = Column(DateTime(timezone=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)


class Project(Base):
   

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    design_ids = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class Report(Base):
  

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    markdown = Column(Text, nullable=False)
    design_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class Chat(Base):


    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    title = Column(Text, nullable=False)
    messages = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    design_id = Column(Text, nullable=True)
    design_name = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
