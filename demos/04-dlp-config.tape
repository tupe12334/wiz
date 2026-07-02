# Challenge 4: The One Thing That Works
# Read the DLP filter's own config file.
Output demos/gifs/04-dlp-config.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type "docker compose exec nginx cat /etc/nginx/dlp-rules/patterns.json"
Enter
Sleep 3s
