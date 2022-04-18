#/bin/bash

alias scone="docker run -it --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v \"$HOME/.docker:/root/.docker\" \
    -v \"$HOME/.cas:/root/.cas\" \
    -v \"$HOME/.scone:/root/.scone\" \
    -v \"\$PWD:/root\" \
    -w /root \
    registry.scontain.com:5050/cicd/sconecli scone"

scone apply -f FastApi.yml   # generates the FastAPI image
scone apply -f Meshfile.yml  # generates and uploads the policies and writes the 

kubectl create namespace SecureDocuments # ensure that we have the right name
helm install --namespace SecureDocuments secure-doc-management # use helm chart to install
