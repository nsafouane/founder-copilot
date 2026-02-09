import os
import requests
import json
import time
import logging
from typing import Dict, Any, Optional
from founder_copilot.copilot.providers.base import CRMProvider

logger = logging.getLogger(__name__)


class SalesForceProvider(CRMProvider):
    """
    SalesForce CRM Provider for OAuth2 integration.
    Handles token management (access and refresh tokens) and CRUD operations.
    """

    def __init__(self):
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._redirect_uri: Optional[str] = None
        self._instance_url: Optional[str] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0
        self._session: requests.Session = requests.Session()

    @property
    def name(self) -> str:
        return "salesforce"

    def configure(self, config: Dict[str, Any]) -> None:
        self._client_id = config.get("client_id") or os.getenv("SALESFORCE_CLIENT_ID")
        self._client_secret = config.get("client_secret") or os.getenv("SALESFORCE_CLIENT_SECRET")
        self._redirect_uri = config.get("redirect_uri") or os.getenv("SALESFORCE_REDIRECT_URI", "http://localhost:8000/salesforce-oauth-callback")
        
        # Load existing tokens if available
        self._access_token = config.get("access_token")
        self._refresh_token = config.get("refresh_token")
        self._instance_url = config.get("instance_url")
        self._expires_at = config.get("expires_at", 0)

        if not self._client_id or not self._client_secret:
            raise ValueError("SalesForce client_id and client_secret must be provided.")

        logger.info("SalesForceProvider configured.")

    def _get_auth_header(self) -> Dict[str, str]:
        if self._access_token and self._expires_at > time.time():
            return {"Authorization": f"Bearer {self._access_token}"}
        
        if self._refresh_token:
            logger.info("Access token expired, attempting to refresh...")
            self._refresh_access_token()
            if self._access_token and self._expires_at > time.time():
                return {"Authorization": f"Bearer {self._access_token}"}
        
        raise RuntimeError("SalesForce not authenticated. Please perform OAuth handshake.")

    def get_authorization_url(self) -> str:
        """Returns the URL to redirect the user for OAuth authorization."""
        if not self._client_id or not self._redirect_uri:
            raise RuntimeError("SalesForce client_id and redirect_uri must be configured.")
        
        # SalesForce uses the authorization code flow
        return (
            "https://login.salesforce.com/services/oauth2/authorize?"
            f"client_id={self._client_id}&"
            "response_type=code&"
            f"redirect_uri={self._redirect_uri}"
        )

    def exchange_code_for_tokens(self, code: str) -> None:
        """Exchanges an authorization code for access and refresh tokens."""
        if not self._client_id or not self._client_secret or not self._redirect_uri:
            raise RuntimeError("SalesForce client_id, client_secret, and redirect_uri must be configured.")
        
        token_url = "https://login.salesforce.com/services/oauth2/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "code": code
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_info = response.json()
            
            self._access_token = token_info["access_token"]
            self._refresh_token = token_info.get("refresh_token", self._refresh_token) # May not always return refresh token
            self._instance_url = token_info["instance_url"]
            self._expires_at = time.time() + int(token_info.get("expires_in", 3600))
            
            logger.info(f"SalesForce tokens exchanged successfully. Instance URL: {self._instance_url}")
            # TODO: Persist these tokens securely in config_manager
        except requests.RequestException as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            if response:
                logger.error(f"SalesForce API error: {response.text}")
            raise

    def _refresh_access_token(self) -> None:
        """Refreshes the access token using the refresh token."""
        if not self._client_id or not self._client_secret or not self._refresh_token:
            raise RuntimeError("SalesForce client_id, client_secret, or refresh_token missing for refresh.")
        
        token_url = "https://login.salesforce.com/services/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_info = response.json()
            
            self._access_token = token_info["access_token"]
            self._instance_url = token_info.get("instance_url", self._instance_url)
            self._expires_at = time.time() + int(token_info.get("expires_in", 3600))
            
            logger.info("SalesForce access token refreshed successfully.")
            # TODO: Persist these updated tokens securely in config_manager
        except requests.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            if response:
                logger.error(f"SalesForce API error: {response.text}")
            raise

    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new contact in SalesForce."""
        if not self._instance_url:
            raise RuntimeError("SalesForce instance URL not configured. Please authenticate first.")
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/json"
        
        url = f"{self._instance_url}/services/data/v59.0/sobjects/Contact/"
        
        try:
            response = self._session.post(url, headers=headers, json=contact_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to create contact: {e}")
            if response:
                logger.error(f"SalesForce API error: {response.text}")
            raise

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing contact in SalesForce."""
        if not self._instance_url:
            raise RuntimeError("SalesForce instance URL not configured. Please authenticate first.")
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/json"
        
        url = f"{self._instance_url}/services/data/v59.0/sobjects/Contact/{contact_id}"
        
        try:
            response = self._session.patch(url, headers=headers, json=contact_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to update contact {contact_id}: {e}")
            if response:
                logger.error(f"SalesForce API error: {response.text}")
            raise

    def create_deal(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new deal/opportunity in SalesForce."""
        if not self._instance_url:
            raise RuntimeError("SalesForce instance URL not configured. Please authenticate first.")
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/json"
        
        url = f"{self._instance_url}/services/data/v59.0/sobjects/Opportunity/"
        
        try:
            response = self._session.post(url, headers=headers, json=deal_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to create deal/opportunity: {e}")
            if response:
                logger.error(f"SalesForce API error: {response.text}")
            raise

    def health_check(self) -> bool:
        """Verifies API connectivity by querying identity endpoint."""
        try:
            if not self._instance_url or not self._access_token:
                return False
            headers = {"Authorization": f"Bearer {self._access_token}"}
            url = f"{self._instance_url}/services/data/v59.0/limits"
            response = self._session.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"SalesForce health check failed: {e}")
            return False
