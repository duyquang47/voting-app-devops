from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json
import logging

option_a = os.getenv('OPTION_A', "Dogs")
option_b = os.getenv('OPTION_B', "Cats")
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

@app.route("/", methods=['POST','GET'])
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

@app.route("/metrics", methods=['GET'])
def metrics():
    redis = get_redis()
    votes = redis.lrange('votes', 0, -1)
    count_a = 0
    count_b = 0
    for v in votes:
        try:
            data = json.loads(v)
            if data.get('vote') == 'a':
                count_a += 1
            elif data.get('vote') == 'b':
                count_b += 1
        except Exception:
            continue
    metrics_text = f"vote_count_a {count_a}\nvote_count_b {count_b}\n"
    return app.response_class(
        response=metrics_text,
        status=200,
        mimetype='text/plain; version=0.0.4'
    )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
