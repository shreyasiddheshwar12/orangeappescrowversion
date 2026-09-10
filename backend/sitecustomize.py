"""Python startup hook for the Orange backend.

Python imports sitecustomize automatically when it is available on sys.path.
This keeps the documented `uvicorn server:app --reload` command unchanged.
"""
import e2e_patch  # noqa: F401
