"""HTTP client for backend API calls."""

from typing import Any, Dict, Optional

import requests

from tools.mcp_server.errors import JsonRpcError


class BackendClient:
    """HTTP client for backend API calls with timeout and retry logic."""

    def __init__(self, base_url: str, bearer_token: Optional[str] = None):
        self.base_url = base_url
        self.bearer_token = bearer_token
        self.timeout = 5

    def health(self, trace_id: str) -> Dict[str, Any]:
        """Check backend system health."""
        url = f"{self.base_url}/api/v1/health"
        return self._get(url, trace_id)

    def create_session(self, module_id: str, trace_id: str, module_version: Optional[str] = None) -> Dict[str, Any]:
        """Create a new game session."""
        url = f"{self.base_url}/api/v1/sessions"
        payload = {"module_id": module_id}
        if module_version:
            payload["module_version"] = module_version
        return self._post(url, trace_id, json=payload)

    def _get(self, url: str, trace_id: str) -> Dict[str, Any]:
        """Make GET request with timeout and retry logic."""
        headers = {"X-Trace-ID": trace_id}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code >= 400:
                raise JsonRpcError(
                    code=-32603,
                    message=f"Backend HTTP {response.status_code}",
                    data={"url": url, "status": response.status_code},
                )
            return response.json()
        except (requests.RequestException, TimeoutError, ConnectionError, JsonRpcError) as e:
            # For JsonRpcError, re-raise it
            if isinstance(e, JsonRpcError):
                raise
            # Retry once on network error
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                if response.status_code >= 400:
                    raise JsonRpcError(
                        code=-32603,
                        message=f"Backend HTTP {response.status_code}",
                        data={"url": url, "status": response.status_code},
                    )
                return response.json()
            except (requests.RequestException, TimeoutError, ConnectionError):
                raise JsonRpcError(
                    code=-32603,
                    message="Backend unavailable",
                    data={"url": url},
                )

    def _post(self, url: str, trace_id: str, **kwargs) -> Dict[str, Any]:
        """Make POST request with timeout and retry logic."""
        headers = kwargs.pop("headers", {})
        headers["X-Trace-ID"] = trace_id
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        kwargs["headers"] = headers
        kwargs["timeout"] = self.timeout

        try:
            response = requests.post(url, **kwargs)
            if response.status_code >= 400:
                raise JsonRpcError(
                    code=-32603,
                    message=f"Backend HTTP {response.status_code}",
                    data={"url": url, "status": response.status_code},
                )
            return response.json()
        except (requests.RequestException, TimeoutError, ConnectionError, JsonRpcError) as e:
            # For JsonRpcError, re-raise it
            if isinstance(e, JsonRpcError):
                raise
            # Retry once on network error
            try:
                response = requests.post(url, **kwargs)
                if response.status_code >= 400:
                    raise JsonRpcError(
                        code=-32603,
                        message=f"Backend HTTP {response.status_code}",
                        data={"url": url, "status": response.status_code},
                    )
                return response.json()
            except (requests.RequestException, TimeoutError, ConnectionError):
                raise JsonRpcError(
                    code=-32603,
                    message="Backend unavailable",
                    data={"url": url},
                )
