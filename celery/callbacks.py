# c:\Mood_Market\celery\callbacks.py
import time
import logging
from celery.signals import task_prerun, task_postrun, task_failure

logger = logging.getLogger("celery.logger")

# Local storage to track start times
_task_start_times = {}


@task_prerun.connect
def on_task_prerun(task_id, task, **kwargs):
    """Fires before a task runs, marking the baseline timestamp."""
    _task_start_times[task_id] = time.perf_counter()


@task_postrun.connect
def on_task_postrun(task_id, task, state, **kwargs):
    """Fires after task completion, calculating total duration."""
    start_time = _task_start_times.pop(task_id, None)
    if start_time is not None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            f"Task '{task.name}' [{task_id}] completed in state '{state}' "
            f"in {duration_ms:.2f}ms."
        )


@task_failure.connect
def on_task_failure(task_id, exception, args, kwargs, traceback, einfo, **extra_kwargs):
    """Fires upon task failure, logging details for alerts."""
    logger.critical(
        f"❌ Task Failure Alert: Task ID '{task_id}' raised exception: {exception}\n"
        f"Arguments: {args} | Kwargs: {kwargs}\n"
        f"Traceback: {traceback}"
    )
