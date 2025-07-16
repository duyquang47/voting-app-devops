from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json
import logging
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger

# --- Cấu hình ---
option_a = os.getenv('OPTION_A', "Dogs")
option_b = os.getenv('OPTION_B', "Cats")
hostname = socket.gethostname()

app = Flask(__name__)

# --- Logger JSON ---
logger = logging.getLogger("vote-app")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
app.logger.addHandler(logHandler)
app.logger.setLevel(logging.INFO)

# --- Log sau mỗi request ---
@app.after_request
def log_request_info(response):
    logger.info(
        "Request handled",
        extra={
            'request_path': request.path,
            'http_method': request.method,
            'response_code': response.status_code
        }
    )
    return response

# --- Tích hợp gunicorn logging ---
gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

# --- Prometheus metric ---
VOTE_COUNT = Gauge('vote_votes', 'Current vote count', ['vote_option'])

# --- Kết nối Redis ---
def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

# --- Route chính ---
@app.route("/", methods=['POST', 'GET'])
def hello():
    voter_id = request.cookies.get('voter_id')
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    vote = None

    if request.method == 'POST':
        redis = get_redis()
        vote = request.form['vote']
        app.logger.info('Received vote for %s', vote)
        data = json.dumps({'voter_id': voter_id, 'vote': vote})
        redis.rpush('votes', data)

    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        hostname=hostname,
        vote=vote,
    ))
    resp.set_cookie('voter_id', voter_id)
    return resp

# --- Prometheus metrics endpoint ---
@app.route("/metrics")
def metrics():
    redis = get_redis()
    vote_counts = {option_a: 0, option_b: 0}
    
    for item in redis.lrange('votes', 0, -1):
        try:
            data = json.loads(item)
            vote = data.get('vote')
            if vote in vote_counts:
                vote_counts[vote] += 1
        except Exception as e:
            app.logger.warning("Failed to parse vote: %s", str(e))

    # Cập nhật lại Gauge metric
    for vote_option, count in vote_counts.items():
        VOTE_COUNT.labels(vote_option=vote_option).set(count)

    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# --- Khởi chạy ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
