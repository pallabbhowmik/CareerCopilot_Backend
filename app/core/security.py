import jwt
from fastapi import HTTPException, status
from app.core.config import settings
import httpx


def _supabase_anon_key() -> str | None:
    # Support either SUPABASE_ANON_KEY or the older SUPABASE_KEY.
    return settings.SUPABASE_ANON_KEY or settings.SUPABASE_KEY


async def _validate_token_with_supabase(token: str):
    """Validate a JWT by asking Supabase Auth.

    This is a safe fallback when the backend doesn't have the correct JWT secret.
    """
    if not settings.SUPABASE_URL or not _supabase_anon_key():
        return None

    url = settings.SUPABASE_URL.rstrip("/") + "/auth/v1/user"
    headers = {
        "apikey": _supabase_anon_key(),
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        return None

    data = resp.json() if resp.content else None
    if not isinstance(data, dict) or not data.get("id"):
        return None

    # Return a minimal payload compatible with get_current_user()
    return {
        "sub": data.get("id"),
        "email": data.get("email"),
        "role": data.get("role"),
        "aud": data.get("aud"),
    }

async def verify_supabase_token(token: str):
    """
    Verifies a Supabase JWT token.
    Returns the decoded payload if valid.
    """
    try:
        if settings.SUPABASE_JWT_SECRET:
            # Supabase typically uses HS256 with the project's JWT secret.
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload

        # No secret configured; fall back to Supabase Auth validation.
        validated = await _validate_token_with_supabase(token)
        if validated:
            return validated

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT Secret not configured (set SUPABASE_JWT_SECRET or SUPABASE_URL+SUPABASE_ANON_KEY)",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        # If signature verification fails, we can still validate via Supabase Auth as a fallback.
        try:
            validated = await _validate_token_with_supabase(token)
            if validated:
                return validated
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
