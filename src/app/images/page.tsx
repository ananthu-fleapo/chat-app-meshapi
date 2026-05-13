"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "@/components/layout/Sidebar";
import { useModels } from "@/hooks/useModels";
import type { ImageGenerationRequest, ImageGenerationResponse, ImageChunkResponse } from "@/lib/types";

const SIZE_OPTIONS = ["1024x1024", "1536x864", "864x1536", "512x512", "1:1", "16:9", "9:16", "3:4", "4:3"];
const QUALITY_OPTIONS = ["auto", "low", "medium", "high"];
const FORMAT_OPTIONS = ["png", "jpeg", "webp"];

export default function ImageGenerationPage() {
  const { data: models } = useModels();
  const [prompt, setPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("openai/gpt-image-2");
  const [numImages, setNumImages] = useState(1);
  const [size, setSize] = useState("1024x1024");
  const [quality, setQuality] = useState("auto");
  const [format, setFormat] = useState("png");
  const [compression, setCompression] = useState(80);
  const [stream, setStream] = useState(true);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImages, setGeneratedImages] = useState<Array<{ url: string; prompt: string; id: string }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);

  const showToast = (message: string, type: "error" | "success" = "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  // Filter for image models or add defaults
  const imageModels = models?.filter(m => 
    m.id.includes("image") || 
    m.id.includes("imagen") || 
    m.id.includes("dall-e")
  ) ?? [];

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setError(null);
    setStatus("Initiating generation...");
    
    const requestBody: ImageGenerationRequest = {
      prompt,
      model: selectedModel,
      n: numImages,
      size,
      quality: quality as any,
      output_format: format as any,
      stream,
    };

    // Only include compression for lossy formats
    if (format === "jpeg" || format === "webp") {
      requestBody.output_compression = compression;
    }

    console.log("Starting image generation with body:", requestBody);

    try {
      const response = await fetch("/api/images/generations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      console.log("Response status from /api/images/generations:", response.status);

      if (!response.ok) {
        const err = await response.json();
        console.error("Error response from server:", err);
        const msg = err.error?.message || err.error || "Failed to generate image";
        showToast(msg);
        throw new Error(msg);
      }

      if (stream) {
        console.log("Starting stream reader...");
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        if (!reader) throw new Error("No response body");

        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log("Stream reader done");
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? ""; // Keep the last partial part in the buffer

          for (const part of parts) {
            const lines = part.split("\n");
            for (const line of lines) {
              if (line.startsWith(": ping")) {
                console.log("Received ping from stream");
                setStatus("Processing... (still working)");
                continue;
              }
              if (!line.startsWith("data: ")) continue;
              const data = line.slice(6);
              if (data === "[DONE]") {
                console.log("Received [DONE] from stream");
                break;
              }

              try {
                const parsed = JSON.parse(data);
                console.log("Parsed stream data:", parsed);

                if (parsed.error) {
                  const msg = parsed.error.message || parsed.error;
                  showToast(msg);
                  setError(msg);
                  break;
                }

                if (parsed.status === "processing") {
                  setStatus("Generating image...");
                } else if (parsed.data) {
                  console.log("Received image data in stream:", parsed.data);
                  const newImages = parsed.data
                    .filter((d: any) => d.url || d.b64_json)
                    .map((d: any) => ({
                      url: d.url || `data:image/${format};base64,${d.b64_json}`,
                      prompt,
                      format,
                      id: Math.random().toString(36).substring(7)
                    }));
                  setGeneratedImages(prev => [...newImages, ...prev]);
                  setStatus(null);
                }
              } catch (e) {
                console.error("Error parsing stream chunk", e, "Data length:", data.length);
              }
            }
          }
        }
      } else {
        const data = await response.json() as any;
        console.log("Received JSON response data:", data);
        
        if (data.error) {
          const msg = data.error.message || data.error;
          showToast(msg);
          throw new Error(msg);
        }

        if (data.data) {
          const newImages = data.data
            .filter((d: any) => d.url || d.b64_json)
            .map((d: any) => ({
              url: d.url || `data:image/${format};base64,${d.b64_json}`,
              prompt,
              format,
              id: Math.random().toString(36).substring(7)
            }));
          setGeneratedImages(prev => [...newImages, ...prev]);
        }
        setStatus(null);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred";
      setError(msg);
      setStatus(null);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 relative">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-50 rounded-xl">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 leading-tight">Image Generator</h1>
              <p className="text-xs text-gray-500">Create stunning visuals with RouterV</p>
            </div>
          </div>
        </header>

        <main className="flex flex-1 overflow-hidden">
          {/* Settings Sidebar */}
          <aside className="w-80 bg-white border-r border-gray-100 overflow-y-auto p-6 space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="A futuristic city with neon lights and flying cars..."
                className="w-full h-32 px-4 py-3 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all resize-none"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Model</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all appearance-none cursor-pointer"
              >
                <option value="openai/gpt-image-2">GPT Image 2 (OpenAI)</option>
                <option value="imagen-3">Imagen 3 (Vertex AI)</option>
                {imageModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Size</label>
                <select
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all appearance-none cursor-pointer"
                >
                  {SIZE_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Images (n)</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={numImages}
                  onChange={(e) => setNumImages(parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Quality</label>
                <select
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all appearance-none cursor-pointer"
                >
                  {QUALITY_OPTIONS.map(q => <option key={q} value={q}>{q}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all appearance-none cursor-pointer"
                >
                  {FORMAT_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
            </div>

            <AnimatePresence>
              {(format === "jpeg" || format === "webp") && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 overflow-hidden"
                >
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Compression</label>
                    <span className="text-xs font-medium text-purple-600">{compression}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={compression}
                    onChange={(e) => setCompression(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-purple-600"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">Streaming</label>
                <button
                  onClick={() => setStream(!stream)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${stream ? "bg-purple-600" : "bg-gray-200"}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${stream ? "translate-x-6" : "translate-x-1"}`} />
                </button>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all shadow-lg shadow-purple-200 flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12h14" />
                      <path d="M12 5l7 7-7 7" />
                    </svg>
                    <span>Generate</span>
                  </>
                )}
              </button>
            </div>

            {error && (
              <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
                {error}
              </div>
            )}
          </aside>

          {/* Gallery View */}
          <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
            {isGenerating && status && (
              <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="relative">
                   <div className="w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin"></div>
                   <div className="absolute inset-0 flex items-center justify-center">
                     <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2">
                       <circle cx="12" cy="12" r="10"/>
                       <path d="M12 16v-4"/>
                       <path d="M12 8h.01"/>
                     </svg>
                   </div>
                </div>
                <p className="text-gray-500 font-medium animate-pulse">{status}</p>
              </div>
            )}

            {!isGenerating && generatedImages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4">
                <div className="p-6 bg-white rounded-3xl shadow-sm border border-gray-100">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="opacity-20">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                </div>
                <p className="text-lg">Enter a prompt to generate your first image</p>
                <p className="text-sm">High-quality AI images powered by RouterV</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence mode="popLayout">
                {generatedImages.map((img) => (
                  <motion.div
                    key={img.id}
                    layout
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all border border-gray-100"
                  >
                    <div className="aspect-square relative overflow-hidden bg-gray-100">
                      <img
                        src={img.url}
                        alt={img.prompt}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4">
                        <div className="flex gap-2">
                          <button 
                            onClick={() => window.open(img.url, '_blank')}
                            className="flex-1 py-2 px-3 bg-white/20 backdrop-blur-md hover:bg-white/30 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M15 3h6v6"/><path d="M10 14L21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            </svg>
                            View
                          </button>
                          <a 
                            href={img.url} 
                            download={`generated-${img.id}.${(img as any).format || 'png'}`}
                            className="flex-1 py-2 px-3 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                            Download
                          </a>
                        </div>
                      </div>
                    </div>
                    <div className="p-4">
                      <p className="text-sm text-gray-600 line-clamp-2 italic">"{img.prompt}"</p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </main>

        {/* Toast Notification */}
        <AnimatePresence>
          {toast && (
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed bottom-8 right-8 z-50"
            >
              <div className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-2xl border ${
                toast.type === "error" 
                  ? "bg-red-50 border-red-100 text-red-600" 
                  : "bg-green-50 border-green-100 text-green-600"
              } backdrop-blur-xl`}>
                {toast.type === "error" ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
                <span className="text-sm font-semibold">{toast.message}</span>
                <button 
                  onClick={() => setToast(null)}
                  className="ml-2 hover:opacity-70 transition-opacity"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
