#!/bin/sh
curl -v -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"dthat53@gmail.com","password":"admin1243"}' \
  http://localhost:8000/api/auth/login > /tmp/auth_response.txt 2>&1

echo "--- RESPONSE START ---"
cat /tmp/auth_response.txt
echo "--- RESPONSE END ---"
