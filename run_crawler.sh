#!/bin/bash
# Start SSH tunnel on port 5434
expect << 'INNER_EOF' &
spawn ssh -N -L 5434:127.0.0.1:5432 -o StrictHostKeyChecking=no globaladmin@40.81.234.20
expect "password:"
send "8765@@@###!!!Global\r"
expect eof
INNER_EOF

TUNNEL_PID=$!
sleep 3 # Wait for tunnel to establish

export DATABASE_URL="postgresql://postgres:8765%40%40%40###!!!Global@127.0.0.1:5434/postgres"
export DB_CONFIG=""
python3 scripts/live_ingestion.py

kill $TUNNEL_PID
