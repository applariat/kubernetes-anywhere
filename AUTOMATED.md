# Kubernetes Anywhere as a Job

*Run kubernetes-anywhere with env vars*

### Goals and Motivation

This automated version of Kubernetes Anywhere will allow you to run deploy/destroy from a script or a job. The config file will be generated the same way using Kconfig but instead of interactive it will utilize environment variables.

### 

### Config File Creation
The Kubernetes Anywhere project utilizes Kconfig to ask the user questions. This process creates a .config file. That file is used to create .config.json and so on... In order to automate this process ENV vars are used instead. As the Kconfig file tree is traversed the environment is examined for a matching variable. If found, it assigns the value and validates it. The variables in Kconfig have a phase1/2/3 prefix so we strip that off, swap all . with _ and then turn it to upper case. 
If we see the following:
```
menuconfig phase1.cloud_provider
	string "cloud provider: gce, azure or vsphere"
	default "gce"
	help
	  The cloud provider you would like to deploy to.
```
We strip off 'phase1.' and search the env for CLOUD_PROVIDER

Another example:
```
config phase1.gce.project
	string "GCP project"
	help
	  The GCP project to use.
```
We strip off the 'phase1.' and search the env for GCE_PROJECT. In this example there is no default so it will exit if not set. If the Kconfig files change, this code will ask for the new values. The job will continue to parse the files and ENV even after an error. At the end of this process it will exit if there are errors. Either way it prints all Kconfig vars it finds and whether it set a default. An error is prefixed with ERR

Example output:
```
ENV[phase1.num_nodes] NUM_NODES="2" (ok)
ENV[phase1.cluster_name] CLUSTER_NAME="dev-cluster4" (ok)
ENV[phase1.cloud_provider] CLOUD_PROVIDER="gce" (ok)
ENV[phase1.gce.os_image] GCE_OS_IMAGE="ubuntu-1604-xenial-v20160420c" (env var missing, using default)
ENV[phase1.gce.instance_type] GCE_INSTANCE_TYPE="n1-standard-2" (env var missing, using default)
ERR[phase1.gce.project] GCE_PROJECT="" (missing required env var, no default found)
<snip>
```


The result will produce a .config file. The rest of the make process is unaltered.

### Environment Variables
Common required ENV vars:

  * IS_JOB
    - can be set to any value. 
    - If set, the container will run in non-interactive mode.
  * CLUSTER_NAME
  * CLOUD_PROVIDER=[gce|azure|vsphere]

GCE required ENV vars:

  * GCE_PROJECT

Azure required ENV vars:

  * // TODO

vSphere required ENV vars:

  * // TODO

Optional ENV vars:

  * CLOUD_STORAGE
    - can be set to any value. 
    - If set, see Storing the Configs below for more info.
  * DELETE_CLUSTER
    - can be set to any value. 
    - If set, the container will run in destroy mode.
  * KUBEADM_TOKEN
    - If set, the value will be used instead of one being generated.

### Storing the Configs
The container will exit when it completes. There are config and state files on-board that we will need later to destroy the cluster. These files can be stored in kubernetes or in a cloud bucket. To store configs in a cloud bucket, set the CLOUD_STORAGE env var to any value. If it's set, a bucket will be used. If the bucket doesn't exist one will be created for you. The format will be <project_name_here>-k8-anywhere-cluster-data. A folder will be made inside the bucket named ${CLUSTER_NAME} and all the configs will be placed there. This allows multiple cluster configs to be stored in the same bucket.

If CLOUD_STORAGE is not set, a zip file of the configs is stored in kubernetes as a secret in the kube-system namespace.



### Deploy

In order to deploy you must do the following:
* Mount /dropbox or 

export GCE_PROJECT=applariat-dev
export CLUSTER_NAME=chris-cluster5
export CLOUD_PROVIDER=gce
export IS_JOB=y
export NUM_NODES=2
entrypoint.sh deploy
echo KUBECONTROL_JSON=<base64 encoded json>
