#!/usr/bin/env bash

set -e

RED="\e[31m"
BLUE='\e[34m'
ORANGE='\e[33m'
NC='\e[0m' # No Color

CUSTOM_STORAGE_CLASS_FLAG="--custom-storage-class"

# print an error message on an error exit
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'if [ $? -ne 0 ]; then echo -e "${RED}\"${last_command}\" command failed - exiting.${NC}"; fi' EXIT

if [[ "$1" == "$CUSTOM_STORAGE_CLASS_FLAG" ]] ; then
    if [ -z "$2" ]; then
        echo -e "${RED}A storage class name must be provided. Do${NC} \"$0 ${CUSTOM_STORAGE_CLASS_FLAG} <storage-class-name>\""
        exit 0
    fi
    echo -e "${BLUE}Applying persistent volume claims with ${ORANGE}storage class name = $2${NC}. kubectl apply -f persistentVolumeClaims.yaml"
    sed "s/\#  storageClassName: \$CUSTOM_STORAGE_CLASS/  storageClassName: $2/g" persistentVolumeClaims.yaml | kubectl apply -f -
else
    echo -e "${BLUE}Using default storage class. To use a custom storage class, do \"$0 ${CUSTOM_STORAGE_CLASS_FLAG} <storage-class-name>\"${NC}"
    echo -e "${BLUE}Applying persistent volume claims:${NC} kubectl apply -f persistentVolumeClaims.yaml"
    kubectl apply -f persistentVolumeClaims.yaml
fi
