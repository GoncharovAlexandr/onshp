from pydantic import BaseModel

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    address: str

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    address: str

    class Config:
        from_attributes = True