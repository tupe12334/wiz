# Demos

One [VHS](https://github.com/charmbracelet/vhs) `.tape` file per challenge,
recording the exact commands from [`WRITEUP.md`](../WRITEUP.md) against a
real, running copy of this stack. The rendered GIFs are in `gifs/`.

| Tape | Shows |
|---|---|
| `01-account-not-found.tape` | DB creds in a pod's env vars → `debug_flag` in `system_config` |
| `02-admin-access.tape` | `python3` locked to mode 0000, restored via `busybox chmod`, admin password decrypted |
| `03-blocked.tape` | Login blocked by the DLP filter; the flag leaking out of its own incident log |
| `04-dlp-config.tape` | Reading the DLP filter's own config file |
| `05-provision-account.tape` | Bypassing nginx/DLP by calling the app Service directly; captcha bypass; credentials; account provisioning |
| `06-the-checklist.tape` | The three-bug crash chain: incomplete modules → `NULL` value → wrong XOR key |
| `07-complete-onboarding.tape` | The timeout, then the index that fixes it |

## Regenerating

Needs [`vhs`](https://github.com/charmbracelet/vhs) installed (`brew install vhs`
on macOS - it pulls in `ttyd` and `ffmpeg`), and the stack running:

```bash
docker compose up -d --build
# wait for postgres to finish seeding: docker compose logs postgres | tail -5

vhs demos/01-account-not-found.tape
vhs demos/02-admin-access.tape
vhs demos/03-blocked.tape
vhs demos/04-dlp-config.tape
vhs demos/05-provision-account.tape
vhs demos/06-the-checklist.tape
vhs demos/07-complete-onboarding.tape
```

Run them in order against a **freshly reset** stack
(`docker compose down -v && docker compose up -d --build`) - challenges 5-7
create real accounts and DB state (an employee account, a fixed `NULL`
row, a new index) that the later tapes build on, same as actually
playing through it. Re-running an individual tape against a stack that's
already past that point still works, it just skips some of the "before"
states (e.g. challenge 7's tape won't show a timeout if the index
already exists).

## `scripts/`

Small helper scripts the tapes call instead of typing long inline
`python3 -c "..."` blocks on camera. They're thin wrappers around the
same HTTP calls documented in `WRITEUP.md` - nothing here is required to
solve the challenge, they just keep the recordings readable. Mounted
into the `shell` container at `/scripts` (see `docker-compose.yml`).
