from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyUpdateRequest(BaseModel):
    gemini_api_key: str


class ApiKeyStatusResponse(BaseModel):
    has_custom_key: bool


class AskAsyncResponse(BaseModel):
    job_id: str
    status: str = "pending"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending" | "running" | "done" | "failed"
    result: Optional[dict[str, Any]] = None


class AskRequest(BaseModel):
    question: str
    file_id: str
    include_chart: bool = False


class AskResponse(BaseModel):
    answer: str
    success: bool
    generated_code: str
    stdout: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retries_used: int = 0
    cached: bool = False
    chart_generated: bool = False
    chart_base64: Optional[str] = None
    chart_url: Optional[str] = None
    chart_error: Optional[str] = None


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: list[str]


class FileListItem(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: list[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DatabaseListItem(BaseModel):
    db_id: str
    label: str
    dialect: str
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryItem(BaseModel):
    source_type: str
    question: str
    answer: str
    generated_code: str
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retries_used: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectDBRequest(BaseModel):
    connection_string: str
    label: str


class ConnectDBResponse(BaseModel):
    db_id: str
    label: str
    dialect: str
    schema_summary: str


class AskDBRequest(BaseModel):
    db_id: str
    question: str
    include_chart: bool = False


class AskDBResponse(BaseModel):
    answer: str
    success: bool
    generated_sql: str
    columns: list[str]
    rows: list[list]
    row_count: int
    truncated: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retries_used: int = 0
    cached: bool = False
    chart_generated: bool = False
    chart_base64: Optional[str] = None
    chart_url: Optional[str] = None
    chart_error: Optional[str] = None
