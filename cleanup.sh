#!/usr/bin/env bash

helm uninstall secure-doc-management 
kubectl delete -f persistentVolumeClaims.yaml
rm -rf target
unset APP_NAMESPACE
echo -e "export RELEASE=\"secure-doc-management\"\n" > release.sh

kubectl delete -f persistentVolumeClaims.yaml

./setup.sh


