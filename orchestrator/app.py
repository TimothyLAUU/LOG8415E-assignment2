"""Orchestrator: routes requests to free workers, queues them when both are busy."""
import json
import os
import threading
import time
from collections import deque

import requests
from flask import Flask, request, jsonify

STATUS_FILE = os.getenv("STATUS_FILE", "status.json")
WORKER_TIMEOUT = 120      # max seconds for a worker to answer
CLIENT_TIMEOUT = 600      # max seconds a client waits (including queue time)

app = Flask(__name__)
lock = threading.Lock()   # protects status.json and the queue
pending = deque()         # FIFO queue of Job objects


# ---------- status.json helpers (always called with the lock, except reads) ----------
def read_status():
    with open(STATUS_FILE) as f:
        return json.load(f)


def write_status(status):
    tmp = STATUS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(status, f, indent=2)
    os.replace(tmp, STATUS_FILE)  # atomic


def init_status():
    status = {
        f"worker{i}": {"ip": os.environ[f"WORKER{i}_IP"], "port": "5000", "status": "free"}
        for i in (1, 2)
    }
    write_status(status)


def set_status(name, value):
    status = read_status()
    status[name]["status"] = value
    write_status(status)


def claim_worker():
    """Return the name of a free worker and mark it busy, or None. Call with lock held."""
    status = read_status()
    for name, w in status.items():
        if w["status"] == "free":
            w["status"] = "busy"
            write_status(status)
            return name
    return None


# ---------- jobs ----------
class Job:
    def __init__(self, payload):
        self.payload = payload
        self.done = threading.Event()
        self.response = None
        self.code = 500
        self.queued = False
        self.worker = None
        self.enqueued_at = time.time()
        self.started_at = None


def run_on_worker(name, job):
    """Process `job` on worker `name`, then keep draining the queue until it is empty."""
    while True:
        job.worker = name
        job.started_at = time.time()
        try:
            w = read_status()[name]
            r = requests.post(f"http://{w['ip']}:{w['port']}/process",
                              json=job.payload, timeout=WORKER_TIMEOUT)
            job.code, job.response = r.status_code, r.json()
        except Exception as exc:  # worker down, timeout, bad JSON...
            job.code, job.response = 502, {"error": str(exc)}
        job.done.set()

        with lock:
            if pending:                      # a request is waiting: take it, stay busy
                job = pending.popleft()
                continue
            set_status(name, "free")         # nothing waiting: free the worker
            return


@app.route("/new_request", methods=["POST"])
def new_request():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="Invalid or missing JSON body"), 400

    job = Job(payload)
    with lock:
        name = claim_worker()
        if name is None:                     # both busy -> queue
            job.queued = True
            pending.append(job)

    if name is not None:
        threading.Thread(target=run_on_worker, args=(name, job), daemon=True).start()

    if not job.done.wait(timeout=CLIENT_TIMEOUT):
        return jsonify(error="timed out waiting for a worker"), 504

    return jsonify(
        worker=job.worker,
        queued=job.queued,
        wait_in_queue_s=round(job.started_at - job.enqueued_at, 3),
        worker_response=job.response,
    ), job.code


@app.route("/status")
def status():
    with lock:
        return jsonify(workers=read_status(), queue_length=len(pending))


init_status()