import threading
import queue

# Create the queue
task_queue = queue.Queue()

def db_worker():
    while True:
        task = task_queue.get()
        if task is None:
            break

        try:
            task()
        except Exception as e:
            print(f"Error during database operation: {e}")
        finally:
            task_queue.task_done()

def start_worker_queue():
    """Starts the worker thread."""
    worker_thread = threading.Thread(target=db_worker, daemon=True)
    worker_thread.start()
    return worker_thread

def add_to_queue(task):
    """Adds a function to the database writes queue."""
    task_queue.put(task)

def stop_worker():
    """Stops the worker by sending a None task."""
    task_queue.put(None)