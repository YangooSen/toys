cat >> ~/.ssh/config <<'EOF'
Host p
 HostName 100.107.160.60
 User yangsen
 RequestTTY force
 RemoteCommand /home/yangsen/.local/bin/pm
 ServerAliveInterval 30
EOF
