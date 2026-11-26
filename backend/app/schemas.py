from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class HoldingInput(BaseModel):
    instrument_id: str
    asset_type: str
    quantity: float = Field(gt=0)
    average_cost: float = Field(default=0, ge=0)
    scheme_code: str | None = None


class CopilotRequest(BaseModel):
    portfolio_id: str
    question: str = Field(min_length=2, max_length=1000)


class CsvConfirmation(BaseModel):
    rows: list[HoldingInput]


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
