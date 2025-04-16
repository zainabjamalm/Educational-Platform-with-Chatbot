from pydantic import BaseModel
from typing import Optional
from typing import Literal
from datetime import datetime
class CourseModel(BaseModel):
    course_title: str
    course_description: str
    prerequisites: Optional[str] = None
    tags: Optional[str] = None
    
class UserRegister(BaseModel):
    email: str
    username: str
    password: str
    role: str 

class UserLogin(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    user_id: int
    course_id: Optional[int] = None
    message: str
    agent: Literal["agent1", "agent2"]

class ChatResponse(BaseModel):
    agent: str
    message: str
    timestamp: datetime
