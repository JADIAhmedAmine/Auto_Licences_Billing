from __future__ import annotations

import xmlrpc.client
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


@dataclass
class OdooRPC:
    url: str
    db: str
    user: str
    password: str

    def __post_init__(self) -> None:
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed. Check ODOO_URL/DB/USER/PASSWORD.")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs or {})

    def search_read(self, model: str, domain: list, fields: List[str], limit: int = 20000) -> List[Dict[str, Any]]:
        return self.execute_kw(model, "search_read", [domain], {"fields": fields, "limit": limit})

    def write(self, model: str, record_id: int, values: Dict[str, Any]) -> bool:
        return bool(self.execute_kw(model, "write", [[record_id], values]))

    def batch_write(self, model: str, updates: Sequence[Tuple[int, Dict[str, Any]]], chunk_size: int = 200) -> None:
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i : i + chunk_size]
            for rid, vals in chunk:
                self.write(model, rid, vals)
