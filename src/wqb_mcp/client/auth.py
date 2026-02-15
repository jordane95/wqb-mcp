"""Authentication mixin for BrainApiClient."""

import asyncio
import base64
import sys
from typing import List, Optional

from pydantic import BaseModel
from ..config import load_credentials
from .common import parse_json_or_error


class AuthError(Exception):
    """Base authentication error."""


class AuthInvalidCredentials(AuthError):
    """Raised when login credentials are invalid."""


class AuthChallengeRequired(AuthError):
    """Raised when biometric challenge metadata is incomplete."""


class AuthChallengeTimeout(AuthError):
    """Raised when biometric challenge times out."""


class AuthTransportError(AuthError):
    """Raised when network/transport errors occur during auth."""


class AuthRateLimited(AuthError):
    """Raised when authentication requests are rate limited."""


class AuthResponseParseError(AuthError):
    """Raised when auth response cannot be parsed/validated."""


class AuthUser(BaseModel):
    id: str


class AuthToken(BaseModel):
    expiry: float


class AuthResponse(BaseModel):
    user: AuthUser
    token: AuthToken
    permissions: List[str] = []

    @property
    def status(self) -> str:
        # Compatibility shim for existing call sites expecting auth_result.status
        return "authenticated"

    def __str__(self) -> str:
        return (
            f"{self.status} | user_id={self.user.id} | "
            f"token_expiry={self.token.expiry} | permissions={len(self.permissions)}"
        )


class AuthMixin:
    """Handles authenticate, biometric auth, and ensure_authenticated."""

    async def authenticate(self, email: str, password: str) -> AuthResponse:
        """Authenticate with WorldQuant BRAIN platform with biometric support."""
        self.log("Starting Authentication process...", "INFO")

        # Clear any existing session data
        self.session.cookies.clear()
        self.session.auth = None

        credentials = f"{email}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {'Authorization': f'Basic {encoded_credentials}'}

        try:
            response = self.session.post('https://api.worldquantbrain.com/authentication', headers=headers)
        except Exception as e:
            raise AuthTransportError(f"Authentication request failed: {e}") from e

        if response.status_code == 201:
            self.log("Authentication successful", "SUCCESS")
            jwt_token = self.session.cookies.get('t')
            if jwt_token:
                self.log("JWT token automatically stored by session", "SUCCESS")
            else:
                self.log("No JWT token found in session", "WARNING")
            # Store credentials only after successful authentication.
            self.auth_credentials = {'email': email, 'password': password}
            return AuthResponse.model_validate(parse_json_or_error(response, "/authentication"))

        if response.status_code == 401:
            www_auth = response.headers.get("WWW-Authenticate")
            location = response.headers.get("Location")
            if www_auth == "persona":
                if not location:
                    raise AuthChallengeRequired("Biometric challenge required but Location header is missing.")
                self.log("Biometric authentication required", "INFO")
                from urllib.parse import urljoin
                biometric_url = urljoin(response.url, location)
                return await self._handle_biometric_auth(biometric_url, email, password)
            raise AuthInvalidCredentials("Incorrect email or password.")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                raise AuthRateLimited(f"Authentication rate limited (429). Retry-After: {retry_after}s.")
            raise AuthRateLimited("Authentication rate limited (429).")

        raise AuthError(f"Authentication failed with status code: {response.status_code}")

    async def _handle_biometric_auth(self, biometric_url: str, email: str, password: str) -> AuthResponse:
        """Handle biometric authentication using browser automation."""
        self.log("Starting biometric authentication...", "INFO")

        browser = None
        # Import playwright for browser automation
        from playwright.async_api import async_playwright
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()

                self.log("Opening browser for biometric authentication...", "INFO")
                await page.goto(biometric_url)
                self.log("Browser page loaded successfully", "SUCCESS")

                print("\n" + "="*60, file=sys.stderr)
                print("BIOMETRIC AUTHENTICATION REQUIRED", file=sys.stderr)
                print("="*60, file=sys.stderr)
                print("Browser window is open with biometric authentication page", file=sys.stderr)
                print("Complete the biometric authentication in the browser", file=sys.stderr)
                print("The system will automatically check when you're done...", file=sys.stderr)
                print("="*60, file=sys.stderr)

                max_attempts = 60
                attempt = 0

                while attempt < max_attempts:
                    await asyncio.sleep(5)
                    attempt += 1

                    try:
                        check_response = self.session.post(biometric_url)
                    except Exception as e:
                        raise AuthTransportError(f"Biometric poll request failed: {e}") from e

                    self.log(f"Checking authentication status (attempt {attempt}/{max_attempts}): {check_response.status_code}", "INFO")
                    if check_response.status_code == 201:
                        self.log("Biometric authentication successful!", "SUCCESS")
                        jwt_token = self.session.cookies.get('t')
                        if jwt_token:
                            self.log("JWT token received", "SUCCESS")
                        # Store credentials only after successful authentication.
                        self.auth_credentials = {'email': email, 'password': password}
                        return AuthResponse.model_validate(parse_json_or_error(check_response, "/authentication"))

                raise AuthChallengeTimeout("Biometric authentication timed out.")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    async def is_authenticated(self) -> bool:
        """Check if currently authenticated using JWT token."""
        try:
            # Check if we have a JWT token in cookies
            jwt_token = self.session.cookies.get('t')
            if not jwt_token:
                self.log("No JWT token found", "INFO")
                return False

            # Test authentication with a simple API call
            response = self.session.get(f"{self.base_url}/authentication")
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                self.log("JWT token expired or invalid (401)", "INFO")
                return False
            else:
                self.log(f"Unexpected status code during auth check: {response.status_code}", "WARNING")
                return False
        except Exception as e:
            self.log(f"Error checking authentication: {str(e)}", "ERROR")
            return False

    async def ensure_authenticated(self):
        """Ensure authentication is valid, re-authenticate if needed."""
        if not await self.is_authenticated():
            if not self.auth_credentials:
                self.log("No credentials in memory, loading from config...", "INFO")
                email, password = load_credentials()
                if not email or not password:
                    raise Exception("Authentication credentials not found. Please authenticate first.")
                self.auth_credentials = {'email': email, 'password': password}

            self.log("Re-authenticating...", "INFO")
            await self.authenticate(self.auth_credentials['email'], self.auth_credentials['password'])

    async def get_authentication_status(self) -> Optional[dict]:
        """Get current authentication status and user info."""
        try:
            response = self.session.get(f"{self.base_url}/users/self")
            response.raise_for_status()
            return parse_json_or_error(response, "/users/self")
        except Exception as e:
            self.log(f"Failed to get auth status: {str(e)}", "ERROR")
            return None
