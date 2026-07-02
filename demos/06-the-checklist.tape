# Challenge 6: The Checklist
# Three bugs stacked: a modules-completeness guard nothing ever
# satisfies, a NULL value that blows up `total += value`, and a wrong
# byte in a two-byte XOR key hiding the flag in plain sight.
Output demos/gifs/06-the-checklist.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 20
Set WindowBar Colorful
Set TypingSpeed 35ms

Type `SID=$(docker compose exec shell python3 /scripts/login.py admin 'FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}' | tr -d '\r')`
Enter
Sleep 500ms
Type `read USID UID <<< "$(docker compose exec shell python3 /scripts/provision_and_login.py "$SID" newhire6 "New Hire Six" newhire6@wiznt.io | tr -d '\r')"`
Enter
Sleep 1s
Type `echo "new hire session: $USID (user_id $UID)"`
Enter
Sleep 1.5s

Type `docker compose exec shell python3 /scripts/get_report.py "$USID"`
Enter
Sleep 3s

Type `docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp -c "UPDATE onboarding_modules SET completed=true WHERE user_id=$UID;"`
Enter
Sleep 1.5s

Type `docker compose exec shell python3 /scripts/get_report.py "$USID"`
Enter
Sleep 3s

Type `docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp -c "UPDATE report_data SET value=0 WHERE sequence=13;"`
Enter
Sleep 1.5s

Type `docker compose exec shell python3 /scripts/get_report.py "$USID"`
Enter
Sleep 3s

Type `docker compose exec shell sh -c "PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp -t -A -F',' -c 'SELECT sequence, encoded_char FROM report_data ORDER BY sequence;' | python3 /scripts/decode_xor.py"`
Enter
Sleep 2.5s
