from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Annotated

# Import from the recommended Clerk SDK
from clerk_backend_api import Clerk
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions
from clerk_backend_api.models import ClerkBaseError

# Assuming your settings are correctly configured
from ..config import settings

# Initialize Clerk client - consider moving to startup event for production
clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
bearer_scheme = HTTPBearer()

async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
) -> str:
    try:
        # Convert FastAPI request to httpx request for Clerk's authenticate_request
        httpx_request = httpx.Request(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers)
        )
        
        # Use Clerk's recommended authenticate_request method
        request_state = clerk_client.authenticate_request(
            httpx_request,
            AuthenticateRequestOptions(
                # Add your frontend domain if needed
                authorized_parties=[getattr(settings, 'FRONTEND_URL', None)] if hasattr(settings, 'FRONTEND_URL') else None
            )
        )
        
        if not request_state.is_signed_in:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {request_state.reason}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user ID from token payload
        user_id = request_state.payload.get('sub')

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_id

    except ClerkBaseError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during authentication."
        )