from fastapi import Request, HTTPException, status
from jose import JWTError
from auth import decode_access_token
from database import admin_collection
import traceback


def get_current_admin(request: Request):
    """
    Dependency that ensures the admin is authenticated using JWT from cookies.
    Extracts the access_token cookie, verifies it, and returns the admin username.
    """
    try:
        token = request.cookies.get("access_token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please log in.",
            )

        username = decode_access_token(token)

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token. Please log in again.",
            )

        admin = admin_collection.find_one({"username": username})
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found in database.",
            )

        return username

    except JWTError as e:
        print("[ERROR] JWT decode failed:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed. Please log in again.",
        )

    except Exception as e:
        print("[ERROR] Unexpected error in get_current_admin:", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected authentication error occurred.",
        )
