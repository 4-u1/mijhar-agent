import React, { useState } from 'react';
import { 
  UploadCloud, 
  FileText, 
  Sparkles, 
  ShieldAlert, 
  ArrowRight, 
  ArrowLeft,
  CheckCircle2, 
  AlertTriangle,
  Play,
  RotateCcw,
  Search
} from 'lucide-react';
import { AuditJob, Claim, SecurityThreat, Language } from '../types/audit';
import { SYNTHETIC_BENCHMARKS } from '../data/syntheticBenchmarks';
import { scanForPromptInjections } from '../services/agentEngine';

interface UploadAuditViewProps {
  currentJob: AuditJob;
  onSelectBenchmark: (index: number) => void;
  onNavigateTab: (tab: string) => void;
  language: Language;
}

export const UploadAuditView: React.FC<UploadAuditViewProps> = ({
  currentJob,
  onSelectBenchmark,
  onNavigateTab,
  language,
}) => {
  const isAr = language === 'ar';
  const ArrowIcon = isAr ? ArrowLeft : ArrowRight;

  const [customText, setCustomText] = useState<string>('');
  const [selectedBenchmarkIdx, setSelectedBenchmarkIdx] = useState<number>(0);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [scanStep, setScanStep] = useState<number>(0);
  const [liveThreats, setLiveThreats] = useState<SecurityThreat[]>([]);
  const [extractedPropositions, setExtractedPropositions] = useState<string[]>([]);

  const activeBenchmark = SYNTHETIC_BENCHMARKS[selectedBenchmarkIdx];
  const activeContent = customText || (isAr ? activeBenchmark.documentContentAr : activeBenchmark.documentContentEn);

  const handleBenchmarkSelect = (idx: number) => {
    setSelectedBenchmarkIdx(idx);
    setCustomText('');
    setLiveThreats([]);
    setExtractedPropositions([]);
    setScanStep(0);
    onSelectBenchmark(idx);
  };

  const handleRunInteractiveScan = () => {
    setIsScanning(true);
    setScanStep(1);
    setLiveThreats([]);
    setExtractedPropositions([]);

    // Step 1: Ingestion
    setTimeout(() => {
      setScanStep(2);
      // Step 2: Prompt Injection Guardrail Scan
      const threats = scanForPromptInjections(activeContent, activeBenchmark.job.id);
      setLiveThreats(threats);

      setTimeout(() => {
        setScanStep(3);
        // Step 3: Extract Claims
        const mockProps = activeBenchmark.claims.map(c => isAr ? c.textAr : c.textEn);
        setExtractedPropositions(mockProps);

        setTimeout(() => {
          setScanStep(4); // Finished
          setIsScanning(false);
        }, 800);
      }, 900);
    }, 700);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          {isAr ? 'استيعاب المستندات واستخراج الادعاءات' : 'Document Ingestion & Claim Extraction'}
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-400">
          {isAr
            ? 'اختر إحدى الوثائق التنظيمية القياسية أو الصق نصًا مخصصًا لتشغيل درع فحص حقن الأوامر وتفكيك النص إلى ادعاءات ذرية.'
            : 'Select a regulatory benchmark corpus or provide document text to run injection defense and atomic proposition extraction.'}
        </p>
      </div>

      {/* Benchmark Selector Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {SYNTHETIC_BENCHMARKS.map((bench, idx) => {
          const isSelected = selectedBenchmarkIdx === idx && !customText;
          return (
            <button
              key={bench.job.id}
              onClick={() => handleBenchmarkSelect(idx)}
              className={`p-4 rounded-xl text-start border transition-all ${
                isSelected
                  ? 'bg-cyan-950/30 border-cyan-500/50 shadow-sm shadow-cyan-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span className="font-mono text-cyan-400">{bench.job.id}</span>
                <span className="font-mono text-xs">{bench.job.claimsCount} {isAr ? 'ادعاءات' : 'claims'}</span>
              </div>
              <div className="text-sm font-semibold text-slate-200 line-clamp-1">
                {isAr ? bench.job.titleAr : bench.job.titleEn}
              </div>
              <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                {isAr ? bench.job.categoryAr : bench.job.categoryEn} · {bench.job.riskScore > 70 ? (isAr ? 'مخاطر حرجة' : 'High Risk') : (isAr ? 'امتثال جزئي' : 'Compliant')}
              </div>
            </button>
          );
        })}
      </div>

      {/* Main Two-Column Layout: Document Source View vs Extraction Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left/Right Document Previewer (7 cols) */}
        <div className="lg:col-span-7 rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-semibold text-white">
                {isAr ? 'محتوى الوثيقة الخاضعة للفحص' : 'Document Ingestion Buffer'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span>{activeBenchmark.job.sourceDocument}</span>
            </div>
          </div>

          <div className="flex-1 min-h-[360px] bg-slate-950/80 rounded-lg p-4 border border-slate-800/80 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
            {activeContent}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="text-[11px] text-slate-500">
              {isAr ? 'يتم حفظ إحداثيات كل فقرة وعزل أي أوامر خفية تلقائيًا' : 'All chunks hashed with SHA-256 and mapped to source line offsets'}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleRunInteractiveScan}
                disabled={isScanning}
                className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 rounded-lg flex items-center gap-2 transition-colors shadow-sm"
              >
                {isScanning ? (
                  <>
                    <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                    <span>{isAr ? 'جاري الفحص والاستخراج...' : 'Analyzing Chunks...'}</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{isAr ? 'تشغيل فحص الأمان والاستخراج' : 'Execute Extraction Pipeline'}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right/Left Extraction & Guardrail Results (5 cols) */}
        <div className="lg:col-span-5 rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-semibold text-white">
                {isAr ? 'مخرجات الفحص والادعاءات' : 'Extraction Pipeline Output'}
              </span>
            </div>
            <span className="text-xs font-mono text-cyan-400">
              {isScanning ? `${isAr ? 'المرحلة' : 'Step'} ${scanStep}/4` : (isAr ? 'جاهز' : 'Ready')}
            </span>
          </div>

          {/* Stepper Status Indicators */}
          <div className="space-y-2 text-xs">
            <div className={`p-2.5 rounded-lg border transition-all ${
              scanStep >= 1 ? 'bg-slate-950/80 border-cyan-500/30 text-cyan-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'
            }`}>
              <div className="flex items-center justify-between">
                <span>1. {isAr ? 'تجزئة المستند وحساب SHA-256' : 'Document Ingestion & Tokenizer'}</span>
                {scanStep >= 1 && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />}
              </div>
            </div>

            <div className={`p-2.5 rounded-lg border transition-all ${
              scanStep >= 2 ? (liveThreats.length > 0 || activeBenchmark.threats.length > 0 ? 'bg-rose-950/30 border-rose-500/40 text-rose-300' : 'bg-slate-950/80 border-emerald-500/30 text-emerald-300') : 'bg-slate-950/40 border-slate-800 text-slate-500'
            }`}>
              <div className="flex items-center justify-between">
                <span>2. {isAr ? 'درع فحص حقن الأوامر (Prompt Injection)' : 'Security Guardrail Scan'}</span>
                {scanStep >= 2 && (
                  (liveThreats.length > 0 || activeBenchmark.threats.length > 0) ? (
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  )
                )}
              </div>
            </div>

            <div className={`p-2.5 rounded-lg border transition-all ${
              scanStep >= 3 ? 'bg-slate-950/80 border-cyan-500/30 text-cyan-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'
            }`}>
              <div className="flex items-center justify-between">
                <span>3. {isAr ? 'تفكيك الادعاءات الذرية (Atomic Propositions)' : 'Proposition & Claim Parsing'}</span>
                {scanStep >= 3 && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />}
              </div>
            </div>
          </div>

          {/* Security Alert Callout if threats exist */}
          {(liveThreats.length > 0 || (scanStep === 0 && activeBenchmark.threats.length > 0)) && (
            <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-800/80 text-rose-300 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-rose-400">
                <ShieldAlert className="w-4 h-4" />
                <span>{isAr ? 'تم اعتراض محاولة حقن أوامر خفية!' : 'Indirect Prompt Injection Intercepted!'}</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed font-mono">
                {liveThreats[0]?.rawPayload || activeBenchmark.threats[0]?.rawPayload}
              </p>
              <div className="text-[10px] text-rose-400 pt-1">
                {isAr ? 'تم عزل النص المحقون ومنع تمريره كتعليمات إلى الوكيل' : 'Quarantined before prompt construction. Prevented role elevation.'}
              </div>
            </div>
          )}

          {/* Extracted Claims Preview List */}
          <div className="flex-1 overflow-y-auto space-y-2 max-h-[220px]">
            <div className="text-xs font-semibold text-slate-300">
              {isAr ? 'الادعاءات المستخرجة للتدقيق:' : 'Extracted Claims Awaiting Audit:'}
            </div>
            {(extractedPropositions.length > 0 ? extractedPropositions : activeBenchmark.claims.map(c => isAr ? c.textAr : c.textEn)).map((clm, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-200 flex items-start gap-2">
                <span className="font-mono text-cyan-400 text-[10px] mt-0.5">#{i+1}</span>
                <span className="leading-snug">{clm}</span>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            <button
              onClick={() => onNavigateTab('claims')}
              className="w-full py-2 px-3 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <span>{isAr ? 'استعراض مصفوفة الأدلة والمراجع' : 'Proceed to Evidence Matrix'}</span>
              <ArrowIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
