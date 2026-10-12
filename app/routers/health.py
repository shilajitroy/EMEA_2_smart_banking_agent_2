from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health", summary="Health check")
@router.get("/health", include_in_schema=False)
def health_check() -> dict[str, object]:
    return {"success": True, "status": "ok"}
