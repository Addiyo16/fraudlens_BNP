from fastapi import APIRouter

router = APIRouter()


@router.get("/flags")
def get_flags():
    return {
        "message": "GET /flags working"
    }


@router.patch("/flags/{flag_id}")
def update_flag(flag_id: int):
    return {
        "message": "PATCH /flags/{id} working",
        "flag_id": flag_id
    }