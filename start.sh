#!/bin/bash
exec gunicorn --bind=0.0.0.0:$PORT app:app \
  --workers 4 \
  --capture-output \
  --enable-stdio-inheritance \
  --access-logfile - \
  --error-logfile - \
  --log-level debug