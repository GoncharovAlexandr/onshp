from pydantic import BaseModel, EmailStr, Field

class AdminRegister(BaseModel):
    email: EmailStr = Field(..., example="admin@example.com")
    password: str = Field(..., min_length=6, example="adminpass")

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class AdminOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True
