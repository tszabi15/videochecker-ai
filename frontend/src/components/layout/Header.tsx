import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Video, History, BarChart3, ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              VideoChecker<span className="text-indigo-400 font-extrabold ml-1">AI</span>
            </span>
            <span className="block text-[10px] uppercase tracking-wider font-mono text-slate-400">Gemini 3.1 Auditor</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            to="/"
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/') 
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            <Video className="w-4 h-4" />
            <span>Upload Studio</span>
          </Link>

          <Link
            to="/jobs"
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/jobs') 
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Jobs History</span>
          </Link>
        </nav>
      </div>
    </header>
  );
};
