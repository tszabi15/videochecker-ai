import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Header } from './components/layout/Header';
import { UploadPage } from './pages/UploadPage';
import { JobStatusPage } from './pages/JobStatusPage';
import { ReportPage } from './pages/ReportPage';
import { HistoryPage } from './pages/HistoryPage';

export const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/jobs" element={<HistoryPage />} />
            <Route path="/jobs/:job_id" element={<JobStatusPage />} />
            <Route path="/jobs/:job_id/report" element={<ReportPage />} />
          </Routes>
        </main>
        <footer className="border-t border-slate-800/80 py-6 text-center text-xs font-mono text-slate-500 glass-panel">
          <p>VideoChecker AI Auditor • Powered by Gemini 3.1 Pro Preview & Whisper large-v3</p>
        </footer>
      </div>
    </Router>
  );
};

export default App;
