from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Public health-check endpoint.
    Flutter can call this to verify the backend is reachable before making
    authenticated requests.
    """
    return {"status": "ok", "project": "rscommendation-493408"}
