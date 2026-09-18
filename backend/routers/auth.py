"""
Authentication routes: /register and /login.

Flow:
  Register -> validate input -> hash password -> store in MongoDB -> 201
  Login    -> find user -> verify password -> issue JWT -> return token
"""

from fastapi import APIRouter, HTTPException

from ..db.database import (
    UserAlreadyExistsError,
    create_user,
    find_user_by_email,
    find_user_by_username,
)
from ..models.user import LoginRequest, UserCreate, User
from ..core.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(payload: UserCreate):
    """Create a new account. Returns the user + a JWT token."""
    # Pydantic already validated field lengths/types via UserCreate.

    # Check email doesn't already exist
    if find_user_by_email(str(payload.email)):
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Check username doesn't already exist
    if find_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken.")

    # Hash the password BEFORE storing — never store plain text.
    password_hash = hash_password(payload.password)

    try:
        user = create_user(payload, password_hash)
    except UserAlreadyExistsError as exc:
        # Race condition: another request registered the same email meanwhile.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = create_access_token(user.id)

    return {
        "token": token,
        "user": user.model_dump(mode="json"),
    }


@router.post("/login")
def login(payload: LoginRequest):
    """Log in with email OR username. Returns a JWT token."""
    identifier = payload.identifier.strip().lower()

    # Try email first, then username.
    user_doc = (
        find_user_by_email(identifier)
        or find_user_by_username(identifier)
    )

    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not verify_password(payload.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    user = User.from_doc(user_doc)
    token = create_access_token(user.id)

    return {
        "token": token,
        "user": user.model_dump(mode="json"),
    }