#!/bin/bash
#
# Seed Firebase Emulator with test data
# Creates a test user: test@example.com / password123
#
# Usage: ./scripts/seed-emulator.sh
#
# This script should be run after emulators are started.
# It uses the Auth emulator REST API to create users.
#

set -e

AUTH_EMULATOR_HOST="${AUTH_EMULATOR_HOST:-localhost:9099}"
PROJECT_ID="${FIREBASE_PROJECT_ID:-legalease-420}"

echo "Seeding Firebase Auth Emulator at ${AUTH_EMULATOR_HOST}..."

# Create test user via Auth emulator REST API
# The emulator's signUp endpoint creates users with passwords
curl -s -X POST "http://${AUTH_EMULATOR_HOST}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "displayName": "Test User",
    "returnSecureToken": true
  }' | jq -r '.localId // "User already exists or error occurred"'

echo ""
echo "✅ Test user created:"
echo "   Email: test@example.com"
echo "   Password: password123"
echo ""
echo "View users at: http://localhost:4000/auth"
