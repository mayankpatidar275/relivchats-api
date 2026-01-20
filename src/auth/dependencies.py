from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Annotated

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from clerk_backend_api.models import ClerkBaseError

from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)

# Initialize Clerk client once (module-level)
try:
    clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
    logger.info("Clerk client initialized")
except Exception as e:
    logger.critical(f"Failed to initialize Clerk client: {e}", exc_info=True)
    clerk_client = None

bearer_scheme = HTTPBearer()


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
) -> str:
    """
    Authenticate request and extract user ID
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    
    if not clerk_client:
        logger.critical("Clerk client not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )
    
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
                authorized_parties=[getattr(settings, 'FRONTEND_URL', None)] 
                if hasattr(settings, 'FRONTEND_URL') else None
            )
        )
        
        if not request_state.is_signed_in:
            logger.warning(
                f"Authentication failed: {request_state.reason}",
                extra={"extra_data": {"reason": request_state.reason}}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {request_state.reason}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user ID from token payload
        user_id = request_state.payload.get('sub')
        
        if not user_id:
            logger.error("Token missing user ID (sub claim)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug("User authenticated successfully", extra={"user_id": user_id})
        
        return user_id
        
    except ClerkBaseError as e:
        logger.error(f"Clerk authentication error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(
            f"Unexpected authentication error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )