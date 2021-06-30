#!/bin/sh
cd /opt/libresbc/run/liberator
LOGLEVEL=debug
WORKERS=$(expr 1 + 2 \* $(nproc))
ADDRESS=0.0.0.0
PORT=8080
MODULE=main:fapi
# run asgi server
uvicorn $MODULE --host $ADDRESS --port $PORT --workers $WORKERS --reload \
 --log-level $LOGLEVEL --use-colors --access-log &
