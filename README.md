# Airi Voice — Render

## Deploy
1. Taruh `NinaIseri_e200_s11600.pth` di folder `model/` (buat foldernya).
2. Push folder ini (`voice-render/`) sebagai repo GitHub terpisah, atau subfolder
   dengan "Root Directory" di Render diarahkan ke `voice-render`.
3. Di Render: **New +  -> Web Service -> Build from a Dockerfile** (Blueprint `render.yaml` juga bisa dipakai otomatis).
4. Deploy. Endpoint: `https://NAMA-SERVICE.onrender.com/tts`
5. Isi `VOICE_MODEL_URL` di `assets/chat.js` dengan URL itu.

## Hemat RAM — yang sudah diterapkan
- Torch CPU-only (bukan build CUDA) -> paket & RAM jauh lebih kecil.
- Model RVC dimuat lazy saat request pertama, bukan saat server start.
- `torch.set_num_threads(1)` + `OMP_NUM_THREADS=1` -> hindari overhead thread pool.
- Cache audio di `/tmp` dibatasi 60 file terakhir, otomatis dibuang.
- 1 worker Uvicorn saja, supaya model cuma ke-load sekali di memori.

## Catatan jujur
- Plan **Starter (512MB)** Render mungkin masih kurang untuk torch + model RVC;
  kalau servicenya crash/OOM pas request pertama, naikkan ke plan **Standard (2GB)**.
- Plan gratis/murah Render "sleep" kalau idle lama -> request pertama setelah
  bangun bisa 30-60 detik (cold start + lazy load model). `chat.js` sudah
  dikasih timeout lebih panjang untuk jalur ini dan otomatis jatuh ke suara
  cadangan (MeloTTS lewat Cloudflare Worker) kalau Render belum siap.
