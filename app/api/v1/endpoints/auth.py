from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# In a real Clerk integration, you'd verify the JWT token from Clerk.
# This is a placeholder dependency.
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Placeholder to get the current authenticated user's ID from a JWT.
    In a real Clerk integration, you would verify the token with Clerk's public keys.
    The frontend should send the Clerk JWT in the Authorization: Bearer header.
    """
    token = credentials.credentials
    # For now, we'll assume the token *is* the user_id for simplicity in testing.
    # Replace this with actual Clerk JWT verification.
    if token.startswith("clerk_user_"): # Example prefix for Clerk user IDs
        return token
    
    # --- REAL CLERK INTEGRATION WOULD GO HERE ---
    # Example using PyJWT (you'd install `python-jose` or `PyJWT`):
    # from jose import jwt
    # from cryptography.hazmat.primitives import serialization
    # from cryptography.hazmat.backends import default_backend
    # import requests

    # try:
    #     # Fetch Clerk's JWKS (JSON Web Key Set) to get public keys
    #     # This should be cached in a production app to avoid fetching on every request
    #     jwks_url = "https://<YOUR_CLERK_FRONTEND_API_URL>/.well-known/jwks.json"
    #     jwks_response = requests.get(jwks_url)
    #     jwks_response.raise_for_status()
    #     jwks = jwks_response.json()

    #     # Find the matching key
    #     header = jwt.get_unverified_header(token)
    #     key = next((k for k in jwks["keys"] if k["kid"] == header["kid"]), None)
    #     if not key:
    #         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found.")

    #     # Decode and verify the token
    #     # Ensure algorithms match Clerk's (e.g., "RS256") and audience/issuer are correct
    #     # You might need to reconstruct the public key using 'n' and 'e' if it's not a direct cert
    #     # For RS256, PyJWT might require `from_jwk` if you install `PyJWT[crypto]`
    #     decoded_token = jwt.decode(
    #         token,
    #         key, # Or a specific public key object if constructed
    #         algorithms=["RS256"],
    #         audience="your_clerk_frontend_api_key", # Replace with your Clerk frontend API key
    #         issuer=f"https://<YOUR_CLERK_FRONTEND_API_URL>/", # Replace with your Clerk frontend API URL
    #         options={"verify_signature": True, "verify_aud": True, "verify_iss": True}
    #     )
    #     user_id = decoded_token.get("sub") # 'sub' is usually the user ID in Clerk JWTs
    #     if not user_id:
    #         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload: missing 'sub'.")
    #     return user_id

    # except jwt.PyJWTError as e:
    #     logger.error(f"JWT decoding/validation error: {e}")
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")
    # except requests.exceptions.RequestException as e:
    #     logger.error(f"Error fetching JWKS from Clerk: {e}")
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication service unavailable.")
    # ---------------------------------------------

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token invalid or missing. (Placeholder for Clerk validation).")

@router.get("/me", summary="Get current user ID (for testing auth)")
async def read_current_user(user_id: str = Depends(get_current_user_id)):
    """
    A simple endpoint to test if authentication is working and returns the user ID.
    The `user_id` will be extracted from the `Authorization: Bearer <token>` header.
    For local testing without Clerk, you can send `Bearer clerk_user_test_id`.
    """
    return {"user_id": user_id}