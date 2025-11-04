#!/bin/bash

# Set Neon database environment variables
export NEON_DB_HOST="YOUR_NEON_DB_HOST"
export NEON_DB_NAME="YOUR_NEON_DB_NAME"
export NEON_DB_USER="YOUR_NEON_DB_USER"
export NEON_PASSWORDLESS_TOKEN="YOUR_NEON_PASSWORDLESS_TOKEN"
export NEON_SSLMODE="require"

# Verify environment variables are set
echo "Environment variables:"
echo "NEON_DB_HOST: $NEON_DB_HOST"
echo "NEON_DB_NAME: $NEON_DB_NAME"
echo "NEON_DB_USER: $NEON_DB_USER"
echo "NEON_PASSWORDLESS_TOKEN: [REDACTED]"
echo "NEON_SSLMODE: $NEON_SSLMODE"

# Run Streamlit
streamlit run chat_llama.py


