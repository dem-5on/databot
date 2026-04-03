---
description: how to run celery workers and beat scheduler
---

# Running Celery

Celery handles background tasks and scheduled jobs. You need 3 terminals:

## 1. Start Redis (if not already running)

```bash
sudo systemctl start redis
redis-cli ping  # Should return PONG
```

## 2. Start Celery Worker (Terminal 1)

```bash
cd /home/dae-5om/Main/dae-/PERSONAL_PROJECTS/databot
source env/bin/activate
celery -A app.celery_app worker --loglevel=info
```

## 3. Start Celery Beat Scheduler (Terminal 2)

```bash
cd /home/dae-5om/Main/dae-/PERSONAL_PROJECTS/databot
source env/bin/activate
celery -A app.celery_app beat --loglevel=info
```

## 4. Start FastAPI (Terminal 3)

```bash
cd /home/dae-5om/Main/dae-/PERSONAL_PROJECTS/databot
source env/bin/activate
python3 -m app.main
```

## Useful Commands

### Trigger manual bundle sync

```bash
# From Python shell or API endpoint
from app.tasks import sync_bundles_task
sync_bundles_task.delay()  # Runs async in worker
```

### Check workers status

```bash
celery -A app.celery_app status
```

### View scheduled tasks

```bash
celery -A app.celery_app inspect scheduled
```

### One-liner for development (runs worker + beat together)

```bash
celery -A app.celery_app worker --beat --loglevel=info
```
