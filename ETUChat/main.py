from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET_KEY = "your-secret-jwt-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

fake_users_db = {
    "alice": {
        "username": "alice",
        "hashed_password": pwd_context.hash("secret"),
    }
}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Cookie(default=None)):
    if token is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    user = fake_users_db.get(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, token: str = Cookie(default=None)):
    user = None
    if token:
        try:
            user = await get_current_user(token)
        except HTTPException:
            user = None
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "msg": ""})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "msg": "用户名或密码错误"})
    access_token = create_access_token(data={"sub": user["username"]},
                                       expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # 把 token 写进 HttpOnly cookie
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        secure=False, samesite="lax")
    return response


@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, token: str = Cookie(default=None)):
    user = None
    if token:
        try:
            user = await get_current_user(token)
        except HTTPException:
            user = None
    return templates.TemplateResponse("about.html", {"request": request, "user": user})


@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "msg": ""})


@app.post("/api/chat-stream")
async def chat_stream(request: Request):
    data = await request.json()
    messages = data.get("messages", [])

    headers = {
        "Authorization": f"Bearer 123",
        "Content-Type": "application/json",
    }
    json_data = {
        "model": "qwen3-32b",
        "messages": messages,
        "stream": True
    }

    async def event_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", "http://127.0.0.1:8005/v1/chat/completions",
                                     headers=headers, json=json_data) as response:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
