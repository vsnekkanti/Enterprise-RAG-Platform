from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

user_acl_groups = Table(
    "user_acl_groups",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("acl_group_name", String(255), ForeignKey("acl_groups.name"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    api_token = Column(String(512), unique=True, nullable=False)
    acl_groups = relationship(
        "AclGroup",
        secondary=user_acl_groups,
        backref="users"
    )
    created_at = Column(DateTime, default=datetime.utcnow)

class AclGroup(Base):
    __tablename__ = "acl_groups"
    name = Column(String(255), primary_key=True)
    description = Column(Text)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    source = Column(String(512), nullable=False)
    filename = Column(String(512), nullable=False)
    acl_group = Column(String(255), ForeignKey("acl_groups.name"))
    minio_path = Column(String(512), nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
