# Wizn't Day One - a recreated CTF

A self-hostable recreation of Wiz's ["Day One"](https://day-one.wiz.io) engineering
CTF: an internal onboarding app called **OnBored**, deliberately left in a
broken state by an engineer named Derek who left mid-restart. Seven flags,
each teaching a distinct cloud/appsec lesson - default creds, DLP bypass,
in-cluster network trust, IDOR-adjacent business logic, and a classic
missing-index performance bug that's gating a secret.

This repo is a **from-scratch recreation**, built by reverse-engineering the
behavior of the real hosted challenge, not a copy of Wiz's source. See
[WRITEUP.md](WRITEUP.md) for the full walkthrough of how to solve every
challenge and why each bug exists.

## Architecture

```
                    ┌──────────┐
   browser ────────▶│  nginx   │  (DLP filter on request bodies)
                    └────┬─────┘
                         │
                    ┌────▼─────┐        ┌──────────────────┐
                    │   app    │───────▶│ credential-store  │
                    │ (OnBored)│        │ (bearer-token API)│
                    └────┬─────┘        └───────────────────┘
                         │
                    ┌────▼─────┐
                    │ postgres │
                    └──────────┘

   ┌───────┐
   │ shell │  <- "your" pod / recon box, network access only
   └───────┘
```

- **app** - Flask "OnBored" onboarding portal. Deliberately hardened in a
  way that backfires (see challenge 2), gates a real bug (challenge 6),
  and calls out to credential-store using a mounted token (challenge 5).
- **credential-store** - a tiny internal service that will hash a password
  or hand back provisioned credentials, but only for callers presenting a
  valid service token - not for anyone hitting it through the front door.
- **nginx** - reverse proxy in front of `app`, running a Lua DLP filter
  that blocks any request body containing something that looks like a
  leaked secret.
- **postgres** - seeded with a debug flag, a Fernet-encrypted admin
  password, XOR-encoded report data, and a 150k-row `audit_logs` table
  backing a function with a missing index.
- **shell** - your foothold. No credentials, just network access to
  everything else - same as the original challenge's `kubectl exec`-able
  pod.

## Quick start (Docker Compose)

```bash
docker compose up -d --build
```

Wait for postgres to finish seeding (a few seconds - `docker compose logs
postgres` should end with `database system is ready to accept
connections`), then:

- The app is at **http://localhost:8080** (through nginx, DLP filter active).
- Your recon box: `docker compose exec shell sh`
- Direct DB access: `docker compose exec shell env PGPASSWORD=dbpassword123 psql -h postgres -U appuser -d ctfapp`

There is no `kubectl` in Compose mode - anywhere the write-up says
`kubectl exec app-... -- ...`, use `docker compose exec app ...` instead.

## Quick start (Kubernetes)

Needs a local cluster (kind, minikube, k3d, ...) and the images built
locally with matching tags:

```bash
docker build -t wiz-app:local ./app
docker build -t wiz-credential-store:local ./credential-store
docker build -t wiz-shell:local ./shell
docker build -t wiz-db:local ./db

# kind: `kind load docker-image wiz-app:local wiz-credential-store:local wiz-shell:local wiz-db:local`
# minikube: `minikube image load wiz-app:local ...` (or point your shell at minikube's docker daemon)

kubectl apply -f k8s/
kubectl -n challenge get pods -w
```

Then:

```bash
kubectl -n challenge exec -it shell -- sh
```

`shell` runs as the `challenge-user` ServiceAccount with the same
narrow RBAC the original challenge granted - `pods/exec`, read access to
most namespaced resources, no secrets access, no cluster scope. Reach the
app through the nginx NodePort service (`30080` by default) or
`kubectl -n challenge port-forward svc/nginx 8080:80`.

## The seven flags

| # | Challenge | Bug |
|---|-----------|-----|
| 1 | Account Not Found | DB credentials sitting in a pod's env vars |
| 2 | Admin Access | Admin password is "encrypted" with a key mounted right next to it |
| 3 | Blocked | The DLP filter that blocks your login leaks a flag in its own incident log |
| 4 | The One Thing That Works | DLP config file has its own secret baked in |
| 5 | Provision My Account | Client-side "NetworkPolicy" is just a scary string; the real gate is a bearer token you can get to in-cluster |
| 6 | The Checklist | Missing-modules guard + a NULL row + a wrong XOR key, stacked three deep |
| 7 | Complete Onboarding | Correlated subquery + 150k rows + no index = timeout every time, until you add one |

Full solve steps, exact commands, and *why* each bug exists: [WRITEUP.md](WRITEUP.md).

## Fidelity notes

A few places where this recreation deliberately simplifies the real
challenge's infrastructure without changing the puzzle:

- **Service-account token check.** The real challenge validated a
  genuine per-pod Kubernetes ServiceAccount token (via TokenReview).
  Recreating that here would mean shipping a TokenReview ClusterRole
  just for a demo, so `credential-store` instead checks a shared secret
  mounted at the conventional SA token path. The puzzle - reach
  credential-store in-cluster with a token instead of through nginx -
  is unchanged.
- **`analyze_burst_activity()`'s slow query** (challenge 7) forces
  `enable_hashjoin`/`enable_mergejoin` off inside the function. Modern
  Postgres is good enough to rewrite the original correlated `EXISTS`
  into an efficient hash join on its own, which would make the bug
  disappear without an index. This models the same failure mode
  (correlated subquery + no index = O(n²)) that shows up constantly in
  ORMs that can't produce anything but a nested-loop-shaped query.
