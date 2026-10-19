
import os

from flask import Flask, jsonify, request
from transformers import pipeline

app = Flask(__name__)

WORKER_NAME = os.environ.get("WORKER_NAME", "worker")

#load the model
classifier = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

@app.route("/health")
def health():
    return jsonify(status="ok", worker=WORKER_NAME)

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify(error="Missing 'text' field"), 400
    text = str(data["text"])
    time.sleep(float(data.get("simulate_delay", 0)))  # pour la démo de la file
    r = classifier(text, truncation=True)[0]
    return jsonify(worker=WORKER_NAME, input=text, result={"label": r["label"], "score": round(float(r["score"]), 4)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)