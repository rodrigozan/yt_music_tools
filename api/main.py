import shutil
import os
import glob
import asyncio
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses 
import FileResponse, JSONResponse
from fastapi.middleware.cors 
import CORSMiddleware
import Security, HTTPException, status, Depends
from fastapi.security
import HTTPBearer, HTTPAuthorizationCredentials
import os
import yt_dlp
import ffmpeg

app = FastAPI(title="YT Music Tools API")

# Configurar CORS (para seu frontend Angular/Ionic poder chamar)
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

# --- FUNÇÕES CORE (Lógica do Script Anterior) ---

def processar_video_background(video_path: str, urls: List[str], job_id: str):
    """
    Esta função roda em background. Baixa áudios, junta e renderiza.
    """
    print(f"[{job_id}] Iniciando processamento...")
    output_filename = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")
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
        # Nota: yt-dlp adiciona a extensão .mp3 automaticamente
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
        # Limpeza: Remove arquivos temporários de áudio e o vídeo de upload original
        files = glob.glob(os.path.join(TEMP_DIR, f"{job_id}_audio_*"))
        for f in files:
            os.remove(f)
        if os.path.exists(video_path):
            os.remove(video_path)

# --- ENDPOINTS ---

@app.post("/create-music")
async def create_music(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    urls: str = Form(...) # Recebe string separada por vírgulas ou JSON string
):
    """
    Recebe um vídeo (MP4) e uma lista de URLs do YouTube (separadas por vírgula).
    """
    job_id = f"job_{os.urandom(4).hex()}"
    video_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    
    # Salvar o arquivo de vídeo enviado
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Processar lista de URLs (quebra a string por vírgula)
    lista_urls = [url.strip() for url in urls.split(",") if url.strip()]

    # Adicionar tarefa em background (não trava a resposta da API)
    background_tasks.add_task(processar_video_background, video_path, lista_urls, job_id)

    return {
        "message": "Processamento iniciado.",
        "job_id": job_id,
        "info": "O vídeo estará disponível em breve no endpoint /download"
    }

@app.get("/videos")
def listar_videos():
    """Lista os vídeos prontos na pasta de saída."""
    files = os.listdir(OUTPUT_DIR)
    return {"videos": files}

@app.get("/download/{filename}")
def download_video(filename: str):
    """Baixa um vídeo processado."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    return JSONResponse(status_code=404, content={"message": "Arquivo não encontrado"})

# Se rodar direto pelo python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
