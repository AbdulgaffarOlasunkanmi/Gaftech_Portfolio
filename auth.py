from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
import sys
import traceback

# Load environment variables
load_dotenv()

# Environment configuration
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Setup password hashing context
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Test bcrypt availability
    pwd_context.hash("test")
except Exception as e:
    print("[WARN] bcrypt not available:", e)
    print("[INFO] Falling back to pbkdf2_sha256 for password hashing.")
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# -----------------------------
# Password Hashing Utilities
# -----------------------------


def hash_password(password: str) -> str:
    """
    Hash the given password securely.
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print("[ERROR] Password hashing failed:", e)
        traceback.print_exc()
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored hash.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print("[ERROR] Password verification failed:", e)
        traceback.print_exc()
        return False


# -----------------------------
# JWT Token Utilities
# -----------------------------


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Generate a JWT access token for the given data.
    """
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print("[ERROR] Failed to create JWT token:", e)
        traceback.print_exc()
        raise


def decode_access_token(token: str) -> str | None:
    """
    Decode and validate a JWT access token.
    Returns the username ('sub') if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print("[ERROR] JWT payload missing 'sub'.")
            return None
        return username
    except JWTError as e:
        print("[ERROR] JWT decode error:", e)
        traceback.print_exc()
        return None
    except Exception as e:
        print("[ERROR] Unexpected JWT decode failure:", e)
        traceback.print_exc()
        return None
