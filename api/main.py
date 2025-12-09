import shutil
import os
import glob
import asyncio
from typing import List

# Importações do FastAPI e Segurança corrigidas
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Security, HTTPException, status, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Bibliotecas externas
import yt_dlp
import ffmpeg

app = FastAPI(title="YT Music Tools API")

# --- SEGURANÇA ---
security = HTTPBearer()

# Pega a senha das variáveis de ambiente (definidas no systemd)
# Se não encontrar, usa uma senha padrão de aviso
API_SECRET_TOKEN = os.getenv("API_TOKEN", "senha-padrao-insegura")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Valida se o token enviado no cabeçalho Authorization bate com a nossa senha."""
    token = credentials.credentials
    if token != API_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# --- CONFIGURAÇÃO CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÕES DE DIRETÓRIOS ---
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
TEMP_DIR = "temp"

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# --- FUNÇÕES CORE (Lógica de Processamento) ---

def processar_video_background(video_path: str, urls: List[str], job_id: str):
    """
    Esta função roda em background. Baixa áudios, junta e renderiza.
    """
    print(f"[{job_id}] Iniciando processamento...")
    output_filename = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")
    # Ajuste no template para evitar conflito de nomes
    temp_audio_pattern = os.path.join(TEMP_DIR, f"{job_id}_audio_%(autonumber)s")

    try:
        # 1. Baixar Áudios
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'outtmpl': temp_audio_pattern,
            'quiet': True
        }
        
        print(f"[{job_id}] Baixando {len(urls)} músicas...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)

        # Listar arquivos baixados para este job
        audios = sorted(glob.glob(os.path.join(TEMP_DIR, f"{job_id}_audio_*.mp3")))

        if not audios:
            print(f"[{job_id}] Erro: Nenhum áudio baixado.")
            return

        # 2. Manipulação FFmpeg
        inputs_audio = [ffmpeg.input(audio) for audio in audios]
        
        # Concatena áudios se houver mais de um
        if len(inputs_audio) > 1:
            audio_stream = ffmpeg.concat(*inputs_audio, v=0, a=1).node[0]
        else:
            audio_stream = inputs_audio[0]

        # Configura vídeo em loop
        video_input = ffmpeg.input(video_path, stream_loop=-1)

        print(f"[{job_id}] Renderizando vídeo final...")
        (
            ffmpeg
            .output(video_input.v, audio_stream, output_filename, shortest=None, vcodec='libx264', acodec='aac')
            .global_args('-shortest') 
            .overwrite_output()
            .run(quiet=True)
        )
        
        print(f"[{job_id}] Concluído! Salvo em: {output_filename}")

    except Exception as e:
        print(f"[{job_id}] ERRO FATAL: {str(e)}")
    
    finally:
        # Limpeza
        files = glob.glob(os.path.join(TEMP_DIR, f"{job_id}_audio_*"))
        for f in files:
            try: os.remove(f)
            except: pass
        if os.path.exists(video_path):
            try: os.remove(video_path)
            except: pass

# --- ENDPOINTS ---

# Rota PROTEGIDA (exige token)
@app.post("/create-music", dependencies=[Depends(verify_token)])
async def create_music(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    urls: str = Form(...) 
):
    job_id = f"job_{os.urandom(4).hex()}"
    video_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    lista_urls = [url.strip() for url in urls.split(",") if url.strip()]

    background_tasks.add_task(processar_video_background, video_path, lista_urls, job_id)

    return {
        "message": "Processamento iniciado.",
        "job_id": job_id,
        "info": "O vídeo estará disponível em breve no endpoint /download"
    }

# Rota PROTEGIDA (exige token)
@app.get("/videos", dependencies=[Depends(verify_token)])
def listar_videos():
    files = os.listdir(OUTPUT_DIR)
    return {"videos": files}

# Rota ABERTA (Download não exige token para facilitar acesso direto no browser)
@app.get("/download/{filename}")
def download_video(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    return JSONResponse(status_code=404, content={"message": "Arquivo não encontrado"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
