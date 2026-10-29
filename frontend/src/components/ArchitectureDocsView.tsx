import React, { useState } from 'react';
import { 
  FileCode, 
  Terminal, 
  BookOpen, 
  ShieldCheck, 
  Layers, 
  Copy, 
  Check, 
  Cpu, 
  Database,
  AlertCircle
} from 'lucide-react';
import { Language } from '../types/audit';
import { 
  PYTHON_LANGGRAPH_SOURCE, 
  PYTHON_MCP_SERVER_SOURCE, 
  AGENTS_MD_SPEC, 
  SECURITY_EVAL_SOURCE 
} from '../services/backendContracts';

interface ArchitectureDocsViewProps {
  language: Language;
}

export const ArchitectureDocsView: React.FC<ArchitectureDocsViewProps> = ({ language }) => {
  const isAr = language === 'ar';

  const [activeTab, setActiveTab] = useState<'agents_md' | 'langgraph' | 'mcp' | 'security_tests' | 'status'>('status');
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
          <Terminal className="w-3.5 h-3.5" />
          <span>SDAIA CAPSTONE ENGINEERING SPECIFICATIONS & CONTRACTS</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          {isAr ? 'المعمارية التقنية، عقود MCP، ومواصفات AGENTS.md' : 'System Architecture, FastMCP Contracts & AGENTS.md'}
        </h1>
        <p className="mt-0.5 text-xs sm:text-sm text-slate-400">
          {isAr
            ? 'توثيق هندسي كامل يوضح عقود خدمات Python المستقلة، خادم FastMCP، ميزانية نافذة السياق، وجدول الشفافية الهندسية الصريح.'
            : 'Engineering contracts defining Python LangGraph nodes, FastMCP tool interfaces, 128k context allocations, and honest implementation boundaries.'}
        </p>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 rounded-xl border border-slate-800 text-xs overflow-x-auto">
        <button
          onClick={() => setActiveTab('status')}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'status' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          <span>{isAr ? 'جدول الشفافية والجاهزية' : 'Implementation Status'}</span>
        </button>

        <button
          onClick={() => setActiveTab('agents_md')}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'agents_md' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>AGENTS.md & Budget</span>
        </button>

        <button
          onClick={() => setActiveTab('langgraph')}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'langgraph' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>LangGraph (agent_graph.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('mcp')}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'mcp' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>FastMCP (mcp_server.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('security_tests')}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'security_tests' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Security Pytest Suite</span>
        </button>
      </div>

      {/* Tab 1: Implementation Status Demarcation Table */}
      {activeTab === 'status' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <span>{isAr ? 'مصفوفة الشفافية الهندسية والامتثال للشروط الإلزامية' : 'Engineering Transparency & Capstone Compliance Matrix'}</span>
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              {isAr
                ? 'التزاماً بالشروط الصارمة لمشروع التخرج: نوضح بجلاء تام ما الذي يعمل فعلياً داخل المتصفح، وما تم إعداده كعقود برمجية جاهزة للربط بخدمة Python خارجية.'
                : 'In strict compliance with evaluation rules: Clear demarcation of what is actively executed client-side vs. what is structured as external Python/MCP service contracts.'}
            </p>
          </div>

          <div className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
            <table className="w-full text-xs text-start">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-3 px-4 text-start font-medium">{isAr ? 'المكوّن الهندسي' : 'Engineering Component'}</th>
                  <th className="py-3 px-4 text-start font-medium">{isAr ? 'الحالة الحالية' : 'Current Status'}</th>
                  <th className="py-3 px-4 text-start font-medium">{isAr ? 'آلية العمل الحالية' : 'Active Execution Mechanism'}</th>
                  <th className="py-3 px-4 text-start font-medium">{isAr ? 'المطلوب للنشر الإنتاجي' : 'External Python Runtime Path'}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                <tr className="hover:bg-slate-800/20">
                  <td className="py-3 px-4 font-semibold text-white">
                    {isAr ? 'واجهة المستخدم RTL/LTR ولوحة التحكم' : 'RTL/LTR Frontend & Dashboard'}
                  </td>
                  <td className="py-3 px-4 text-emerald-400 font-mono">
                    ✓ {isAr ? 'يعمل فعلياً' : 'Live & Operational'}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {isAr ? 'تطبيق React 19 كامل متجاوب مع دعم اللغتين وتصميم تقني متطور' : 'Full React 19 SPA with bilingual RTL/LTR and strict SaaS design'}
                  </td>
                  <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                    مكتمل 100% في الواجهة
                  </td>
                </tr>

                <tr className="hover:bg-slate-800/20">
                  <td className="py-3 px-4 font-semibold text-white">
                    {isAr ? 'درع الأمان وفحص Prompt Injection' : 'Security Injection Guardrail'}
                  </td>
                  <td className="py-3 px-4 text-emerald-400 font-mono">
                    ✓ {isAr ? 'يعمل فعلياً' : 'Live & Operational'}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {isAr ? 'محرك فحص regex وعزل التهديدات في المتصفح + سيناريوهات اختبار حية' : 'In-browser regex heuristic engine + live red-team attack sandbox'}
                  </td>
                  <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                    جاهز للتكامل مع LLM Guard / Llama-Guard
                  </td>
                </tr>

                <tr className="hover:bg-slate-800/20">
                  <td className="py-3 px-4 font-semibold text-white">
                    {isAr ? 'بوابة الاعتماد البشري (HITL Gate)' : 'HITL Governance Mutation Gate'}
                  </td>
                  <td className="py-3 px-4 text-emerald-400 font-mono">
                    ✓ {isAr ? 'يعمل فعلياً' : 'Live & Operational'}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {isAr ? 'حظر برمجي صارم لكافة عمليات الكتابة وتوليد بصمة توقيع رقمي' : 'Deterministic mutation lock with SHA-256 cryptographic signature'}
                  </td>
                  <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                    جاهز للربط مع MemorySaver interrupt()
                  </td>
                </tr>

                <tr className="hover:bg-slate-800/20">
                  <td className="py-3 px-4 font-semibold text-white">
                    {isAr ? 'محرك استرجاع هجين (BM25 + تضمين)' : 'Hybrid Retrieval (BM25 + Dense)'}
                  </td>
                  <td className="py-3 px-4 text-cyan-400 font-mono">
                    ⚡ {isAr ? 'محاكاة دقيقة + كود FastMCP' : 'Simulated + FastMCP Ready'}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {isAr ? 'حساب أوزان BM25 وتطابق دلالي على مدونة الأنظمة المرفقة' : 'In-browser BM25 term weighting + dense cosine approximation'}
                  </td>
                  <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                    تشغيل `python mcp_server.py` مع SentenceTransformers
                  </td>
                </tr>

                <tr className="hover:bg-slate-800/20">
                  <td className="py-3 px-4 font-semibold text-white">
                    {isAr ? 'محرك LangGraph StateGraph' : 'LangGraph Python StateGraph'}
                  </td>
                  <td className="py-3 px-4 text-cyan-400 font-mono">
                    ⚡ {isAr ? 'محاكاة تفاعلية + كود Python' : 'Visual DAG + Code Contract'}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {isAr ? 'مخطط DAG مرئي تفاعلي مع فحص حمولة كل عقدة والتحكم في المسار' : 'Interactive visual DAG inspector with step-through state controller'}
                  </td>
                  <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                    تشغيل `python agent_graph.py` عبر FastAPI
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: AGENTS.md & Context Window Budget */}
      {activeTab === 'agents_md' && (
        <div className="space-y-6">
          {/* Context Window Budget Breakdown Graphic */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white">
                {isAr ? 'توزيع ميزانية نافذة السياق (128,000 Tokens Target Window):' : 'Context Window Allocation Budget (128k Tokens):'}
              </span>
              <span className="font-mono text-cyan-400">128k Model Target</span>
            </div>

            {/* Visual Budget Bar */}
            <div className="w-full h-4 rounded-lg bg-slate-950 flex overflow-hidden border border-slate-800 text-[9px] font-mono font-bold text-slate-950">
              <div style={{ width: '4.7%' }} className="bg-slate-400 h-full" title="System Prompt (6k)" />
              <div style={{ width: '25.0%' }} className="bg-cyan-400 h-full" title="Regulatory Reference Corpus (32k)" />
              <div style={{ width: '18.7%' }} className="bg-indigo-400 h-full" title="Target Document Chunks (24k)" />
              <div style={{ width: '12.5%' }} className="bg-emerald-400 h-full" title="Claims & Propositions (16k)" />
              <div style={{ width: '6.25%' }} className="bg-rose-400 h-full" title="Security Sandbox & Canaries (8k)" />
              <div style={{ width: '26.5%' }} className="bg-amber-400 h-full" title="Working Scratchpad (34k)" />
              <div style={{ width: '6.25%' }} className="bg-purple-400 h-full" title="Output Report (8k)" />
            </div>

            {/* Legend */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-1">
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-slate-400"></span>
                <span>System Directives: 6k (4.7%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400"></span>
                <span>Corpus References: 32k (25%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-indigo-400"></span>
                <span>Document Chunks: 24k (18.7%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400"></span>
                <span>Claims Cache: 16k (12.5%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-rose-400"></span>
                <span>Security Sandbox: 8k (6.25%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-amber-400"></span>
                <span>Scratchpad: 34k (26.5%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-sm bg-purple-400"></span>
                <span>Output Report: 8k (6.25%)</span>
              </div>
            </div>
          </div>

          {/* AGENTS.md Raw Content */}
          <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-mono text-cyan-400">AGENTS.md</span>
              <button
                onClick={() => handleCopy(AGENTS_MD_SPEC)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-950 border border-slate-800"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? (isAr ? 'تم النسخ' : 'Copied') : (isAr ? 'نسخ المواصفة' : 'Copy')}</span>
              </button>
            </div>
            <pre className="p-4 bg-slate-950/90 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
              {AGENTS_MD_SPEC}
            </pre>
          </div>
        </div>
      )}

      {/* Tab 3: LangGraph Code */}
      {activeTab === 'langgraph' && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-xs font-mono text-cyan-400">backend/agent_graph.py</span>
              <span className="text-xs text-slate-400 mx-2">· Python 3.11+ LangGraph StateGraph</span>
            </div>
            <button
              onClick={() => handleCopy(PYTHON_LANGGRAPH_SOURCE)}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-950 border border-slate-800"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? (isAr ? 'تم النسخ' : 'Copied') : (isAr ? 'نسخ الكود' : 'Copy')}</span>
            </button>
          </div>
          <pre className="p-4 bg-slate-950/90 rounded-lg border border-slate-800 font-mono text-xs text-cyan-200 overflow-x-auto leading-relaxed max-h-[500px]">
            {PYTHON_LANGGRAPH_SOURCE}
          </pre>
        </div>
      )}

      {/* Tab 4: FastMCP Server Code */}
      {activeTab === 'mcp' && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-xs font-mono text-cyan-400">mcp/mcp_server.py</span>
              <span className="text-xs text-slate-400 mx-2">· FastMCP Standalone Tool Server</span>
            </div>
            <button
              onClick={() => handleCopy(PYTHON_MCP_SERVER_SOURCE)}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-950 border border-slate-800"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? (isAr ? 'تم النسخ' : 'Copied') : (isAr ? 'نسخ الكود' : 'Copy')}</span>
            </button>
          </div>
          <pre className="p-4 bg-slate-950/90 rounded-lg border border-slate-800 font-mono text-xs text-amber-200 overflow-x-auto leading-relaxed max-h-[500px]">
            {PYTHON_MCP_SERVER_SOURCE}
          </pre>
        </div>
      )}

      {/* Tab 5: Security Pytest Suite */}
      {activeTab === 'security_tests' && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-xs font-mono text-cyan-400">tests/test_security_eval.py</span>
              <span className="text-xs text-slate-400 mx-2">· Pytest Security & HITL Test Harness</span>
            </div>
            <button
              onClick={() => handleCopy(SECURITY_EVAL_SOURCE)}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-950 border border-slate-800"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? (isAr ? 'تم النسخ' : 'Copied') : (isAr ? 'نسخ الكود' : 'Copy')}</span>
            </button>
          </div>
          <pre className="p-4 bg-slate-950/90 rounded-lg border border-slate-800 font-mono text-xs text-emerald-200 overflow-x-auto leading-relaxed max-h-[500px]">
            {SECURITY_EVAL_SOURCE}
          </pre>
        </div>
      )}
    </div>
  );
};
