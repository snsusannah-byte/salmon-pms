#!/bin/bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
