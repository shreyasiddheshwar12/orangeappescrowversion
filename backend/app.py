"""Production application entrypoint for Orange.

Importing this module builds the legacy FastAPI server and then applies the
runtime hardening layer explicitly. This is more reliable than depending on
Python's optional sitecustomize startup hook.
"""
import server
import e2e_patch

e2e_patch._patch_server(server)

app = server.app
