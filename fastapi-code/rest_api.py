import hashlib
import os
import secrets
import ssl

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import pymysql
import pymemcache

PYMYSQL_DUPLICATE_ERROR = 1062
RATE_LIMIT = 10  # acceptable client requests per minute

# connection to database
DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
# DB_PASSWORD = os.environ["DB_PASSWORD"]

# TLS args
mariadb_ca_path = '/etc/mariadb-ca.crt'
mariadb_cert_path = '/etc/mariadb-client.crt'
mariadb_key_path = '/etc/mariadb-client.key'

connection = pymysql.connect(host=DB_HOST,
                             user=DB_USER,
                             # password=DB_PASSWORD,
                             ssl={
                                 'mode': 'VERIFY_IDENTITY',
                                 'cert': mariadb_cert_path,
                                 'key': mariadb_key_path,
                                 'ca': mariadb_ca_path
                             },
                             cursorclass=pymysql.cursors.DictCursor)

# connect to memcached
MC_HOST = os.environ["MC_HOST"]

# TLS args
memcached_ca_path = '/etc/memcached-ca.crt'
memcached_cert_path = '/etc/memcached-client.crt'
memcached_key_path = '/etc/memcached-client.key'

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=memcached_ca_path)
context.load_cert_chain(certfile=memcached_cert_path, keyfile=memcached_key_path)

mc_client = pymemcache.client.base.Client((MC_HOST, 11211), tls_context=context)


# FastAPI config
class Document(BaseModel):
    record_id: int
    content: str


app = FastAPI()

# FastAPI security - HTTPBasic
security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    compare_credentials = get_user_account(credentials.username)

    correct_username = secrets.compare_digest(credentials.username, compare_credentials['username'])

    # recalculate hash
    new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        credentials.password.encode('utf-8'),  # Convert the password to bytes
        compare_credentials['salt'],
        100000,
        dklen=128
    )

    # compare recalculated hash with actual hash
    correct_password = secrets.compare_digest(new_hash, compare_credentials['hash'])
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/users/me")
def read_current_user(request: Request, username: str = Depends(get_current_username)):
    rate_limit(request.client.host)
    return {"username": username}


@app.get("/users/create_account", status_code=status.HTTP_201_CREATED)
def create_account(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    rate_limit(request.client.host)
    create_user_account(credentials)
    return {"username": credentials.username}


# FastAPI document service methods
@app.post("/documents/create_document")
async def create_document(request: Request, document: Document, username: str = Depends(get_current_username)):
    rate_limit(request.client.host)
    insert_document(document, username)
    return document


@app.get("/documents/{record_id}")
async def read_record(request: Request, record_id: int, username: str = Depends(get_current_username)):
    rate_limit(request.client.host)
    return get_document(record_id, username)
    # return {"record_id": record_id}


# memcached rate limiting methods
def rate_limit(client_ip):
    hits = mc_client.get(key=client_ip)

    if not hits:
        mc_client.set(key=client_ip, value=1, expire=60)
    elif int(hits.decode('utf-8')) > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Requests exceed more than {RATE_LIMIT} requests in the last minute"
        )
    else:
        mc_client.incr(key=client_ip, value=1)


# database methods
def get_user_account(username: str):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM document_db.account AS doc WHERE doc.username = %s"
            cursor.execute(sql, username)
            result = cursor.fetchone()
    except pymysql.Error as err:
        print("could not close connection error pymysql %d: %s" % (err.args[0], err.args[1]))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return result


def create_user_account(credentials: HTTPBasicCredentials):
    # storing plane text passwords is bad
    # hash password
    salt = os.urandom(32)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',  # The hash digest algorithm for HMAC
        credentials.password.encode('utf-8'),  # Convert the password to bytes
        salt,  # Provide the salt
        100000,  # It is recommended to use at least 100,000 iterations of SHA-256
        dklen=128  # Get a 128 byte key
    )

    try:
        # insert user account into database
        with connection.cursor() as cursor:
            sql = "INSERT INTO document_db.account (username, hash, salt) VALUES (%s, %s, %s)"
            cursor.execute(sql, (credentials.username, pw_hash, salt))

        connection.commit()

    except pymysql.Error as err:
        if err.args[0] == PYMYSQL_DUPLICATE_ERROR:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This username is already taken.")

        print("could not close connection error pymysql %d: %s" % (err.args[0], err.args[1]))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_document(record_id: int, username: str):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM document_db.document AS doc WHERE doc.record_id = %s AND doc.owner = %s"
            cursor.execute(sql, (record_id, username))
            result = cursor.fetchone()
    except pymysql.Error as err:
        print("could not close connection error pymysql %d: %s" % (err.args[0], err.args[1]))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="A document with this record ID does not exist")

    return result


def insert_document(document: Document, username: str):
    try:
        # insert document into database
        with connection.cursor() as cursor:
            sql = "INSERT INTO document_db.document (record_id, content, owner) VALUES (%s, %s, %s)"
            cursor.execute(sql, (document.record_id, document.content, username))

        connection.commit()

    except pymysql.Error as err:
        if err.args[0] == PYMYSQL_DUPLICATE_ERROR:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="This record ID already exists. Please specify a different ID")

        print("could not close connection error pymysql %d: %s" % (err.args[0], err.args[1]))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# main
if __name__ == "__main__":
    # get uvicorn TLS args for secure connection to nginx
    server_ca_path = '/etc/fastapi-ca.crt'
    server_cert_path = '/etc/server.crt'
    server_key_path = '/etc/server.key'

    uvicorn.run(
        "rest_api:app", host="0.0.0.0", log_level="info", port=8000,
        ssl_ca_certs=server_ca_path, ssl_certfile=server_cert_path, ssl_keyfile=server_key_path,
        ssl_cert_reqs=2  # require client side certs
    )
