# Challenge 1: Account Not Found
# DB creds sitting in a pod's env vars, then a debug flag left in a config table.
# Run from the repo root with the stack already up: docker compose up -d --build
Output demos/gifs/01-account-not-found.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type "docker compose exec app printenv | grep DATABASE_CONNECTION_STRING"
Enter
Sleep 1.5s

Type `docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp -c "SELECT * FROM system_config;"`
Enter
Sleep 3s
