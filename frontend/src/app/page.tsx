export default function Home() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-8 animate-in fade-in duration-700">
      
      <div className="text-center space-y-4">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
          IT Helpdesk <span className="text-blue-600">RAG Assistant</span>
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Your AI-powered internal infrastructure troubleshooting bot. Ask me anything about the company's IT systems and I'll find the answer from our documentation.
        </p>
      </div>

      <div className="w-full max-w-2xl bg-white shadow-xl rounded-2xl border border-slate-100 overflow-hidden min-h-[500px] flex flex-col">
        {/* Chat Header */}
        <div className="bg-slate-50 border-b border-slate-100 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="font-medium text-slate-700">System Online</span>
          </div>
          <div className="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-1 rounded">v1.0.0-beta</div>
        </div>

        {/* Chat Messages Area (Placeholder for Phase 5) */}
        <div className="flex-1 p-6 flex flex-col items-center justify-center text-slate-400 space-y-4 bg-slate-50/50">
          <svg className="w-12 h-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p>Chat interface will be implemented in Phase 5</p>
        </div>

        {/* Chat Input Area (Placeholder for Phase 5) */}
        <div className="p-4 bg-white border-t border-slate-100">
          <div className="relative flex items-center">
            <input 
              disabled
              type="text" 
              placeholder="Type your IT question here..." 
              className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl outline-none transition-all cursor-not-allowed opacity-50"
            />
            <button disabled className="absolute right-2 p-2 bg-slate-200 text-slate-400 rounded-lg cursor-not-allowed">
               <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
