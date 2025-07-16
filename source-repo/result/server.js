const express = require('express');
const async = require('async');
const { Pool } = require('pg');
const cookieParser = require('cookie-parser');
const promClient = require('prom-client');
const pino = require('pino');
const pinoHttp = require('pino-http');
const path = require('path');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.Server(app);
const io = socketIo(server);

const port = process.env.PORT || 4000;

// ---------- Logging ----------
const logger = pino(); // Main logger
const httpLogger = pinoHttp({ logger }); // Middleware for HTTP access log
app.use(httpLogger);

// ---------- Prometheus Metrics ----------
const register = promClient.register;

const voteCounts = new promClient.Gauge({
  name: 'result_vote_counts',
  help: 'Current vote counts by option',
  labelNames: ['vote_option']
});

// ---------- PostgreSQL ----------
const pool = new Pool({
  connectionString: 'postgres://postgres:postgres@db/postgres'
});

// ---------- Socket.IO ----------
io.on('connection', function (socket) {
  socket.emit('message', { text : 'Welcome!' });
  socket.on('subscribe', function (data) {
    socket.join(data.channel);
  });
});

// ---------- Database retry logic ----------
async.retry(
  { times: 1000, interval: 1000 },
  function (callback) {
    pool.connect(function (err, client, done) {
      if (err) {
        logger.warn("Waiting for db");
      }
      callback(err, client);
    });
  },
  function (err, client) {
    if (err) {
      return logger.error("Giving up connecting to DB");
    }
    logger.info("Connected to db");
    getVotes(client);
  }
);

// ---------- Vote Polling ----------
function getVotes(client) {
  client.query('SELECT vote, COUNT(id) AS count FROM votes GROUP BY vote', [], function (err, result) {
    if (err) {
      logger.error("Error performing query: " + err);
    } else {
      const votes = collectVotesFromResult(result);
      io.sockets.emit("scores", JSON.stringify(votes));

      // Update Prometheus metrics
      voteCounts.labels('a').set(votes.a || 0);
      voteCounts.labels('b').set(votes.b || 0);
    }

    setTimeout(() => getVotes(client), 1000);
  });
}

function collectVotesFromResult(result) {
  const votes = { a: 0, b: 0 };
  result.rows.forEach(row => {
    votes[row.vote] = parseInt(row.count);
  });
  return votes;
}

// ---------- Express Middlewares ----------
app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname + '/views'));

// ---------- Routes ----------
app.get('/', function (req, res) {
  res.sendFile(path.resolve(__dirname + '/views/index.html'));
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (err) {
    logger.error("Error exposing metrics: " + err);
    res.status(500).end(err);
  }
});

// ---------- Start Server ----------
server.listen(port, function () {
  logger.info(`App running on port ${port}`);
});
