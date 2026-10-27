import json
from datetime import datetime, timezone

def log(component, event, **fields):
    print(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                          component=component, event=event, **fields)), flush=True)
