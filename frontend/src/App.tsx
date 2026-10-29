import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DashboardView } from './components/DashboardView';
import { UploadAuditView } from './components/UploadAuditView';
import { ClaimDetailView } from './components/ClaimDetailView';
import { LangGraphVisualizer } from './components/LangGraphVisualizer';
import { HITLApprovalModal } from './components/HITLApprovalModal';
import { RedTeamSecurityLab } from './components/RedTeamSecurityLab';
import { AuditTrailView } from './components/AuditTrailView';
import { ArchitectureDocsView } from './components/ArchitectureDocsView';

import { AuditJob, Language, HITLDecision } from './types/audit';
import { SYNTHETIC_BENCHMARKS } from './data/syntheticBenchmarks';

export default function App() {
  const [language, setLanguage] = useState<Language>('ar');
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [jobs, setJobs] = useState<AuditJob[]>(SYNTHETIC_BENCHMARKS.map(b => b.job));
  const [selectedJobId, setSelectedJobId] = useState<string>(SYNTHETIC_BENCHMARKS[0].job.id);

  // Sync document language and text direction
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  }, [language]);

  const selectedJob = jobs.find(j => j.id === selectedJobId) || jobs[0];

  const handleToggleLanguage = () => {
    setLanguage(prev => (prev === 'ar' ? 'en' : 'ar'));
  };

  const handleSelectJob = (job: AuditJob) => {
    setSelectedJobId(job.id);
  };

  const handleSelectBenchmark = (index: number) => {
    const bench = SYNTHETIC_BENCHMARKS[index];
    if (bench) {
      setSelectedJobId(bench.job.id);
    }
  };

  const handleDecisionSubmitted = (decision: HITLDecision) => {
    setJobs(prev => prev.map(j => {
      if (j.id === decision.jobId) {
        return {
          ...j,
          status: decision.decision === 'approved' ? 'approved' : 'rejected',
          hitlDecision: decision,
        };
      }
      return j;
    }));
  };

  const pendingHITLCount = jobs.filter(j => j.status === 'hitl_pending').length;

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 flex flex-col ${language === 'ar' ? 'font-arabic' : 'font-latin'}`}>
      {/* Universal Top Bar */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        language={language}
        onToggleLanguage={handleToggleLanguage}
        pendingHITLCount={pendingHITLCount}
      />

      {/* Main Workspace Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {currentTab === 'dashboard' && (
          <DashboardView
            jobs={jobs}
            selectedJob={selectedJob}
            onSelectJob={handleSelectJob}
            onNavigateTab={setCurrentTab}
            language={language}
          />
        )}

        {currentTab === 'upload' && (
          <UploadAuditView
            currentJob={selectedJob}
            onSelectBenchmark={handleSelectBenchmark}
            onNavigateTab={setCurrentTab}
            language={language}
          />
        )}

        {currentTab === 'claims' && (
          <ClaimDetailView
            job={selectedJob}
            language={language}
            onNavigateTab={setCurrentTab}
          />
        )}

        {currentTab === 'langgraph' && (
          <LangGraphVisualizer
            job={selectedJob}
            language={language}
            onNavigateTab={setCurrentTab}
          />
        )}

        {currentTab === 'hitl' && (
          <HITLApprovalModal
            job={selectedJob}
            onDecisionSubmitted={handleDecisionSubmitted}
            language={language}
          />
        )}

        {currentTab === 'security' && (
          <RedTeamSecurityLab language={language} />
        )}

        {currentTab === 'specs' && (
          <ArchitectureDocsView language={language} />
        )}

        {currentTab === 'logs' && (
          <AuditTrailView
            job={selectedJob}
            language={language}
          />
        )}
      </main>

      {/* Engineering Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">
              {language === 'ar' ? 'مِجهر | MIJHAR' : 'MIJHAR'}
            </span>
            <span>·</span>
            <span>
              {language === 'ar' 
                ? 'مشروع تخرج برنامج هندسة أنظمة الذكاء الاصطناعي التوكيلي المتقدمة (SDAIA Advanced Agentic AI Systems Engineering Capstone)'
                : 'SDAIA Academy Advanced Agentic AI Systems Engineering Capstone Project'}
            </span>
          </div>

          <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
            <button
              onClick={() => setCurrentTab('specs')}
              className="hover:text-cyan-400 transition-colors"
            >
              AGENTS.md
            </button>
            <span>·</span>
            <button
              onClick={() => setCurrentTab('logs')}
              className="hover:text-cyan-400 transition-colors"
            >
              {language === 'ar' ? 'سجل العمليات' : 'Telemetry Logs'}
            </button>
            <span>·</span>
            <span>{language === 'ar' ? 'نموذج أولي · البيانات المعروضة اصطناعية' : 'Prototype UI · displayed data is synthetic'}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
