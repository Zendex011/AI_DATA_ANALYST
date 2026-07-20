from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.core.crypto import encrypt_secret
from app.models.schemas import (
    SignupRequest,
    TokenResponse,
    ApiKeyUpdateRequest,
    ApiKeyStatusResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(400, "An account with this email already exists")

    user = User(email=req.email, hashed_password=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Uses OAuth2PasswordRequestForm (username + password fields) rather than
    a plain JSON body, specifically so Swagger's built-in "Authorize" button
    works against this endpoint directly -- `username` is treated as the
    email address here.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.put("/api-key", response_model=ApiKeyStatusResponse)
def set_api_key(
    req: ApiKeyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lets a user supply their own Gemini API key so their usage bills to
    their own Google account instead of the app owner's. Stored encrypted
    (see app/core/crypto.py) -- never returned back in plaintext by any
    endpoint, including this one.
    """
    if not req.gemini_api_key.strip():
        raise HTTPException(400, "API key cannot be empty")

    current_user.gemini_api_key = encrypt_secret(req.gemini_api_key.strip())
    db.commit()
    return ApiKeyStatusResponse(has_custom_key=True)


@router.get("/api-key", response_model=ApiKeyStatusResponse)
def get_api_key_status(current_user: User = Depends(get_current_user)):
    """Never returns the key itself -- only whether one is set."""
    return ApiKeyStatusResponse(has_custom_key=current_user.gemini_api_key is not None)


@router.delete("/api-key", response_model=ApiKeyStatusResponse)
def delete_api_key(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Removes the user's own key -- they fall back to the app's shared key."""
    current_user.gemini_api_key = None
    db.commit()
    return ApiKeyStatusResponse(has_custom_key=False)
