"""
# DB HTTP Client (FastAPI /db routes)

Thin wrapper around your FastAPI DB routes:

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

# Typed helpers:
row = client.create_input(x=1, y=2, z=3, yaw=4, arm=True)
print("Inserted input rowid:", row)

newest_input = client.get_newest_input()
print("Newest input:", newest_input)

all_outputs = client.get_all_outputs()
print("Outputs:", all_outputs)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, cast

import requests

JsonDict = Dict[str, Any]
Json = Union[JsonDict, List[Any], str, int, float, bool, None]


class DBApiError(RuntimeError):
    """
    Exception raised when the DB API returns a non-2xx response.
    """

    def __init__(
        self, status_code: int, message: str, url: str, details: Optional[Any] = None
    ) -> None:
        super().__init__(f"[DBApiError] {status_code} {message} | url={url} | details={details}")
        self.status_code = status_code
        self.message = message
        self.url = url
        self.details = details


# -----------------------------------------------------------------------------
# Typed "Read" models (client-side)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class InputRead:
    """
    Client-side representation of a row in `inputs`.

    Notes:
        - SQLite often stores booleans as 0/1; this class normalizes arm -> bool.
        - Your API returns rows as dicts via SELECT * FROM inputs.
    """

    id: int
    x: int
    y: int
    z: int
    yaw: int
    arm: bool

    @staticmethod
    def from_row(row: JsonDict) -> "InputRead":
        arm_val = row.get("arm")
        if isinstance(arm_val, bool):
            arm_bool = arm_val
        else:
            # accept 0/1, "0"/"1", etc.
            arm_bool = bool(int(arm_val)) if arm_val is not None else False

        return InputRead(
            id=int(row["id"]),
            x=int(row["x"]),
            y=int(row["y"]),
            z=int(row["z"]),
            yaw=int(row["yaw"]),
            arm=arm_bool,
        )


@dataclass(frozen=True)
class OutputRead:
    """
    Client-side representation of a row in `outputs`.
    """

    id: int
    inputs_id: int
    m1: int
    m2: int
    m3: int
    m4: int
    m5: int
    m6: int
    m7: int
    m8: int

    @staticmethod
    def from_row(row: JsonDict) -> "OutputRead":
        return OutputRead(
            id=int(row["id"]),
            inputs_id=int(row["inputs_id"]),
            m1=int(row["m1"]),
            m2=int(row["m2"]),
            m3=int(row["m3"]),
            m4=int(row["m4"]),
            m5=int(row["m5"]),
            m6=int(row["m6"]),
            m7=int(row["m7"]),
            m8=int(row["m8"]),
        )


# -----------------------------------------------------------------------------
# Client
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DBApiClient:
    """
    A small client for the DB FastAPI endpoints under /db.

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
            ValueError: If response is not JSON or not a JSON object.
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

        # Try to parse JSON even on errors (FastAPI typically returns {"detail": ...})
        try:
            payload = resp.json()
        except ValueError:
            payload = None

        if not (200 <= resp.status_code < 300):
            details = payload.get("detail") if isinstance(payload, dict) else payload
            raise DBApiError(resp.status_code, resp.reason, url, details)

        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object response, got: {type(payload)} from {url}")

        return cast(JsonDict, payload)

    # -------------------------
    # Raw /db endpoints
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

        Your FastAPI route uses Body(..., embed=True) with parameter name row_ids,
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
            table_name: Table to insert into.
            row_data: Dict mapping column->value, must match actual table columns.

        Notes:
            If your table uses an INTEGER PRIMARY KEY AUTOINCREMENT `id`,
            you should NOT include "id" in row_data (SQLite will generate it).
        """
        return self._request("POST", f"/db/tables/{table_name}/append", json_body=row_data)

    # -------------------------
    # Typed helpers (inputs/outputs)
    # -------------------------

    def get_all_inputs(self) -> List[InputRead]:
        """
        Fetch all rows from `inputs` and parse into InputRead objects.
        """
        payload = self.table_get_all("inputs")
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("Expected payload['rows'] to be a list for inputs")
        return [InputRead.from_row(cast(JsonDict, r)) for r in rows]

    def get_newest_input(self) -> Optional[InputRead]:
        """
        Fetch newest row from `inputs` (by rowid) and parse into InputRead.
        """
        payload = self.table_get_newest("inputs")
        row = payload.get("newest_row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise ValueError("Expected payload['newest_row'] to be an object for inputs")
        return InputRead.from_row(cast(JsonDict, row))

    def get_oldest_input(self) -> Optional[InputRead]:
        """
        Fetch oldest row from `inputs` (by rowid) and parse into InputRead.
        """
        payload = self.table_get_oldest("inputs")
        row = payload.get("oldest_row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise ValueError("Expected payload['oldest_row'] to be an object for inputs")
        return InputRead.from_row(cast(JsonDict, row))

    def create_input(self, *, x: int, y: int, z: int, yaw: int, arm: bool) -> int:
        """
        Insert a new row into `inputs`.

        Returns:
            The inserted SQLite rowid returned by the API.

        Notes:
            This assumes your `inputs.id` is auto-generated by SQLite (INTEGER PRIMARY KEY).
            So we do NOT send 'id' in the payload.
        """
        body = {
            "x": int(x),
            "y": int(y),
            "z": int(z),
            "yaw": int(yaw),
            "arm": 1 if arm else 0,
        }
        resp = self.table_append("inputs", body)
        return int(resp["rowid"])

    def get_all_outputs(self) -> List[OutputRead]:
        """
        Fetch all rows from `outputs` and parse into OutputRead objects.
        """
        payload = self.table_get_all("outputs")
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("Expected payload['rows'] to be a list for outputs")
        return [OutputRead.from_row(cast(JsonDict, r)) for r in rows]

    def get_newest_output(self) -> Optional[OutputRead]:
        """
        Fetch newest row from `outputs` (by rowid) and parse into OutputRead.
        """
        payload = self.table_get_newest("outputs")
        row = payload.get("newest_row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise ValueError("Expected payload['newest_row'] to be an object for outputs")
        return OutputRead.from_row(cast(JsonDict, row))

    def create_output(
        self,
        *,
        inputs_id: int,
        m1: int,
        m2: int,
        m3: int,
        m4: int,
        m5: int,
        m6: int,
        m7: int,
        m8: int,
    ) -> int:
        """
        Insert a new row into `outputs`.

        Returns:
            The inserted SQLite rowid returned by the API.

        Notes:
            This assumes your `outputs.id` is auto-generated by SQLite (INTEGER PRIMARY KEY).
            So we do NOT send 'id' in the payload.
        """
        body = {
            "inputs_id": int(inputs_id),
            "m1": int(m1),
            "m2": int(m2),
            "m3": int(m3),
            "m4": int(m4),
            "m5": int(m5),
            "m6": int(m6),
            "m7": int(m7),
            "m8": int(m8),
        }
        resp = self.table_append("outputs", body)
        return int(resp["rowid"])


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

    # Try typed reads (safe even if empty tables)
    print("NEWEST INPUT:", client.get_newest_input())
    print("NEWEST OUTPUT:", client.get_newest_output())


if __name__ == "__main__":
    quick_smoke_test()
