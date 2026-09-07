"""Convenience launcher:  python run.py  (equivalent to uvicorn app.main:app).

Port defaults to 8000 but can be overridden, e.g.  PORT=8001 python run.py
"""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
