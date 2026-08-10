from fastapi import APIRouter

router = APIRouter(prefix="/v1/workers", tags=["workers"])


@router.get("")
def list_workers():
    # Heartbeats are deliberately left as the next feature.
    return {
        "workers": [],
        "note": "Add worker heartbeat storage in the next iteration."
    }
