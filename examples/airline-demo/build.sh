#! /bin/bash
# For the avoidance of doubt, this script is meant to be run with the airline-demo directory as pwd
# Builds the Docker image for Airflow and scaffolds the DAGs

pip install --upgrade pip

cp -R ../dagster . && \
cp -R ../dagster-graphql . && \
cp -R ../dagstermill . && \
\
rm -rf dagster/.tox && \
rm -rf dagster-graphql/.tox && \
rm -rf dagstermill/.tox && \
\
rm -rf dagster/dist && \
rm -rf dagster-graphql/dist && \
rm -rf dagstermill/dist && \
\
rm -rf .tox dist && \
\
docker build -t airline-demo-airflow . && \
docker tag airline-demo-airflow dagster/airline-demo-airflow

rm -rf dagster && \
rm -rf dagster-graphql && \
rm -rf dagstermill 
