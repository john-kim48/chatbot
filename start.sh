#!/bin/bash
exec gunicorn --bind=0.0.0.0:$PORT app:app \
  --workers 4 \
  --timeout 120 \
  --capture-output \
  --enable-stdio-inheritance \
  --access-logfile - \
  --error-logfile - \
  --log-level debug