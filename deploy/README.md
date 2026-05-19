# Deployment playbook — pixel.rafeldt.ch

Target: Hetzner VPS (157.90.112.14), TLJH-managed Traefik already terminating
HTTPS for kuersli.ch and friends. We add the bildfilter app at
`https://pixel.rafeldt.ch` behind Gunicorn on 127.0.0.1:5001.

## 0. DNS

In your rafeldt.ch DNS panel, add:

```
pixel.rafeldt.ch.   A   157.90.112.14
```

Wait until `dig +short pixel.rafeldt.ch` returns the right address.

## 1. Clone and install on the server

```bash
ssh root@157.90.112.14

cd /opt
git clone <your-github-url> pixel
cd pixel

python3 -m venv .venv
source .venv/bin/activate
pip install -r stempel-wanderung/requirements.txt
```

## 2. Configure secrets

```bash
cp deploy/pixel.env.example /etc/pixel.env
nano /etc/pixel.env                   # set APP_SECRET and TEACHER_PASSWORD
chmod 600 /etc/pixel.env
```

## 3. Seed the student roster

Copy your class roster CSV to the server (it is NOT in git):

```bash
# from your laptop:
scp Auswahl_Person__19-05-2026.csv root@157.90.112.14:/opt/pixel/
```

Then on the server:

```bash
cd /opt/pixel/stempel-wanderung
../.venv/bin/python import_students.py ../Auswahl_Person__19-05-2026.csv
../.venv/bin/python generate_login_cards.py https://pixel.rafeldt.ch
```

Pull `login_cards.pdf` back to your laptop to print:

```bash
# from your laptop:
scp root@157.90.112.14:/opt/pixel/stempel-wanderung/login_cards.pdf .
```

## 4. systemd service

```bash
cp /opt/pixel/deploy/pixel.service /etc/systemd/system/pixel.service
systemctl daemon-reload
systemctl enable --now pixel
systemctl status pixel
curl -I http://127.0.0.1:5001/        # should return 200 OK
```

If the service fails to start, check:

```bash
journalctl -u pixel -e
```

## 5. Traefik routing

```bash
cp /opt/pixel/deploy/pixel.toml /opt/tljh/state/rules/pixel.toml
```

**Before reloading, check the entryPoint and certResolver names match
your existing setup.** Run:

```bash
ls /opt/tljh/state/rules/
cat /opt/tljh/state/rules/kuersli*.toml      # or whatever the kuersli rule is called
```

If kuersli's file uses different names for entryPoints (e.g. `web`/`websecure`
instead of `http`/`https`) or a different `certResolver`, edit `pixel.toml`
to match.

TLJH-managed Traefik reloads dynamic config automatically. Verify:

```bash
curl -I https://pixel.rafeldt.ch       # expect 200 OK with Let's Encrypt cert
```

## 6. Test in a browser

1. Open <https://pixel.rafeldt.ch> — login page should appear.
2. Log in with a username/password from `login_cards.pdf`.
3. Open <https://pixel.rafeldt.ch/teacher>, log in with `TEACHER_PASSWORD`,
   award a stamp to a test student.
4. Switch back to the student tab — two new colours on the picture.

## Updating the deployment

```bash
ssh root@157.90.112.14
cd /opt/pixel
git pull
source .venv/bin/activate
pip install -r stempel-wanderung/requirements.txt   # if requirements changed
systemctl restart pixel
```

Re-importing the roster (e.g. mid-year transfer-ins) keeps existing
passwords because `credentials.csv` is preserved:

```bash
cd /opt/pixel/stempel-wanderung
../.venv/bin/python import_students.py ../new_roster.csv
../.venv/bin/python generate_login_cards.py https://pixel.rafeldt.ch
```

Then `scp login_cards.pdf` back to print only the new students' cards.

## Files

- `pixel.service` — systemd unit, runs Gunicorn with 2 workers on :5001.
- `pixel.toml` — Traefik dynamic config; routes pixel.rafeldt.ch to :5001
  with HTTPS via Let's Encrypt.
- `pixel.env.example` — env-var template for `APP_SECRET` + `TEACHER_PASSWORD`.

## Backups

The single piece of state that matters is the SQLite database at
`/opt/pixel/stempel-wanderung/data/progress.db`. Stamp progress lives
there. Back it up with a cron job, e.g.:

```cron
0 18 * * * cp /opt/pixel/stempel-wanderung/data/progress.db /root/backups/progress-$(date +\%F).db
```
