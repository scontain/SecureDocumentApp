#/bin/bash

sconectl apply -f FastApi.yml   # generates the FastAPI image
sconectl apply -f Meshfile.yml  # generates and uploads the policies and writes the 

helm install secure-doc-management target/helm
