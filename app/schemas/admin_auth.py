from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class AdminLoginResponse(BaseModel):
    admin: AdminUserResponse


class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
