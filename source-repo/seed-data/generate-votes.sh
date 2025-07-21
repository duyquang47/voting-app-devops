#!/bin/sh

VOTES_FOR_A=${VOTES_FOR_A:-200}
VOTES_FOR_B=${VOTES_FOR_B:-100}


ab -n $((VOTES_FOR_A / 2)) -c 50 -p posta -T "application/x-www-form-urlencoded" http://vote:8080/
ab -n $VOTES_FOR_B -c 50 -p postb -T "application/x-www-form-urlencoded" http://vote:8080/
ab -n $((VOTES_FOR_A / 2)) -c 50 -p posta -T "application/x-www-form-urlencoded" http://vote:8080/