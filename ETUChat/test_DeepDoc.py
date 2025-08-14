from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import shutil
import os

# 引入你的 DeepDocEngine
from DeepDocEngine import DeepDocEngine  # 改成你保存的模块名

app = FastAPI(title="DeepDocEngine 文件解析 API")

# 创建 DeepDocEngine 实例
engine = DeepDocEngine()

# 临时文件存储路径
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/parse_file")
async def parse_file(file: UploadFile = File(...)):
    """
    上传文件并解析
    支持格式: PDF, DOCX, PPTX, XLSX, TXT, JSON, CSV, YAML, HTML/XML, MD
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # 保存上传文件到本地
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 调用 DeepDocEngine 解析
        result = engine.parse(file_path)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    finally:
        # 可选：解析后删除临时文件
        os.remove(file_path)

    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
