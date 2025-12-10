"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Music, Zap, Video, Download, CheckCircle, Loader2, History, RefreshCw, AlertCircle } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

// CONFIGURAÇÃO
const API_URL = "https://ytmusictools.smartutilitybox.com"; 
const API_TOKEN = "RDZ2003RDYA20232025"; 

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [urls, setUrls] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [jobHistory, setJobHistory] = useState<any[]>([]);

  // Carrega histórico ao abrir
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_URL}/jobs`, {
        headers: { Authorization: `Bearer ${API_TOKEN}` }
      });
      setJobHistory(res.data.jobs);
    } catch (error) {
      console.error("Erro ao carregar histórico", error);
    }
  };

  const pollStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${API_TOKEN}` }
        });
        
        const status = res.data.status;
        
        if (status === 'completed') {
          clearInterval(interval);
          setLoading(false);
          setStatusMessage("Concluído!");
          fetchHistory(); // Atualiza a lista lá embaixo
          // Opcional: Auto-download ou alerta
          alert("Seu vídeo ficou pronto! Confira na lista de histórico.");
        } else if (status === 'failed') {
          clearInterval(interval);
          setLoading(false);
          alert("Ocorreu um erro no processamento do vídeo.");
        } else {
          setStatusMessage("Processando áudio e vídeo... Isso pode levar alguns minutos.");
        }
      } catch (e) {
        console.error("Erro no polling", e);
      }
    }, 3000); // Checa a cada 3 segundos
  };

  const handleGenerate = async () => {
    if (!file || !urls) return alert("Por favor, preencha tudo!");

    setLoading(true);
    setStatusMessage("Enviando arquivos...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("urls", urls);

    try {
      const res = await axios.post(`${API_URL}/create-music`, formData, {
        headers: { 
          "Content-Type": "multipart/form-data",
          "Authorization": `Bearer ${API_TOKEN}`
        },
      });

      const { job_id } = res.data;
      setStatusMessage("Job criado. Aguardando processamento...");
      pollStatus(job_id); // Inicia a verificação real

    } catch (error) {
      console.error(error);
      alert("Erro ao conectar com a API.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center py-10 px-4 relative overflow-y-auto">
      
      {/* Background Decor */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px] pointer-events-none" />
      
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl w-full z-10 space-y-8">
        
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
            Lofi Maker
          </h1>
          <p className="text-zinc-400">Crie loops infinitos com suas playlists.</p>
        </div>

        {/* Card de Criação */}
        <Card className="bg-zinc-900/50 border-white/10 backdrop-blur-md">
          <CardContent className="p-6 space-y-6">
            
            <div className="space-y-3">
              <label className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                <Video className="w-4 h-4 text-purple-400" /> Vídeo de Fundo (Loop)
              </label>
              <div className="relative">
                <input type="file" accept="video/mp4" onChange={(e) => setFile(e.target.files?.[0] || null)} className="hidden" id="video-upload" />
                <label htmlFor="video-upload" className={`block w-full p-4 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors ${file ? 'border-green-500/50 bg-green-500/10' : 'border-zinc-700 hover:border-purple-500'}`}>
                  {file ? <span className="text-green-400 font-semibold">{file.name}</span> : <span className="text-zinc-500">Clique para selecionar MP4</span>}
                </label>
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                <Music className="w-4 h-4 text-blue-400" /> Links do YouTube
              </label>
              <Input placeholder="Separe os links por vírgula..." className="bg-zinc-950/50 border-zinc-700 text-zinc-100" value={urls} onChange={(e) => setUrls(e.target.value)} />
            </div>

            <Button onClick={handleGenerate} disabled={loading || !file || !urls} className="w-full bg-purple-600 hover:bg-purple-700 h-12 text-lg">
              {loading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Processando...</> : <><Zap className="mr-2 h-5 w-5" /> Iniciar Criação</>}
            </Button>

            {loading && (
              <div className="space-y-2 pt-2">
                <Progress value={100} className="h-1 bg-zinc-800" indicatorClassName="bg-purple-500 animate-pulse w-full" />
                <p className="text-xs text-center text-zinc-400 animate-pulse">{statusMessage}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Lista de Histórico */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-xl font-semibold flex items-center gap-2"><History className="w-5 h-5" /> Histórico de Vídeos</h2>
            <Button variant="ghost" size="sm" onClick={fetchHistory}><RefreshCw className="w-4 h-4" /></Button>
          </div>

          <div className="grid gap-3">
            {jobHistory.length === 0 && <p className="text-center text-zinc-600 py-8">Nenhum vídeo criado ainda.</p>}
            
            {jobHistory.map((job) => (
              <Card key={job.id} className="bg-zinc-900/30 border-white/5 hover:bg-zinc-900/50 transition-colors">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="overflow-hidden">
                    <p className="font-medium text-zinc-200 truncate">{job.filename || job.video_input || "Vídeo sem nome"}</p>
                    <div className="flex items-center gap-2 text-xs mt-1">
                      <span className={`px-2 py-0.5 rounded-full ${
                        job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        job.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400 animate-pulse'
                      }`}>
                        {job.status === 'completed' ? 'Pronto' : job.status === 'failed' ? 'Erro' : 'Processando...'}
                      </span>
                      <span className="text-zinc-600">{new Date(job.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {job.status === 'completed' ? (
                    <Button asChild size="sm" variant="outline" className="border-green-900/50 hover:bg-green-900/20 text-green-400">
                      <a href={`${API_URL}/download/${job.filename}`} target="_blank">
                        <Download className="w-4 h-4 mr-2" /> Baixar
                      </a>
                    </Button>
                  ) : job.status === 'failed' ? (
                    <AlertCircle className="text-red-500 w-5 h-5" />
                  ) : (
                    <Loader2 className="text-yellow-500 w-5 h-5 animate-spin" />
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

      </motion.div>
    </div>
  );
}