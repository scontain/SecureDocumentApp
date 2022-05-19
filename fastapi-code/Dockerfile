
# First stage: apply the binary-fs
# FOR BUILDING WITH BINARYFS
FROM registry.scontain.com:5050/sconecuratedimages/apps:python-3.7.3-alpine3.10 AS binary-fs

COPY rest_api.py /.
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt


RUN rm /usr/lib/python3.7/config-3.7m-x86_64-linux-gnu/libpython3.7m.a && \
    mkdir binary-fs-dir && \
    scone binaryfs / /binary-fs-dir -v \
        --include '/usr/lib/python3.7/*' \
        --include /lib/libssl.so.1.1 \
        --include /lib/libcrypto.so.1.1 \
        --include '/lib/libz.so.1*' \
        --include '/usr/lib/libbz2.so.1*' \
        --include '/usr/lib/libsqlite3.so.0*' \
        --include '/usr/lib/libev.so.4*' \
        --include '/usr/lib/libffi.so.6*' \
        --include '/usr/lib/libexpat.so.1*' \
        --include /rest_api.py


# Second stage: compile the binary fs
FROM registry.scontain.com:5050/sconecuratedimages/crosscompilers:alpine as crosscompiler

COPY --from=binary-fs /binary-fs-dir /.

RUN scone gcc ./binary_fs_blob.s ./libbinary_fs_template.a -shared -o /libbinary-fs.so


# Third stage: patch the binary-fs into the enclave executable
FROM registry.scontain.com:5050/sconecuratedimages/apps:python-3.7.3-alpine3.10

COPY --from=crosscompiler /libbinary-fs.so /lib/libbinary-fs.so

ENV SCONE_EXTENSIONS_PATH="/lib/libbinary-fs.so"


ENV SCONE_HEAP=512M
ENV LD_LIBRARY_PATH="/"

ENV SCONE_LOG="INFO"

ENV PYTHONHOME="/usr"

CMD sh -c "python3 /rest_api.py"
