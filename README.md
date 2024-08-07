# Confidential Document Manager Application

## TL'DR

```bash
export SCONECTL_REPO=registry.scontain.com/cicd # default is registry.scontain.com/sconectl
export VERSION=5.8.0  # default version is "latest".
export CAS="cas" # set the name of the CAS instance that we should used; default is "cas"
export CAS_NAMESPACE="scone-system" # set the Kubernetes namespace of the CAS instance that we should used; default is "default"
# if you want to use the latest stable release, ensure that these variables are not set:
unset SCONECTL_REPO
unset VERSION
# cleanup the last state
rm -rf release.sh target
# define REPO to which you are # define REPO to which you are permitted to push container images
REPO="<YOUR-REPO>"
# execute all steps of this tutorial
./run.sh -i "$REPO" --release secure-doc-management -v
```

## Introduction

This application demo is a confidential document web application. This service enables users to upload and download documents and ensures that the documents are always encrypted. Users can create accounts. We use a simple password-based authentication. For production, one should add a two-factor authentication. The application  consists of the following components:

- a **Python FastAPI** service serving as the application's REST API,
- a **MariaDB** service stores the documents and user authentication data,
- a **memcached** service, serving as a rate limiter for the application, and
- an **nginx** instance serves as a proxy server for the application, ensuring termination and forwarding with TLS.

![scone mesh](architecture.png)

All of these components run securely inside of enclaves using the SCONE framework. These services are also integrity protected, and attest each other transparently using TLS in conjunction with a SCONE Configuration and Attestation Service (CAS). Furthermore, the application protects the confidentiality and integrity of all data it receives. We deploy this application using `helm`.

## Set up Azure Cluster (optional)

In case you want to run this demo in an Azure cluster, you may consider the following commands to set up a cluster, using the  [Azure CLI](https://learn.microsoft.com/pt-br/cli/azure/install-azure-cli-linux?source=recommendations&pivots=apt).

```bash
# Export cluster configs
export NUMBER_OF_CONFIDENTIAL_NODES=1
export CLUSTER_NAME="aks-scone-cluster"
export NODE_POOL_NAME="aksnodepool"
export RESOURCE_GROUP="<RESOURCE_GROUP_NAME>"
export NODE_FLAVOR="Standard_DC4s_v3"
 
# Create cluster
az aks create --name $CLUSTER_NAME --generate-ssh-keys --enable-addons confcom -c $NUMBER_OF_CONFIDENTIAL_NODES --node-vm-size $NODE_FLAVOR -g $RESOURCE_GROUP

# Get kubeconfig
az aks get-credentials --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP  -f $CLUSTER_NAME
```

## Building and running the application

No time to read all the steps? We put the sconectl and helm steps in script `run.sh`. Just execute `./run.sh` and have a happy sconification!

![scone mesh](scone_gen_app_image.png)

You can get this program to run with the following steps.

### Installing SCONE operator, its dependencies, and CAS

If you have a clean K8s cluster, you need to install the SCONE operator. CAS is also needed for attesting the SecureDocumentApp components. To install everything, assuming you are in the `default` k8s namespace, do:

1. Install operator, LAS, and SGXPlugin

```bash
curl -fsSL https://raw.githubusercontent.com/scontain/SH/master/operator_controller | bash -s - --set-version 5.8.0 --plugin --reconcile --update --secret-operator --verbose --username $REGISTRY_USERNAME --access-token $REGISTRY_ACCESS_TOKEN  --email $REGISTRY_EMAIL
```

2. `operator_controller` will create the `scone-system` namespace. Check the pods in `scone-system` with

```bash
kubectl get pods -n scone-system
```

3. Once everything in `scone-system` is running and ready (check output of previous command), we can install CAS and provision using the `kubectl-provision` script.

```bash
kubectl provision cas cas --set-version 5.8.0 --verbose
```

4. Check that CAS is HEALTHY before you continue to next steps.

```bash
kubectl get cas.services.scone.cloud cas
```

Once CAS is HEALTHY, you're ready to go.

### Make sure that your local machine meet all requirements

1. Export APP_IMAGE_REPO to point to some registry you have read and write access permissions.

```bash
export APP_IMAGE_REPO=example.registry.com
```

2. Set the `sconectl` version to the `5.8.0` stable version.

```bash
export VERSION=5.8.0
```

3. Run the `check_prerequisites.sh` script. It will check things like the SCONE CRDs in your K8s cluster and your access to the SCONE registry.

```bash
./check_prerequisites.sh
```

### Sconify the FastAPI service and the Client Service with `sconectl` `genservice` kind

1. Create `service.yaml` using the `service.yaml.template` template. This YAML will describe your confidential FastAPI service. Do the same thing with the `clientService.yaml.template` template to create the `clientService.yaml` describing the client.

```bash
SCONE="\$SCONE" envsubst < service.yaml.template > service.yaml
SCONE="\$SCONE" envsubst < clientService.yaml.template > clientService.yaml
```

2. Run `sconectl` with `service.yaml` and `clientService.yaml` to create the confidential services (also known as SCONE elements in the context of SCONE meshes).

```
sconectl apply -f service.yaml
sconectl apply -f clientService.yaml
```

3. Get the information about the CAS deployed in your K8s cluster using the SCONE plugin for `kubectl`. Check if `$CAS_SERVICE` and `$CAS_NAMESPACE` are not empty. If these variables are empty after the following commands, then your CAS is not healthy and you cannot continue. The CAS installation needs to be fixed in this case.

```bash
export CAS_SERVICE=`kubectl get cas --all-namespaces | grep HEALTHY | awk '{print $2}'`
export CAS_NAMESPACE=`kubectl get cas --all-namespaces | grep HEALTHY | awk '{print $1}'`
source <(kubectl provision cas $CAS_SERVICE -n $CAS_NAMESPACE --print-public-keys)
```

4. Create a meshfile using the `mesh.yaml.template` file. This `mesh.yaml` will describe the SCONE mesh that deploys the SecureDocumentApp application with all of its confidential components.

```bash
export RELEASE=secure-doc-management
export APP_NAMESPACE="$RELEASE-$RANDOM-$RANDOM"
export CAS_URL="$CAS_SERVICE.$CAS_NAMESPACE"
SCONE="\$SCONE" envsubst < mesh.yaml.template > mesh.yaml
```

5. Use `sconectl` again to create the SCONE mesh. The following command will upload the security policies for the SecureDocumentApp. It also creates the Helm chart that we use to deploy the application. Besides that, define the release name for the Helm installation.

```bash
sconectl apply -f mesh.yaml --release "$RELEASE"
```

6. Deploy the app with the Helm chart generated by `sconectl`.

```bash
helm install "$RELEASE" target/helm/
```

## Cleaning up resources

You can uninstall the application with the following command:

```bash
helm uninstall "$RELEASE"
```