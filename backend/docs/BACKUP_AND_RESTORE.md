# Backup And Restore

## Backup scope

For production, back up both:

- PostgreSQL database contents
- `backend/storage/spots/` audio files

The database alone is not enough because the spot binaries live on disk.

## Manual backup procedure

### PostgreSQL

```bash
pg_dump "$DATABASE_URL" --format=custom --file /var/backups/dsspot-controller-$(date +%F).dump
```

### Spot storage

```bash
tar -czf /var/backups/dsspot-controller-spots-$(date +%F).tar.gz -C /opt/distributed-spot-controller/DSSpotController_Server/backend/storage spots
```

## Restore procedure

### PostgreSQL

1. Stop the service:

```bash
sudo systemctl stop dsspot-controller.service
```

2. Restore the database:

```bash
pg_restore --clean --if-exists --dbname "$DATABASE_URL" /var/backups/dsspot-controller-YYYY-MM-DD.dump
```

3. Re-apply migrations:

```bash
cd /opt/distributed-spot-controller/DSSpotController_Server/backend
../.venv/bin/python scripts/run_migrations.py
```

### Spot storage

```bash
tar -xzf /var/backups/dsspot-controller-spots-YYYY-MM-DD.tar.gz -C /opt/distributed-spot-controller/DSSpotController_Server/backend/storage
```

4. Start the service again:

```bash
sudo systemctl start dsspot-controller.service
```

## SQLite development note

Development uses SQLite by default. A manual backup is just the DB file plus the `storage/spots` directory:

```bash
cp backend/data/server.db /tmp/server.db.backup
tar -czf /tmp/spots.backup.tar.gz -C backend/storage spots
```
