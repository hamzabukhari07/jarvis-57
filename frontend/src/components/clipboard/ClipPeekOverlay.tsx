import React, { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Copy, Globe, Bot, Send, X, Code, FileText, Sparkles, Clipboard, ChevronDown } from "@/lib/zezo-icons";

interface ClipboardPayload {
  text: string;
  type: "url" | "code" | "article" | "text";
  timestamp: number;
  preview: string;
}

export function ClipPeekOverlay() {
  const [clipData, setClipData] = useState<ClipboardPayload | null>(null);
  const [prompt, setPrompt] = useState("");
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let mounted = true;

    function connect() {
      if (!mounted) return;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "get_clipboard" }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "clipboard_update" && msg.data) {
            setClipData(msg.data);
            setDismissed(false);
            setExpanded(false);
          }
        } catch (e) {
          console.error("Failed to parse websocket message:", e);
        }
      };

      ws.onclose = () => {
        if (mounted) {
          setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      mounted = false;
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  if (!clipData) return null;

  const sendMessageToZezo = (text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "user_message", text }));
    }
  };

  const handleAction = (action: string) => {
    if (action === "browser" && clipData.type === "url") {
      let targetUrl = clipData.text.trim();
      if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://")) {
        targetUrl = "https://" + targetUrl;
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "open_browser", url: targetUrl }));
      } else {
        window.open(targetUrl, "_blank");
      }
    } else if (action === "summarize") {
      sendMessageToZezo(`Please summarize and explain this copied ${clipData.type}: ${clipData.text}`);
    } else if (action === "chat") {
      sendMessageToZezo(`Here is content from my clipboard: ${clipData.text}`);
    }
    setExpanded(false);
    setDismissed(true);
  };

  const handleSendPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    sendMessageToZezo(`${prompt}\n\nClipboard Content:\n${clipData.text}`);
    setPrompt("");
    setExpanded(false);
    setDismissed(true);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 h-12 w-12 pointer-events-none">
      <button
        type="button"
        onClick={() => setExpanded(true)}
        aria-label={`Open ClipPeek. Latest copied content: ${clipData.preview}`}
        aria-hidden={expanded || dismissed}
        inert={expanded || dismissed}
        title={`ClipPeek · ${clipData.type}`}
        className={`absolute bottom-0 right-0 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-card text-primary shadow-xl transition-[opacity,transform,background-color] duration-300 ease-out hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${!expanded && !dismissed ? "pointer-events-auto opacity-100 scale-100" : "pointer-events-none opacity-0 scale-90"}`}
      >
        <Clipboard className="h-5 w-5" />
        <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-card bg-primary" />
      </button>

      <div
        aria-hidden={!expanded || dismissed}
        inert={!expanded || dismissed}
        className={`absolute bottom-0 right-0 w-96 max-w-[calc(100vw-32px)] origin-bottom-right rounded-xl border border-border bg-card p-4 shadow-2xl transition-[opacity,transform] duration-300 ease-out ${expanded && !dismissed ? "pointer-events-auto opacity-100 translate-y-0 scale-100" : "pointer-events-none opacity-0 translate-y-2 scale-95"}`}
      >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider">
          {clipData.type === "url" && <Globe className="w-3.5 h-3.5" />}
          {clipData.type === "code" && <Code className="w-3.5 h-3.5" />}
          {clipData.type === "article" && <FileText className="w-3.5 h-3.5" />}
          {clipData.type === "text" && <Copy className="w-3.5 h-3.5" />}
          <span>ClipPeek — {clipData.type}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-foreground"
            onClick={() => setExpanded(false)}
            aria-label="Collapse ClipPeek"
            title="Collapse"
          >
            <ChevronDown className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-foreground"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss ClipPeek"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="bg-background/80 border border-border/60 rounded-lg p-2.5 text-xs font-mono text-foreground mb-3 truncate">
        {clipData.preview}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {clipData.type === "url" && (
          <Button
            size="sm"
            variant="secondary"
            className="h-7 text-xs gap-1.5"
            onClick={() => handleAction("browser")}
          >
            <Globe className="w-3 h-3" /> Open in Browser
          </Button>
        )}
        <Button
          size="sm"
          variant="secondary"
          className="h-7 text-xs gap-1.5"
          onClick={() => handleAction("summarize")}
        >
          <Sparkles className="w-3 h-3" /> Summarize / Explain
        </Button>
        <Button
          size="sm"
          variant="secondary"
          className="h-7 text-xs gap-1.5"
          onClick={() => handleAction("chat")}
        >
          <Bot className="w-3 h-3" /> Send to Chat
        </Button>
      </div>

      <form onSubmit={handleSendPrompt} className="flex gap-2">
        <Input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask Zezo about this clipboard..."
          className="h-8 text-xs bg-background"
        />
        <Button type="submit" size="sm" className="h-8 px-3">
          <Send className="w-3 h-3" />
        </Button>
      </form>
      </div>
    </div>
  );
}
