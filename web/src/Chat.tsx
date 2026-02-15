import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Connect WebSocket
  useEffect(() => {
    connectWs();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  async function connectWs() {
    try {
      // Create session first
      const res = await fetch("/api/v1/web/session", { method: "POST" });
      const data = await res.json();
      const sid = data.session_id;
      setSessionId(sid);

      // Connect WebSocket
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/web/ws/${sid}`);

      ws.onopen = () => {
        setIsConnected(true);
        addMessage("system", "Connected to Gulama.");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWsMessage(data);
      };

      ws.onclose = () => {
        setIsConnected(false);
        addMessage("system", "Disconnected. Refresh to reconnect.");
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      wsRef.current = ws;
    } catch {
      addMessage("system", "Failed to connect. Is the Gulama server running?");
    }
  }

  function handleWsMessage(data: { type: string; content: string }) {
    if (data.type === "chunk") {
      // Streaming: append to last assistant message
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "assistant") {
          return [
            ...prev.slice(0, -1),
            { ...last, content: last.content + data.content },
          ];
        }
        return [
          ...prev,
          { role: "assistant", content: data.content, timestamp: new Date() },
        ];
      });
    } else if (data.type === "done") {
      setIsStreaming(false);
      // Replace streaming message with final
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "assistant") {
          return [
            ...prev.slice(0, -1),
            { ...last, content: data.content },
          ];
        }
        return [
          ...prev,
          { role: "assistant", content: data.content, timestamp: new Date() },
        ];
      });
    } else if (data.type === "error") {
      setIsStreaming(false);
      addMessage("system", data.content);
    }
  }

  function addMessage(role: Message["role"], content: string) {
    setMessages((prev) => [...prev, { role, content, timestamp: new Date() }]);
  }

  function sendMessage() {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    addMessage("user", text);
    setInput("");
    setIsStreaming(true);

    wsRef.current.send(JSON.stringify({ content: text }));

    // Focus back on input
    inputRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="px-6 py-3 border-b border-gray-800 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Chat</h1>
          <p className="text-xs text-gray-500">
            {isConnected ? "Connected" : "Disconnected"}
            {sessionId && ` — Session ${sessionId.slice(0, 8)}`}
          </p>
        </div>
        <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-gulama-500" : "bg-red-500"}`} />
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <div className="w-16 h-16 bg-gray-800 rounded-2xl flex items-center justify-center text-2xl mb-4">
              G
            </div>
            <p className="text-lg">Welcome to Gulama</p>
            <p className="text-sm mt-1">Your secure AI assistant. Type a message to begin.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-2xl rounded-2xl px-4 py-2 chat-message ${
                msg.role === "user"
                  ? "bg-gulama-600 text-white"
                  : msg.role === "system"
                  ? "bg-gray-800 text-gray-400 text-sm italic"
                  : "bg-gray-800 text-gray-100"
              }`}
            >
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              <div className="text-xs opacity-50 mt-1">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl px-4 py-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-gulama-500 min-h-[44px] max-h-[200px]"
            rows={1}
            disabled={!isConnected}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !input.trim() || isStreaming}
            className="bg-gulama-600 hover:bg-gulama-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl px-4 py-3 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
