from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from bson import ObjectId


class ContactFormSchema(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    created_at: Optional[datetime] = datetime.utcnow()


class AdminSchema(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    username: Optional[str] = None


class Project(BaseModel):
    id: Optional[str]
    title: str
    description: str
    image_url: str
    link: Optional[str] = None
