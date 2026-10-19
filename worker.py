
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

WORKER_NAME = os.environ.get("WORKER_NAME", "worker")

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()

    text = data.get("text", "")

    return jsonify({
        "worker": WORKER_NAME,
        "input": text,
        "response": f"Received: {text}"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)