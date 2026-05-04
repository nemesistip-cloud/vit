#!/bin/bash
set -e

cd frontend
npm install --no-package-lock 2>/dev/null || npm install
