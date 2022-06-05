#/bin/bash

set -e


# print an error message on an error exiting
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'if [ $? -ne 0 ]; then echo "\"${last_command}\" command failed - exiting."; fi' EXIT


sconectl apply -f FastApi.yml   # generates the FastAPI image
sconectl apply -f Meshfile.yml  # generates and uploads the policies and writes the 

helm uninstall secure-doc-management 2> /dev/null || true 

helm install secure-doc-management target/helm
