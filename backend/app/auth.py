import logging
import base64
import time
import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.algorithms import RSAAlgorithm
from .config import settings

logger = logging.getLogger("mkpath.auth")

security = HTTPBearer()

def get_clerk_domain(publishable_key: str) -> str:
    """
    Decodes the Clerk publishable key to extract the instance domain.
    E.g. pk_test_cm9tYW50aWMtYmVhZ2xlLTU5MzAuY2xlcmsuYWNjb3VudHMuZGV2JA
    Decodes to romantic-beagle-5930.clerk.accounts.dev
    """
    if not publishable_key or "_" not in publishable_key:
        return ""
    try:
        parts = publishable_key.split("_")
        b64_part = parts[-1]
        
        # Adjust base64 padding
        padding = len(b64_part) % 4
        if padding:
            b64_part += "=" * (4 - padding)
            
        decoded = base64.b64decode(b64_part).decode("utf-8")
        if decoded.endswith("$"):
            decoded = decoded[:-1]
        return decoded
    except Exception as e:
        logger.error(f"Failed to parse Clerk publishable key: {e}")
        return ""

CLERK_DOMAIN = get_clerk_domain(settings.VITE_CLERK_PUBLISHABLE_KEY)
EXPECTED_ISSUER = f"https://{CLERK_DOMAIN}" if CLERK_DOMAIN else ""

class JWKSCache:
    def __init__(self):
        self.keys = {}
        self.last_fetched = 0
        self.cache_ttl = 3600  # 1 hour

    def get_public_key(self, kid: str, issuer: str):
        now = time.time()
        # Return cached key if valid
        if kid in self.keys and (now - self.last_fetched < self.cache_ttl):
            return self.keys[kid]

        # Fetch fresh JWKS from issuer
        try:
            jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
            logger.info(f"Fetching JWKS from {jwks_url}")
            response = requests.get(jwks_url, timeout=5)
            response.raise_for_status()
            jwks = response.json()

            new_keys = {}
            for jwk in jwks.get("keys", []):
                key_id = jwk.get("kid")
                if key_id:
                    new_keys[key_id] = RSAAlgorithm.from_jwk(jwk)
            
            self.keys = new_keys
            self.last_fetched = now
            return self.keys.get(kid)
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # Gracefully fallback to whatever we have cached
            return self.keys.get(kid)

jwks_cache = JWKSCache()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency that extracts the Bearer token, verifies it against Clerk's JWKS,
    and returns the verified user information.
    """
    token = credentials.credentials

    # 1. Check for Demo Mode fallback
    if settings.DEMO_MODE:
        if token == "demo_token" or not settings.VITE_CLERK_PUBLISHABLE_KEY:
            logger.info("Demo mode bypass: using demo user identity.")
            return {
                "clerk_user_id": "user_demo_12345",
                "email": "demo_user@mkpath.edu",
                "name": "Demo Student",
                "is_demo": True
            }

    try:
        # Decode JWT header without verifying to extract kid and issuer
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        
        kid = unverified_header.get("kid")
        iss = unverified_payload.get("iss")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing key ID (kid)"
            )
        
        if not iss:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing issuer claim (iss)"
            )

        # Security check: verify token belongs to our Clerk instance
        if EXPECTED_ISSUER and iss != EXPECTED_ISSUER:
            # Check custom domain variations or raise error
            if CLERK_DOMAIN not in iss:
                logger.warning(f"Issuer mismatch. Expected {EXPECTED_ISSUER}, got {iss}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer"
                )

        # Get RSA public key from JWKS
        public_key = jwks_cache.get_public_key(kid, iss)
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify token signature: public key not found"
            )

        # Verify JWT signature and claims
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False}  # Clerk session tokens omit audience
        )

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim (sub)"
            )

        # Return verified user dictionary
        return {
            "clerk_user_id": clerk_user_id,
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "is_demo": False
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired"
        )
    except jwt.InvalidTokenError as e:
        # If network is down and we are in Demo Mode, fallback gracefully
        if settings.DEMO_MODE:
            logger.warning(f"Verification failed ({e}). Falling back to demo user profile.")
            return {
                "clerk_user_id": "user_demo_12345",
                "email": "demo_user@mkpath.edu",
                "name": "Demo Student",
                "is_demo": True
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Auth error: {e}")
        if settings.DEMO_MODE:
            return {
                "clerk_user_id": "user_demo_12345",
                "email": "demo_user@mkpath.edu",
                "name": "Demo Student",
                "is_demo": True
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
