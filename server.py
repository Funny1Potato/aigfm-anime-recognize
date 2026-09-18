"""aigfm-anime-recognize —— WD14 二次元角色识别 HTTP 服务

独立部署，供 nonebot-plugin-aigf-master 的「二次元角色识别」功能调用。
单进程；模型单例加载 + 启动预热；推理跑线程池，不阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from tagging import prewarm, tag_characters

# ---------------- 配置（环境变量） ----------------
HOST = os.environ.get("RECOGNIZE_HOST", "0.0.0.0")
PORT = int(os.environ.get("RECOGNIZE_PORT", "8000"))
TOKEN = os.environ.get("RECOGNIZE_TOKEN", "")  # 空 = 不鉴权
CHARACTER_THRESHOLD = float(os.environ.get("RECOGNIZE_CHARACTER_THRESHOLD", "0.85"))
MAX_FILE_BYTES = int(os.environ.get("RECOGNIZE_MAX_FILE_BYTES", str(20 * 1024 * 1024)))
CACHE_TTL = float(os.environ.get("RECOGNIZE_CACHE_TTL", str(24 * 3600)))
WORKERS = max(1, min(8, (os.cpu_count() or 4) // 2))  # 并发 ≈ 物理核心数，保守封顶 8

_executor = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="wd14")
_semaphore = asyncio.Semaphore(WORKERS)
_cache: dict[str, tuple[float, dict]] = {}  # sha256 -> (时间戳, 结果)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger = logging.getLogger("uvicorn.error")
    logger.info("预热中：加载 WD14 模型（首次运行会下载约 446MB，请耐心等待）...")
    await asyncio.get_running_loop().run_in_executor(_executor, prewarm)
    logger.info("预热完成，模型已就绪")
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="aigfm-anime-recognize", lifespan=lifespan)


def _check_auth(authorization: str | None) -> None:
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


def _decode_image(data: bytes) -> bytes:
    """校验图片可解码、限制大小、GIF 取第一帧，返回可喂给模型的 bytes。"""
    if not data:
        raise HTTPException(status_code=400, detail="empty image")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"image too large (>{MAX_FILE_BYTES} bytes)")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image")
    if fmt == "GIF":
        try:
            img.seek(0)
            frame = img.convert("RGB")
            buf = io.BytesIO()
            frame.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid gif")
    return data


@app.get("/health")
async def health():
    return {"status": "ok"}


class RecognizeIn(BaseModel):
    image: str  # base64 编码的图片
    character_threshold: float | None = None  # 覆盖服务端默认阈值


@app.post("/recognize")
async def recognize(
    payload: RecognizeIn | None = None,
    file: UploadFile | None = File(None),
    authorization: str | None = Header(None),
):
    """接收 multipart file 或 JSON base64，返回角色识别结果。"""
    _check_auth(authorization)

    if file is not None:
        data = await file.read()
    elif payload is not None:
        try:
            data = base64.b64decode(payload.image)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid base64")
    else:
        raise HTTPException(status_code=400, detail="need image (multipart file or JSON base64)")

    data = _decode_image(data)
    key = hashlib.sha256(data).hexdigest()

    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    threshold = (
        payload.character_threshold
        if payload and payload.character_threshold
        else CHARACTER_THRESHOLD
    )
    async with _semaphore:
        result = await asyncio.get_running_loop().run_in_executor(
            _executor, tag_characters, data, threshold,
        )

    _cache[key] = (now, result)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
