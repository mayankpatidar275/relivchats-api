from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from typing import Annotated

# Import from the recommended Clerk SDK
from clerk_backend_api import Clerk
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions
from clerk_backend_api.models import ClerkBaseError

# Assuming your settings are correctly configured
from ..config import settings

# Initialize Clerk with your secret key from environment variables
# It's good practice to create a single SDK instance and reuse it.
# Consider using a global instance or a dependency injection pattern
# if your application structure allows for it.
# For simplicity here, we'll initialize it in the dependency.
# In a real application, you might want to initialize this once
# when your FastAPI app starts up.
clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
bearer_scheme = HTTPBearer()

async def get_current_user_id_clerk(
    request: Request, # FastAPI's Request object
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
):
    try:
        # For authenticate_request, you might need to construct a pseudo-httpx.Request
        # or use a library that bridges FastAPI's Request to httpx.Request.
        # A simpler approach might be to extract the token and verify it directly,
        # or to ensure Clerk's SDK can work directly with FastAPI's Request headers.

        # Let's assume for now that authenticate_request needs the full request object.
        # FastAPI's Request object contains headers, which is what authenticate_request uses.
        # We need to create an httpx.Request-like object from FastAPI's Request.
        # This is a common pattern when integrating libraries expecting httpx.Request.
        # For simplicity, if authenticate_request *only* needs headers, we can pass them directly.

        # However, the `authenticate_request` method in the guide takes an `httpx.Request` object.
        # FastAPI's `Request` object is not directly compatible with `httpx.Request`.
        # You would need to convert it.

        # A more direct approach using clerk-backend-api's token verification:
        # The `authenticate_request` is typically for frontend-to-backend communication
        # where the request object itself might contain specific Clerk headers.
        # If you are purely verifying a Bearer token from the Authorization header,
        # you might use a different method of the SDK or implement the verification
        # logic similarly to your initial code but with the new SDK.

        # Let's re-examine the guide for `verify_token` for sessions, as in your original code.
        # The new SDK has `sessions.verify_token` or `m2m.verify_token`.
        # Since you are getting `session_token`, `sessions.verify_token` seems appropriate.

        session_token = credentials.credentials
        session = clerk_client.sessions.verify_token(session_token) # Using the new SDK's method
        return session.user_id

    except ClerkBaseError as e: # Catch the specific base error from the new SDK
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during authentication."
        )

# Example usage in a FastAPI endpoint
# from fastapi import APIRouter
# router = APIRouter()
#
# @router.get("/protected-route")
# async def read_protected_data(user_id: Annotated[str, Depends(get_current_user_id_clerk)]):
#     return {"message": f"Hello, user {user_id}! This is protected data."}