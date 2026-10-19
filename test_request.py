"""Sends 6 concurrent requests: 2 run immediately, 4 must be queued."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ip = sys.argv[1]
URL = f"http://{ip}/new_request"
texts = ["I love this course!", "This is terrible.", "What a wonderful day",
         "I hate waiting", "Cloud computing is fun", "The demo failed again"]

def send(i):
    body = json.dumps({"text": texts[i], "simulate_delay": 3}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    data["total_time_s"] = round(time.time() - t0, 2)
    return data

t0 = time.time()
with ThreadPoolExecutor(max_workers=len(texts)) as ex:
    results = list(ex.map(send, range(len(texts))))

for r in results:
    print(f"{r['worker']} queued={r['queued']!s:5} wait={r['wait_in_queue_s']}s "
          f"total={r['total_time_s']}s -> {r['worker_response']['result']}")
print(f"Wall time: {time.time() - t0:.1f}s (expected ~9s: 3 rounds x 3s on 2 workers)")

with open("responses.json", "w") as f:
    json.dump(results, f, indent=2)