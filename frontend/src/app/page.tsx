'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: Date;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I am your IT Helpdesk Assistant. How can I help you troubleshoot your infrastructure today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      if (!response.ok) {
        throw new Error('Failed to connect to the IT Helpdesk API. Please ensure the backend is running.');
      }

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'An unexpected error occurred.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      <div className="text-center space-y-2">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
          IT Helpdesk <span className="text-blue-600">RAG Assistant</span>
        </h1>
        <p className="text-slate-500 max-w-xl mx-auto font-medium">
          Secure Internal Support Channel
        </p>
      </div>

      <div className="w-full max-w-3xl bg-white shadow-2xl rounded-3xl border border-slate-100 overflow-hidden flex flex-col h-[650px] transition-all hover:shadow-blue-100/50">
        {/* Chat Header */}
        <div className="bg-slate-50/80 backdrop-blur-md border-b border-slate-100 p-4 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-10 h-10 bg-blue-600 rounded-2xl flex items-center justify-center text-white font-bold shadow-lg shadow-blue-200">
                IT
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full"></div>
            </div>
            <div>
              <div className="font-bold text-slate-800 text-sm leading-tight">Helpdesk Butler</div>
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">AI Support Engine</div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-bold text-slate-400 bg-slate-200/50 px-2.5 py-1 rounded-full uppercase">Local Network</span>
          </div>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 bg-gradient-to-b from-white to-slate-50/30 custom-scrollbar">
          {messages.map((m) => (
            <div 
              key={m.id} 
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}
            >
              <div 
                className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
                  m.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none' 
                    : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'
                }`}
              >
                <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{m.content}</p>
                
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Verified Sources</p>
                    <div className="flex flex-wrap gap-2">
                      {m.sources.map((s, idx) => (
                        <span key={idx} className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-500 rounded font-mono truncate max-w-[150px]">
                          {s.split(/[\\/]/).pop()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                <p className={`text-[10px] mt-1.5 opacity-50 font-medium ${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start animate-in fade-in duration-300">
              <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-blue-300 rounded-full animate-bounce"></div>
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                </div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Consulting Docs</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input Area */}
        <form onSubmit={handleSubmit} className="p-4 md:p-6 bg-white border-t border-slate-100">
          <div className="relative group">
            <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              type="text" 
              placeholder="Ask about VPN, Email setup, or VPN resets..." 
              className="w-full pl-6 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all text-slate-700 placeholder:text-slate-400 font-medium"
            />
            <button 
              type="submit"
              disabled={isLoading || !input.trim()} 
              className="absolute right-2.5 top-2.5 p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-slate-100 disabled:text-slate-300 transition-all shadow-lg shadow-blue-200 disabled:shadow-none"
            >
               <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
          <p className="mt-3 text-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">
            Internal Use Only • Authorized Personnel
          </p>
        </form>
      </div>

    </div>
  );
}
