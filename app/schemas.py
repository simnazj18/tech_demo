from pydantic import BaseModel
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class AzureAccountCreate(BaseModel):
    name: str
    client_id: str
    client_secret: str
    tenant_id: str
    keyvault_url: str

class AzureAccountResponse(AzureAccountCreate):
    id: int
    class Config:
        from_attributes = True
