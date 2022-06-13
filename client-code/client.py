import os
import time
import json
import random
import string
import requests
import logging as log

from base64 import b64encode


def get_env_or_die(env_var):
    log.info("Getting env var \"{}\"".format(env_var))
    value = os.environ.get(env_var)
    if value is None:
        log.error("cannot get \"{}\" env var".format(env_var))
        exit(1)
    return value


def create_document(nginx_addr, user, passwd, doc_id):
    ''' Creates a document and returns the ID
    returns ducument id (string)
    '''
    letters = string.ascii_letters
    res = requests.post("https://{}/documents/create_document".format(nginx_addr),
        auth=(user, passwd), data=json.dumps({
            "record_id": doc_id,
            "content": ''.join(random.choice(letters) for i in range(15))
        }))
    if res.status_code == 429:
        log.info("ouch! rate limit caught us. Retrying in 70 seconds...")
        time.sleep(70)
        res = requests.post("https://{}/documents/create_document".format(nginx_addr),
        auth=(user, passwd), data=json.dumps({
            "record_id": doc_id,
            "content": ''.join(random.choice(letters) for i in range(15))
        }))
    return res


def read_document(nginx_addr, user, passwd, doc_id):
    '''
    param id (string): ID of the document to read
    returns document content (string)
    '''
    res = requests.get("https://{}/documents/{}".format(nginx_addr, doc_id), auth=(user, passwd))
    if res.status_code == 429:
        log.info("ouch! rate limit caught us. Retrying in 70 seconds...")
        time.sleep(70)
        res = requests.get("https://{}/documents/{}".format(nginx_addr, doc_id), auth=(user, passwd))
    return res


def create_user(nginx_addr):
    letters = string.ascii_letters
    user = ''.join(random.choice(letters) for i in range(15))
    passwd = ''.join(random.choice(letters) for i in range(15))

    res = requests.get("https://{}/users/create_account".format(nginx_addr), auth=(user, passwd))
    if res.status_code != 201:
        log.error("could not create user account: status_code={} response:\n{}\n".format(res.status_code, res.content))
        return None, None
    return user, passwd
    

def do_work(nginx_addr):
    doc_ids = []

    number_of_docs_in_loop = 20
    while_execution_number = 1
    while True:
        log.info("Creating user")
        user, passwd = create_user(nginx_addr)
        if user is None or passwd is None:
            log.error("could not get auth creds")
            continue
        log.info("New user-passwd pair: user={} passwd={}".format(user, passwd))


        log.info("Creating documents")
        for i in range(number_of_docs_in_loop):
            res = create_document(nginx_addr, user, passwd, str(i))
            if res.status_code != 200:
                log.error("got status code different from 200")
                log.error(res.json())
                time.sleep(2)
                continue
            log.info("response={}".format(res.json()))
            time.sleep(2) 
        time.sleep(10)

        log.info("Reading written documents")
        for i in range(number_of_docs_in_loop):
            res = read_document(nginx_addr, user, passwd, str(i))
            if res.status_code != 200:
                continue
            log.info("response={}".format(res.json()))
            time.sleep(1)
        time.sleep(10)

        # empty doc_ids again
        doc_ids = []

        log.info("Finished execution number {}\n".format(while_execution_number))
        while_execution_number += 1


def wait_for_nginx(nginx_addr):
    while True:
        try:
            requests.get("https://{}/documents/1".format(nginx_addr), timeout=5)
            # if request went well, no matter which status code, NGINX is ready: get out of loop
            break
        except:
            log.warning("NGINX not available yet. Will try again in 10 seconds...")
            time.sleep(10)


if __name__ == '__main__':
    log.basicConfig(level=log.INFO)

    nginx_addr = get_env_or_die("NGINX_ADDR")

    wait_for_nginx(nginx_addr)

    do_work(nginx_addr)
