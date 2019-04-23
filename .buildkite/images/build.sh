#! /bin/bash

docker build python/ --build-arg pyver=3.7.3 -t dagster/buildkite-python:3.7.3 
docker build python/ --build-arg pyver=3.6.8 -t dagster/buildkite-python:3.6.8 
docker build python/ --build-arg pyver=3.5.7 -t dagster/buildkite-python:3.5.7
docker build python/ --build-arg pyver=2.7.16 -t dagster/buildkite-python:2.7.16

docker push dagster/buildkite-python:3.7.3
docker push dagster/buildkite-python:3.6.8 
docker push dagster/buildkite-python:3.5.7
docker push dagster/buildkite-python:2.7.16

docker build pynode/ -t dagster/buildkite-pynode
docker push dagster/buildkite-pynode