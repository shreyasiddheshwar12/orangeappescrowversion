"""Python startup hook for the Orange backend.

Python imports sitecustomize automatically when it is available on sys.path.
This keeps the documented `uvicorn server:app --reload` command unchanged.
"""
try:
    import e2e_patch  # noqa: F401
except Exception:
    # Never prevent Python/uvicorn from starting because of the optional
    # hardening layer. The CI smoke tests will expose any real import issue.
    pass
