from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World"

if __name__ == '__main__':
    port = 5004
    print(f"Starting simple server on {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
