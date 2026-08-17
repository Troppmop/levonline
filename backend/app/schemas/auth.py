import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import UserRole


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    resident_id: uuid.UUID | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    # max_length=72: bcrypt silently ignores bytes beyond 72, so longer
    # inputs would compare unequal in confusing ways; reject them up front.
    password: str = Field(min_length=8, max_length=72)
    full_name: str
    role: UserRole = UserRole.STAFF
    # Required when role=RESIDENT: the existing Resident profile this login
    # grants access to. Must be omitted for every other role.
    resident_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def resident_link_matches_role(self):
        if self.role == UserRole.RESIDENT and self.resident_id is None:
            raise ValueError("resident_id is required when role is 'resident'")
        if self.role != UserRole.RESIDENT and self.resident_id is not None:
            raise ValueError("resident_id may only be set when role is 'resident'")
        return self


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)
