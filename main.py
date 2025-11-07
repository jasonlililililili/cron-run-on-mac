#!/usr/bin/env python3
"""
Cron Daemon - A long-running daemon that schedules and executes tasks based on cron expressions
"""

import json
import logging
import signal
import sys
import importlib.util
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cron-daemon.log')
    ]
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def load_json_config(file_path):
    """Load and parse a JSON configuration file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise


def load_module_from_file(file_path, module_name=None):
    """
    Dynamically load a Python module from a file path
    
    Args:
        file_path: Path to the Python file
        module_name: Optional name for the module (defaults to file name)
    
    Returns:
        The loaded module object
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Module file not found: {file_path}")
            return None
        
        if module_name is None:
            module_name = file_path.stem
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load spec for module: {file_path}")
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        logger.error(f"Error loading module from {file_path}: {e}", exc_info=True)
        return None


def run_task(task_id, task_definitions):
    """
    Execute a task by its task ID
    
    Args:
        task_id: The ID of the task to run
        task_definitions: Dictionary of task definitions from task-definition.json
    """
    try:
        if task_id not in task_definitions:
            logger.error(f"Task ID '{task_id}' not found in task definitions")
            return
        
        task_info = task_definitions[task_id]
        task_location = task_info.get('location')
        
        if not task_location:
            logger.error(f"No location specified for task '{task_id}'")
            return
        
        logger.info(f"Running task '{task_id}' from {task_location}")
        
        # Load the task module
        task_module = load_module_from_file(task_location, f"task_{task_id}")
        
        if task_module is None:
            logger.error(f"Failed to load task module for '{task_id}'")
            return
        
        # Execute the task's run function
        if not hasattr(task_module, 'run'):
            logger.error(f"Task module '{task_id}' does not have a 'run' function")
            return
        
        result = task_module.run()
        logger.info(f"Task '{task_id}' completed with result: {result}")
        
    except Exception as e:
        logger.error(f"Error executing task '{task_id}': {e}", exc_info=True)


def execute_cron_event(event_script_path, task_definitions):
    """
    Execute a cron event script to determine if a task should run
    
    Args:
        event_script_path: Path to the cron event script
        task_definitions: Dictionary of task definitions
    """
    try:
        logger.info(f"Executing cron event: {event_script_path}")
        
        # Load the cron event module
        event_module = load_module_from_file(event_script_path)
        
        if event_module is None:
            logger.error(f"Failed to load cron event script: {event_script_path}")
            return
        
        # Call the task_id function to determine which task to run
        if not hasattr(event_module, 'task_id'):
            logger.error(f"Cron event script '{event_script_path}' does not have a 'task_id' function")
            return
        
        task_id_result = event_module.task_id()
        
        if task_id_result is None:
            logger.info(f"Cron event '{event_script_path}' returned None - no task to run")
            return
        
        logger.info(f"Cron event '{event_script_path}' returned task ID: '{task_id_result}'")
        
        # Run the task
        run_task(task_id_result, task_definitions)
        
    except Exception as e:
        logger.error(f"Error executing cron event '{event_script_path}': {e}", exc_info=True)


def setup_scheduler(cron_jobs, task_definitions):
    """
    Set up the APScheduler with all cron jobs
    
    Args:
        cron_jobs: List of cron job definitions
        task_definitions: Dictionary of task definitions
    
    Returns:
        BackgroundScheduler instance
    """
    scheduler = BackgroundScheduler()
    
    for idx, job in enumerate(cron_jobs):
        cron_expression = job.get('cron')
        task_reference = job.get('task-reference')
        
        if not cron_expression or not task_reference:
            logger.error(f"Invalid cron job definition at index {idx}: {job}")
            continue
        
        try:
            # Parse cron expression (format: minute hour day month day_of_week)
            parts = cron_expression.split()
            if len(parts) != 5:
                logger.error(f"Invalid cron expression format: {cron_expression}")
                continue
            
            minute, hour, day, month, day_of_week = parts
            
            # Add the job to the scheduler
            scheduler.add_job(
                func=execute_cron_event,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                args=[task_reference, task_definitions],
                id=f"cron_job_{idx}",
                name=f"Cron Job {idx}: {task_reference}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled cron job {idx}: '{cron_expression}' -> {task_reference}")
            
        except Exception as e:
            logger.error(f"Error adding cron job {idx}: {e}", exc_info=True)
    
    return scheduler


def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global scheduler
    
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")
    
    sys.exit(0)


def main():
    """Main entry point for the cron daemon"""
    global scheduler
    
    logger.info("=" * 60)
    logger.info("Starting Cron Daemon")
    logger.info("=" * 60)
    
    try:
        # Load configurations
        logger.info("Loading configuration files...")
        cron_jobs = load_json_config('cron.json')
        task_definitions = load_json_config('task-definition.json')
        
        logger.info(f"Loaded {len(cron_jobs)} cron job(s)")
        logger.info(f"Loaded {len(task_definitions)} task definition(s)")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        logger.info("Signal handlers registered")
        
        # Set up and start the scheduler
        scheduler = setup_scheduler(cron_jobs, task_definitions)
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        logger.info("Cron Daemon is running. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

