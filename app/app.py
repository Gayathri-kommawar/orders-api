from flask import Flask, jsonify
import os

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "7.8")
GIT_SHA = os.getenv("GIT_SHA", "unknown")

@app.route("/")
def home():
    return jsonify({
        "application": "orders-api",
        "version": VERSION,
        "git_sha": GIT_SHA,
        "status": "running"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": VERSION
    }), 200

@app.route("/orders")
def orders():
    return jsonify({
        "application": "orders-api",
        "version": VERSION,
        "orders": ["Order-101", "Order-102"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)