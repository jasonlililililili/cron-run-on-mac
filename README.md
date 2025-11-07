# cron-run-on-mac

A Python-based cron daemon that schedules and executes tasks based on cron expressions. This daemon runs continuously, dynamically loading event handlers and task scripts to determine when and what to execute.

## Features

- Long-running daemon process with APScheduler
- Support for multiple cron jobs with different schedules
- Dynamic loading of cron-event scripts and task modules
- Comprehensive error handling and logging
- Graceful shutdown on interrupts (Ctrl+C)
- Task isolation - errors in one task won't crash the daemon

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### cron.json

Defines the cron schedules and their associated event handlers:

```json
[
    {
        "cron": "0 * * * *",
        "task-reference": "./cron-event/example.py"
    }
]
```

- `cron`: Cron expression in the format `minute hour day month day_of_week`
- `task-reference`: Path to the cron-event script that determines which task to run

### task-definition.json

Maps task IDs to their implementation scripts:

```json
{
    "example-task": {
        "description": "This is an example task",
        "location": "./task/example-task.py"
    }
}
```

## Usage

### Running the Daemon

Start the daemon:
```bash
python main.py
```

The daemon will:
1. Load all cron job definitions from `cron.json`
2. Load all task definitions from `task-definition.json`
3. Schedule each cron job with APScheduler
4. Run continuously, executing cron-events at scheduled times

To stop the daemon, press `Ctrl+C` for a graceful shutdown.

### Creating Cron-Event Scripts

Cron-event scripts (in `cron-event/` directory) must implement a `task_id()` function:

```python
def task_id():
    if should_run_task():
        return "example-task"  # Return task ID from task-definition.json
    return None  # Return None if task should not run

def should_run_task():
    # Your conditional logic here
    return True
```

### Creating Task Scripts

Task scripts (in `task/` directory) must implement a `run()` function:

```python
import logging

logger = logging.getLogger(__name__)

def run():
    logger.info("Running task logic")
    # Your task implementation here
    return True  # Return status or result
```

## Project Structure

```
cron-run-on-mac/
├── main.py                  # Main daemon script
├── cron.json               # Cron job definitions
├── task-definition.json    # Task ID to script mappings
├── requirements.txt        # Python dependencies
├── cron-daemon.log        # Log file (created at runtime)
├── cron-event/            # Cron event handler scripts
│   └── example.py
└── task/                  # Task implementation scripts
    └── example-task.py
```

## Logging

The daemon logs to both:
- Console (stdout)
- `cron-daemon.log` file

Logs include:
- Daemon startup and shutdown
- Scheduled job information
- Task executions and results
- Errors with full stack traces

## Error Handling

- Configuration errors: Logged and daemon exits
- Cron-event errors: Logged, daemon continues running
- Task errors: Logged, daemon continues running
- The daemon only stops on intentional interrupts (SIGINT/SIGTERM)