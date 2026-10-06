from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.post("/upload")
async def upload_transactions(
    file: UploadFile = File(...)
):
    return {
        "message": "Upload endpoint working",
        "filename": file.filename
    }