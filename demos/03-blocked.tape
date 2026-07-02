# Challenge 3: Blocked
# Logging in through nginx with the cracked admin password fails - a Lua
# DLP filter blocks any request body that looks like a leaked secret, and
# its own incident log leaks a flag.
Output demos/gifs/03-blocked.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type `curl -i -X POST http://localhost:8080/api/login -H "Content-Type: application/json" -d '{"username":"admin","password":"FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}"}'`
Enter
Sleep 2.5s

Type `docker compose logs nginx | grep -i dlp`
Enter
Sleep 3s
