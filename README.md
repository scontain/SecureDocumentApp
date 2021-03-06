# Confidential Document Manager Application

This application demo is a confidential document web application. This service enables users to upload and download documents and ensures that the documents are always encrypted. Users can create accounts. We use a simple password-based authentication. For production, one should add a two-factor authentication. The application  consists of the following components:

- a **Python FastAPI** service serving as the application's REST API,
- a **MariaDB** service stores the documents and user authentication data,
- a **memcached** service, serving as a rate limiter for the application, and
- an **nginx** instance serves as a proxy server for the application, ensuring termination and forwarding with TLS.

![scone mesh](architecture.png)

All of these components run securely inside of enclaves using the SCONE framework. These services are also integrity protected, and attest each other transparently using TLS in conjunction with a SCONE Configuration and Attestation Service (CAS). Furthermore, the application protects the confidentiality and integrity of all data it receives. We deploy this application using `helm`.

## Building und Running the Application

![scone mesh](scone_gen_app_image.png)

You can get this program to run with the following steps steps:

```bash
./setup.sh # uses persistentVolumeClaims.yaml to create volume claims for MariaDB with the default storage class
# if you want to use a custom storage class, do
# ./setup.sh --custom-storage-class <storage-class-name>
sconectl apply -f clientService.yaml # generates a custom FastAPI client container image
sconectl apply -f service.yaml   # generates a custom FastAPI container image
sconectl apply -f mesh.yaml  # generates/uploads the policies and helm charts
```

## Deploying the application 

The application can be deployed with help as follows:

```bash
helm install secure-doc-management target/helm
```

We put the sconectl and helm steps in script `run.sh`, i.e., you could also just execute `setup.sh` and `run.sh`.

## Cleaning up resources

You can uninstall the application with the following HELM command:

```bash
helm uninstall secure-doc-management
```

Also, to clean up the volumes created, `kubectl` can be used:

```bash
kubectl delete -f persistentVolumeClaims.yaml
```
