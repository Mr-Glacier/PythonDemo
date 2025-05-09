import uvicorn
import io
import os
import uuid
import cv2
from PIL import Image
from fastapi import FastAPI, Body, UploadFile, Form
from paddleocr import PaddleOCR, draw_ocr, PPStructure, draw_structure_result, save_structure_res

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
        OCR_MODEL = PaddleOCR(use_angle_cls=True, lang="ch")
        TABLE_ENGINE = PPStructure()
        inited = True
    return OCR_MODEL, TABLE_ENGINE


MAX_INPUT_LENGTH = 8 * 1024
ALPHA = 0.9


@app.get("/")
def read_root():
    return {"Hello"}


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
