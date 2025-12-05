"""
音频文件处理 API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/audio", tags=["audio"])

# 上传目录
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    上传音频文件
    
    Args:
        file: 音频文件
    
    Returns:
        文件信息
    """
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = Path(file.filename).suffix
        new_filename = f"{timestamp}_{unique_id}{file_extension}"
        
        file_path = UPLOAD_DIR / new_filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "filename": new_filename,
            "filepath": str(file_path),
            "size": len(content)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
