
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

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data.get("text", "")

    result = classifier(text)[0]

    return jsonify({
        "worker": WORKER_NAME,
        "input": text,
        "label": result["label"],
        "score": result["score"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)