#!/bin/bash
# Script to start both Python and Node.js containers

# Build and run Python app container (port 2222)
docker run -d --name keepstone-python-app -p 2222:2222 \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  bash -c "pip install -r keepstone/requirements.txt && python keepstone/app.py --port 2222"

# Build and run Node.js app container (port 3333)
docker run -d --name keepstone-node-app -p 3333:3333 \
  -v $(pwd):/app \
  -w /app \
  node:20 \
  bash -c "npm install && npm start -- --port 3333"

echo "Both containers started:"
echo "- Python app: http://localhost:2222"
echo "- Node.js app: http://localhost:3333"
