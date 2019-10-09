#!/bin/bash

docker network rm python_redis_net 
docker network create python_redis_net

docker stop redis_server
docker rm redis_server
docker run --name redis_server --network python_redis_net -v data:/data -d redis 

docker build -t proxy:latest -f ./proxy_pool/Dockerfile .
docker run -e db_type=REDIS -e db_host=redis_server -e db_port=6379 -p 5010:5010 --network python_redis_net -d proxy:latest
