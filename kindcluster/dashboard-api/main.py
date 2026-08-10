from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

app = FastAPI(
    title="Kubernetes Rollout Dashboard API",
    version="1.0.0",
)

# This allows a future frontend running on another local port
# to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_apps_api() -> client.AppsV1Api:
    """
    Load the same kubeconfig and current context used by kubectl.
    """
    try:
        config.load_kube_config()
        return client.AppsV1Api()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load Kubernetes configuration: {exc}",
        ) from exc


def determine_status(
    desired: int,
    ready: int,
    available: int,
    updated: int,
) -> str:
    if desired == 0:
        return "ScaledDown"

    if ready == desired and available == desired and updated == desired:
        return "Healthy"

    if updated < desired or ready < desired:
        return "Progressing"

    return "Degraded"


def serialize_deployment(deployment: Any) -> dict[str, Any]:
    desired = deployment.spec.replicas or 0
    ready = deployment.status.ready_replicas or 0
    available = deployment.status.available_replicas or 0
    updated = deployment.status.updated_replicas or 0
    unavailable = deployment.status.unavailable_replicas or 0

    containers = deployment.spec.template.spec.containers
    images = [container.image for container in containers]

    return {
        "name": deployment.metadata.name,
        "namespace": deployment.metadata.namespace,
        "desiredReplicas": desired,
        "readyReplicas": ready,
        "availableReplicas": available,
        "updatedReplicas": updated,
        "unavailableReplicas": unavailable,
        "images": images,
        "status": determine_status(
            desired=desired,
            ready=ready,
            available=available,
            updated=updated,
        ),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Kubernetes Rollout Dashboard API",
        "documentation": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "up"}


@app.get("/api/deployments")
def list_deployments(
    namespace: str | None = Query(
        default=None,
        description="Optional Kubernetes namespace",
    ),
) -> dict[str, Any]:
    apps_api = get_apps_api()

    try:
        if namespace:
            response = apps_api.list_namespaced_deployment(
                namespace=namespace
            )
        else:
            response = apps_api.list_deployment_for_all_namespaces()

        deployments = [
            serialize_deployment(deployment)
            for deployment in response.items
        ]

        return {
            "count": len(deployments),
            "namespace": namespace or "all",
            "deployments": deployments,
        }

    except ApiException as exc:
        raise HTTPException(
            status_code=exc.status or 500,
            detail=f"Kubernetes API error: {exc.reason}",
        ) from exc


@app.get("/api/deployments/{namespace}/{deployment_name}")
def get_deployment(
    namespace: str,
    deployment_name: str,
) -> dict[str, Any]:
    apps_api = get_apps_api()

    try:
        deployment = apps_api.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
        )
        return serialize_deployment(deployment)

    except ApiException as exc:
        if exc.status == 404:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Deployment '{deployment_name}' was not found "
                    f"in namespace '{namespace}'."
                ),
            ) from exc

        raise HTTPException(
            status_code=exc.status or 500,
            detail=f"Kubernetes API error: {exc.reason}",
        ) from exc