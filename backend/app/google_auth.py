"""Verify a "Sign in with Google" ID token (a JWT signed by Google).

The browser gets the token from Google's own button; we check Google's signature (keys from its
public JWKS endpoint, cached by PyJWKClient), that it was issued for our client ID, that it hasn't
expired, and that Google has verified the email. No client secret is involved.
"""
import jwt

from app.config import GOOGLE_CLIENT_ID

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_jwks = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True)


class GoogleTokenError(Exception):
    pass


def verify_google_token(credential: str) -> dict:
    """{'sub', 'email', 'name'} from a valid token, else GoogleTokenError."""
    try:
        key = _jwks.get_signing_key_from_jwt(credential)
        claims = jwt.decode(credential, key.key, algorithms=["RS256"], audience=GOOGLE_CLIENT_ID,
                            issuer=GOOGLE_ISSUERS, options={"require": ["exp", "iat", "sub", "email"]})
    except jwt.PyJWTError as e:
        raise GoogleTokenError(f"Google sign-in couldn't be verified: {e}") from e
    if claims.get("email_verified") is not True:
        raise GoogleTokenError("This Google account's email isn't verified")
    return {"sub": str(claims["sub"]), "email": claims["email"].strip().lower(),
            "name": (claims.get("given_name") or claims.get("name") or "").strip()[:80] or None}
