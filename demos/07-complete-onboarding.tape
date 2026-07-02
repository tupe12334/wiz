# Challenge 7: Complete Onboarding
# A correlated EXISTS subquery over audit_logs with no supporting index
# blows past a 2-second statement_timeout, every time - until you add
# the index appuser is allowed to create on its own table.
Output demos/gifs/07-complete-onboarding.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type `SID=$(docker compose exec shell python3 /scripts/login.py admin 'FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}' | tr -d '\r')`
Enter
Sleep 500ms

Type `docker compose exec shell python3 /scripts/get_audit_stats.py "$SID"`
Enter
Sleep 3s

Type `docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp -c "CREATE INDEX idx_audit_logs_burst ON audit_logs(user_id, resource_type, timestamp DESC);"`
Enter
Sleep 1.5s

Type `docker compose exec shell python3 /scripts/get_audit_stats.py "$SID"`
Enter
Sleep 3s
