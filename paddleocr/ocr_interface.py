import uvicorn
import io
import os
import uuid
import cv2
from PIL import Image
from fastapi import FastAPI, Body, UploadFile, Form
from paddleocr import PaddleOCR, draw_ocr, PPStructure, draw_structure_result, save_structure_res
import fitz

app = FastAPI()
OCR_MODEL = None
TABLE_ENGINE = None
inited = False


def load_module():
    global OCR_MODEL
    global TABLE_ENGINE
    global inited
    if inited == False:
        print("Loading model... ")
        OCR_MODEL = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=True)
        TABLE_ENGINE = PPStructure()
        inited = True
    return OCR_MODEL, TABLE_ENGINE


MAX_INPUT_LENGTH = 8 * 1024
ALPHA = 0.9


def extract_text(obj):
    """
    递归提取 OCR 结果中的文本
    obj 可以是：
    - str: 直接返回
    - list/tuple: 遍历每个元素递归提取
    - dict: 遍历值递归提取
    """
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, (list, tuple)):
        return " ".join(extract_text(o) for o in obj if o is not None)
    elif isinstance(obj, dict):
        return " ".join(extract_text(v) for v in obj.values() if v is not None)
    else:
        # 其他类型，直接转字符串
        return str(obj)


@app.get("/")
def read_root():
    return {"Hello"}


@app.post("/ocr_pdf_text")
async def ocr_pdf_text(file: UploadFile):
    model, _ = load_module()
    local_pdf_path = f"/root/ocr/{str(uuid.uuid4())}.pdf"
    try:
        data = await file.read()
        with open(local_pdf_path, "wb") as f:
            f.write(data)

        import fitz
        pdf_doc = fitz.open(local_pdf_path)
        results = []

        for page_index in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_index)
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            local_img_path = f"/root/ocr/{str(uuid.uuid4())}.png"
            with open(local_img_path, "wb") as f:
                f.write(img_data)

            ocr_result = model.ocr(local_img_path, cls=True)
            text_list = [extract_text(line[1]) for line in ocr_result]

            results.append({"page": page_index + 1, "text": "\n".join(text_list)})
            os.remove(local_img_path)

        return {"pages": len(pdf_doc), "results": results}
    finally:
        os.remove(local_pdf_path)


@app.post("/ocr_pdf")
async def ocr_pdf(file: UploadFile):
    """
    接收 PDF 文件，将每一页转换为图片，并使用 OCR 解析。
    返回每页的 OCR 结果列表。
    """
    model, useless_model = load_module()
    local_pdf_path = f"/root/ocr/{str(uuid.uuid4())}.pdf"
    images = []

    try:
        # 保存 PDF 文件
        data = await file.read()
        with open(local_pdf_path, 'wb') as f:
            f.write(data)

        # 打开 PDF
        pdf_doc = fitz.open(local_pdf_path)
        results = []

        for page_index in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_index)
            pix = page.get_pixmap()  # 默认 dpi=72
            img_data = pix.tobytes("png")

            # 临时保存图片
            local_img_path = f"/root/ocr/{str(uuid.uuid4())}.png"
            with open(local_img_path, "wb") as f:
                f.write(img_data)

            # OCR 解析
            page_result = model.ocr(local_img_path, cls=True)
            results.append({"page": page_index + 1, "ocr_result": page_result})

            os.remove(local_img_path)  # 删除临时图片

        return {"response": results}

    finally:
        os.remove(local_pdf_path)


@app.post("/structure")
async def structure(file: UploadFile):
    useless_model, model = load_module()
    local_path = f"/root/ocr/{str(uuid.uuid4())}.png"
    try:
        data = await file.read()
        image = Image.open(io.BytesIO(data))
        with open(local_path, 'wb') as f:
            image.save(f, format='PNG')
        img = cv2.imread(local_path)
        result = model(img, return_ocr_result_in_table=True)
        for line in result:
            line.pop('img')
        return {"response": result}
    finally:
        os.remove(local_path)


@app.post("/ocr")
async def ocr(file: UploadFile):
    model, useless_model = load_module()
    local_path = f"/root/ocr/{str(uuid.uuid4())}.png"
    try:
        data = await file.read()
        image = Image.open(io.BytesIO(data))
        with open(local_path, 'wb') as f:
            image.save(f, format='PNG')
        result = model.ocr(local_path, cls=True)
        return {"response": result}
    finally:
        os.remove(local_path)


if __name__ == "__main__":
    try:
        load_module()
    except Exception as e:
        print(e)
    uvicorn.run(app, host="0.0.0.0", port=3000, workers=1)