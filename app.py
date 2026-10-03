"""Server suara Airi (Render, hemat RAM).
- Torch build CPU-only (lewat requirements.txt) -> jauh lebih kecil & hemat RAM
  dibanding build CUDA (gak perlu GPU di Render gratis/standard).
- Model RVC (.pth) baru dimuat saat request /tts PERTAMA kali (lazy load),
  bukan saat server start -> idle RAM rendah, nyala lebih cepat buat health check.
- 1 thread torch saja -> hindari overhead thread pool yang makan RAM.
"""
import os, asyncio, hashlib, gc
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import torch
torch.set_num_threads(1)

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

MODEL_PATH = os.environ.get("MODEL_PATH", "model/NinaIseri_e200_s11600.pth")
BASE_VOICE = "ja-JP-NanamiNeural"
CACHE_DIR = "/tmp/cache"          # /tmp = disk sementara Render, aman & gak numpuk di repo
CACHE_MAX_ITEMS = 60              # batasi cache biar disk/RAM gak membengkak

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
os.makedirs(CACHE_DIR, exist_ok=True)

_rvc = None
def get_rvc():
    global _rvc
    if _rvc is None:
        from rvc_python.infer import RVCInference
        _rvc = RVCInference(device="cpu")
        _rvc.load_model(MODEL_PATH)
    return _rvc

def trim_cache():
    files = sorted(
        (os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)),
        key=os.path.getmtime
    )
    for f in files[:-CACHE_MAX_ITEMS]:
        try: os.remove(f)
        except OSError: pass

class Req(BaseModel):
    text: str

@app.get("/")
async def health():
    return {"ok": True, "model_loaded": _rvc is not None}

@app.post("/tts")
async def tts(r: Req):
    text = r.text.strip()
    if not text or len(text) > 200:
        raise HTTPException(400, "Teks kosong atau terlalu panjang")
    key = hashlib.sha1(text.encode()).hexdigest()
    wav, mp3 = f"{CACHE_DIR}/{key}.wav", f"{CACHE_DIR}/{key}.mp3"
    if not os.path.exists(wav):
        await edge_tts.Communicate(text, BASE_VOICE).save(mp3)
        rvc = get_rvc()
        with torch.inference_mode():
            await asyncio.to_thread(rvc.infer_file, mp3, wav)
        gc.collect()
        trim_cache()
    return FileResponse(wav, media_type="audio/wav")
