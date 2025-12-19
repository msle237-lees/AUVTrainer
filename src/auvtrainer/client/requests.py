"""
# DB HTTP Client (FastAPI /db routes)

This module provides a thin, safe wrapper around the FastAPI DB routes:

- GET  /db/status
- GET  /db/tables
- GET  /db/tables/{table}/count
- GET  /db/tables/{table}/schema
- GET  /db/tables/{table}/get_all
- GET  /db/tables/{table}/get/newest
- GET  /db/tables/{table}/get/oldest
- POST /db/tables/{table}/delete/oldest
- POST /db/tables/{table}/delete/newest
- POST /db/tables/{table}/delete/selection
- POST /db/tables/{table}/clear
- POST /db/tables/{table}/append

## Install dependency
pip install requests

## Usage
from db_http_client import DBApiClient

client = DBApiClient("http://127.0.0.1:8000")
print(client.status())
print(client.list_tables())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import requests


JsonDict = Dict[str, Any]
Json = Union[JsonDict, List[Any], str, int, float, bool, None]


class DBApiError(RuntimeError):
    """
    Exception raised when the DB API returns a non-2xx response.
    """

    def __init__(self, status_code: int, message: str, url: str, details: Optional[Any] = None) -> None:
        super().__init__(f"[DBApiError] {status_code} {message} | url={url} | details={details}")
        self.status_code = status_code
        self.message = message
        self.url = url
        self.details = details


@dataclass(frozen=True)
class DBApiClient:
    """
    A small client for the AUVTrainer DB FastAPI endpoints under /db.

    Attributes:
        base_url: Base URL for the FastAPI service, e.g. "http://127.0.0.1:8000"
        timeout_s: Request timeout in seconds.
        session: Optional requests.Session for connection reuse.
    """

    base_url: str
    timeout_s: float = 10.0
    session: Optional[requests.Session] = None

    def _url(self, path: str) -> str:
        """
        Build a full URL from a relative path.

        Args:
            path: Route path beginning with "/"

        Returns:
            Full URL.
        """
        return f"{self.base_url.rstrip('/')}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[Json] = None,
    ) -> JsonDict:
        """
        Perform an HTTP request and return JSON response.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Route path, e.g. "/db/status"
            params: Optional query parameters
            json_body: Optional JSON request body

        Returns:
            Parsed JSON as dict.

        Raises:
            DBApiError: If server returns non-2xx response.
            requests.RequestException: For network errors/timeouts.
            ValueError: If response is not JSON.
        """
        url = self._url(path)
        sess = self.session or requests

        resp = sess.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            timeout=self.timeout_s,
        )

        # Try to parse JSON even on errors (FastAPI returns {"detail": ...})
        try:
            payload = resp.json()
        except ValueError:
            payload = None

        if not (200 <= resp.status_code < 300):
            details = payload.get("detail") if isinstance(payload, dict) else payload
            raise DBApiError(resp.status_code, resp.reason, url, details)

        if not isinstance(payload, dict):
            # Your routes currently always return dict-like objects; enforce that contract.
            raise ValueError(f"Expected JSON object response, got: {type(payload)} from {url}")

        return payload

    # -------------------------
    # /db endpoints
    # -------------------------

    def status(self) -> JsonDict:
        """GET /db/status"""
        return self._request("GET", "/db/status")

    def list_tables(self) -> JsonDict:
        """GET /db/tables"""
        return self._request("GET", "/db/tables")

    def table_count(self, table_name: str) -> JsonDict:
        """GET /db/tables/{table_name}/count"""
        return self._request("GET", f"/db/tables/{table_name}/count")

    def table_schema(self, table_name: str) -> JsonDict:
        """GET /db/tables/{table_name}/schema"""
        return self._request("GET", f"/db/tables/{table_name}/schema")

    def table_get_all(self, table_name: str) -> JsonDict:
        """GET /db/tables/{table_name}/get_all"""
        return self._request("GET", f"/db/tables/{table_name}/get_all")

    def table_get_newest(self, table_name: str) -> JsonDict:
        """GET /db/tables/{table_name}/get/newest"""
        return self._request("GET", f"/db/tables/{table_name}/get/newest")

    def table_get_oldest(self, table_name: str) -> JsonDict:
        """GET /db/tables/{table_name}/get/oldest"""
        return self._request("GET", f"/db/tables/{table_name}/get/oldest")

    def table_delete_oldest(self, table_name: str) -> JsonDict:
        """POST /db/tables/{table_name}/delete/oldest"""
        return self._request("POST", f"/db/tables/{table_name}/delete/oldest")

    def table_delete_newest(self, table_name: str) -> JsonDict:
        """POST /db/tables/{table_name}/delete/newest"""
        return self._request("POST", f"/db/tables/{table_name}/delete/newest")

    def table_delete_selection(self, table_name: str, row_ids: List[int]) -> JsonDict:
        """
        POST /db/tables/{table_name}/delete/selection

        Your FastAPI route uses: Body(..., embed=True) with parameter name row_ids,
        so the JSON must be: {"row_ids": [1,2,3]}
        """
        body = {"row_ids": row_ids}
        return self._request("POST", f"/db/tables/{table_name}/delete/selection", json_body=body)

    def table_clear(self, table_name: str) -> JsonDict:
        """POST /db/tables/{table_name}/clear"""
        return self._request("POST", f"/db/tables/{table_name}/clear")

    def table_append(self, table_name: str, row_data: Dict[str, Any]) -> JsonDict:
        """
        POST /db/tables/{table_name}/append

        Args:
            table_name: Table to insert into
            row_data: Dict mapping column->value, must match actual table columns.
        """
        return self._request("POST", f"/db/tables/{table_name}/append", json_body=row_data)


def quick_smoke_test(base_url: str = "http://127.0.0.1:8000") -> None:
    """
    Simple smoke test you can run manually.

    Example:
        python db_http_client.py
    """
    client = DBApiClient(base_url)

    print("STATUS:", client.status())
    tables = client.list_tables()
    print("TABLES:", tables)

    for t in tables.get("tables", []):
        print(f"COUNT({t}):", client.table_count(t))


if __name__ == "__main__":
    quick_smoke_test()
