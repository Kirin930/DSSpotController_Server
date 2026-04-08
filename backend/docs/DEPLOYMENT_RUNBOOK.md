# Deployment Runbook

## 1. Prepare host

1. Install Python 3.12+, `systemd`, and PostgreSQL client tools.
2. Create a service user, for example `spotcontroller`.
3. Clone the repository to `/opt/distributed-spot-controller/DSSpotController_Server`.
4. Create a virtual environment in the repo root:

```bash
python3 -m venv /opt/distributed-spot-controller/DSSpotController_Server/.venv
```

5. Install backend dependencies:

```bash
/opt/distributed-spot-controller/DSSpotController_Server/.venv/bin/pip install -r /opt/distributed-spot-controller/DSSpotController_Server/backend/requirements.txt
```

## 2. Configure environment

1. Copy `backend/.env.example` to `backend/.env`.
2. Set at minimum:

- `SECRET_KEY`
- `DATABASE_URL`
- `PUBLIC_BASE_URL`
- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_PASSWORD`
- `SESSION_COOKIE_SECURE=true` for HTTPS deployments

## 3. Apply DB migrations

Run migrations before first start and after each deployment:

```bash
cd /opt/distributed-spot-controller/DSSpotController_Server/backend
../.venv/bin/python scripts/run_migrations.py
```

For PostgreSQL-specific validation:

```bash
../.venv/bin/python scripts/validate_postgresql_schema.py
```

## 4. Install service

1. Copy `backend/deploy/systemd/dsspot-controller.service` to `/etc/systemd/system/`.
2. Adjust paths and user/group if your install location differs.
3. Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dsspot-controller.service
```

## 5. Verify runtime

1. Check service health:

```bash
systemctl status dsspot-controller.service
curl http://127.0.0.1:8000/api/health
```

2. Review logs:

```bash
journalctl -u dsspot-controller.service -f
```

## 6. Restart policy

The provided unit uses:

- `Restart=always`
- `RestartSec=5`

That matches the Q&A expectation of host-supervised restarts under `systemd`.

## 7. Rolling out updates

1. Pull the new code.
2. Reinstall dependencies if `requirements.txt` changed.
3. Run `scripts/run_migrations.py`.
4. Restart the service:

```bash
sudo systemctl restart dsspot-controller.service
```

5. Re-run the UAT subset most relevant to the release.
