import React from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  FileCheck2, 
  ArrowRight, 
  ArrowLeft,
  ChevronRight,
  Terminal,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import { AuditJob, Language } from '../types/audit';

interface DashboardViewProps {
  jobs: AuditJob[];
  selectedJob: AuditJob;
  onSelectJob: (job: AuditJob) => void;
  onNavigateTab: (tab: string) => void;
  language: Language;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  jobs,
  selectedJob,
  onSelectJob,
  onNavigateTab,
  language,
}) => {
  const isAr = language === 'ar';
  const ArrowIcon = isAr ? ArrowLeft : ArrowRight;

  const totalAudits = jobs.length;
  const totalContradictions = jobs.reduce((acc, j) => acc + j.contradictionsCount, 0);
  const totalInjections = jobs.reduce((acc, j) => acc + j.injectionsDetected, 0);
  const pendingHitl = jobs.filter(j => j.status === 'hitl_pending').length;
  const totalCost = jobs.reduce((acc, j) => acc + j.totalCostUsd, 0).toFixed(4);

  return (
    <div className="space-y-8">
      {/* Hero Headline and Capstone Identification */}
      <div className="border-b border-slate-800 pb-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-2">
              <span className="inline-block w-2 h-2 rounded-sm bg-cyan-400"></span>
              <span>SDAIA AGENTIC AI SYSTEMS ENGINEERING · CAPSTONE PROJECT</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {isAr ? 'منظومة مِجهر للتدقيق المستقل للأدلة والامتثال' : 'MIJHAR Autonomous Evidence & Compliance Audit System'}
            </h1>
            <p className="mt-1 text-sm text-slate-400 max-w-3xl">
              {isAr 
                ? 'استخراج آلي للادعاءات والتحقق من المراجع التنظيمية، واكتشاف التناقضات ومحاولات حقن الأوامر، مع بوابة مراجعة بشرية صارمة قبل تعديل السجلات.'
                : 'Automated claim decomposition, hybrid regulatory retrieval, contradiction discovery, and prompt injection mitigation with human-in-the-loop state mutation barriers.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigateTab('upload')}
              className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg shadow-sm transition-colors whitespace-nowrap"
            >
              {isAr ? 'بدء فحص وثيقة جديدة' : 'Start Document Audit'}
            </button>
            <button
              onClick={() => onNavigateTab('langgraph')}
              className="px-4 py-2 text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap"
            >
              {isAr ? 'عرض مسار LangGraph' : 'Inspect LangGraph DAG'}
            </button>
          </div>
        </div>
      </div>

      {/* High-Level Quantitative Rigor Metrics (Clean unboxed metadata, tabular figures) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>{isAr ? 'وثائق خاضعة للتدقيق' : 'Documents Audited'}</span>
            <FileCheck2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-white">
            {totalAudits}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {isAr ? '3 سيناريوهات تنظيمية قياسية' : '3 benchmark corpora loaded'}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>{isAr ? 'تناقضات نظامية مرصودة' : 'Contradictions Flagged'}</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-rose-400">
            {totalContradictions}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {isAr ? 'مخالفات صريحة لأطر سدايا وساما' : 'Direct regulatory divergences'}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>{isAr ? 'محاولات حقن محجوبة' : 'Prompt Injections Blocked'}</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-amber-400">
            {totalInjections}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {isAr ? 'عزل كامل عند حاجز التجزئة' : 'Isolated at tokenization boundary'}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>{isAr ? 'مهام بانتظار الاعتماد (HITL)' : 'HITL Pending Approvals'}</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-cyan-400">
            {pendingHitl}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {isAr ? 'عمليات الكتابة محظورة حتى الاعتماد' : 'Write mutations locked'}
          </div>
        </div>
      </div>

      {/* Main Audit Jobs Workbench Table */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">
              {isAr ? 'سجل عمليات التدقيق النشطة' : 'Active Audit Operations'}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {isAr ? 'انقر على أي عملية للاطلاع على الادعاءات المستخرجة والأدلة المؤيدة والمعارضة' : 'Select any audit run to inspect extracted claims, hybrid evidence, and contradiction matrix'}
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {isAr ? `إجمالي التكلفة: $${totalCost}` : `Total Compute: $${totalCost}`}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'رمز العملية' : 'Job ID'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'عنوان الوثيقة والمجال' : 'Document & Domain'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'الادعاءات' : 'Claims'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'التناقضات' : 'Contradictions'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'درجة الخطر' : 'Risk Rating'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'حالة الاعتماد' : 'Governance Status'}</th>
                <th className="py-3 px-4 text-end font-medium">{isAr ? 'الإجراء' : 'Action'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {jobs.map((job) => {
                const isSelected = selectedJob.id === job.id;
                return (
                  <tr
                    key={job.id}
                    onClick={() => onSelectJob(job)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-cyan-950/20 text-white' : 'hover:bg-slate-800/40 text-slate-300'
                    }`}
                  >
                    <td className="py-3.5 px-4 font-mono font-medium text-cyan-400 whitespace-nowrap">
                      {job.id}
                    </td>

                    <td className="py-3.5 px-4 max-w-sm">
                      <div className="font-medium text-slate-200 truncate">
                        {isAr ? job.titleAr : job.titleEn}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        <span>{isAr ? job.categoryAr : job.categoryEn}</span>
                        <span className="mx-1.5" aria-hidden="true">·</span>
                        <span className="font-mono">{job.sourceDocument}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono tabular-nums whitespace-nowrap">
                      <span>{job.claimsCount}</span>
                      <span className="text-slate-500 mx-1">/</span>
                      <span className="text-emerald-400">{job.verifiedCount} {isAr ? 'موثق' : 'ver'}</span>
                    </td>

                    <td className="py-3.5 px-4 font-mono tabular-nums whitespace-nowrap">
                      {job.contradictionsCount > 0 ? (
                        <span className="text-rose-400 font-semibold">{job.contradictionsCount} {isAr ? 'تناقض' : 'conflicts'}</span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div 
                            className={`h-full ${
                              job.riskScore > 70 ? 'bg-rose-500' : job.riskScore > 40 ? 'bg-amber-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${job.riskScore}%` }}
                          />
                        </div>
                        <span className="font-mono tabular-nums text-xs">
                          {job.riskScore}/100
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {job.status === 'hitl_pending' ? (
                        <span className="inline-flex items-center gap-1.5 text-amber-400">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{isAr ? 'بانتظار المراجعة' : 'HITL Pending'}</span>
                        </span>
                      ) : job.status === 'approved' ? (
                        <span className="inline-flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{isAr ? 'معتمد وموثق' : 'Approved & Written'}</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-rose-400">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>{isAr ? 'مرفوض' : 'Rejected'}</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-end whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectJob(job);
                          onNavigateTab('claims');
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/40 rounded transition-colors"
                      >
                        <span>{isAr ? 'فحص الأدلة' : 'Inspect'}</span>
                        <ArrowIcon className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Job Quick Detail Banner & Contradiction Alert */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
                {isAr ? 'التقرير الموجز للعملية المحددة' : 'Selected Audit Operation Focus'}
              </span>
              <h3 className="text-base font-bold text-white mt-0.5">
                {isAr ? selectedJob.titleAr : selectedJob.titleEn}
              </h3>
            </div>
            <div className="text-end">
              <span className="text-xs font-mono text-slate-400">
                {selectedJob.id} · {selectedJob.date}
              </span>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            {isAr ? selectedJob.summaryAr : selectedJob.summaryEn}
          </p>

          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <div className="text-[11px] text-slate-400">{isAr ? 'استهلاك الرموز' : 'Token Usage'}</div>
              <div className="text-base font-mono font-bold text-white mt-1 tabular-nums">
                {selectedJob.totalTokens.toLocaleString()}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <div className="text-[11px] text-slate-400">{isAr ? 'زمن التنفيذ' : 'Execution Latency'}</div>
              <div className="text-base font-mono font-bold text-cyan-400 mt-1 tabular-nums">
                {selectedJob.totalDurationMs} ms
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
              <div className="text-[11px] text-slate-400">{isAr ? 'النظام المستهدف' : 'Target Ledger'}</div>
              <div className="text-xs font-medium text-slate-300 mt-1.5 truncate">
                {selectedJob.targetSystem}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => onNavigateTab('claims')}
              className="px-4 py-2 text-xs font-medium text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <span>{isAr ? 'استعراض الادعاءات والمراجع' : 'View Extracted Claims & Evidence'}</span>
              <ArrowIcon className="w-3.5 h-3.5" />
            </button>
            {selectedJob.status === 'hitl_pending' && (
              <button
                onClick={() => onNavigateTab('hitl')}
                className="px-4 py-2 text-xs font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors"
              >
                {isAr ? 'الانتقال لمحطة الاعتماد البشري (HITL)' : 'Go to HITL Approval Station'}
              </button>
            )}
          </div>
        </div>

        {/* Security & Agentic Architecture Highlights */}
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">
              {isAr ? 'ضوابط الأمان ومعمارية Capstone' : 'SDAIA Capstone Architecture'}
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>{isAr ? 'محرك LangGraph ومخطط DAG' : 'LangGraph DAG State Machine'}</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                {isAr 
                  ? 'تدفق محدد بـ 8 عُقد ينفذ تجزئة المستند، درع الأمان، الاسترجاع الهجين، واكتشاف التناقضات، مع توقف شرطي عند بوابة HITL.'
                  : '8-node deterministic workflow executing ingestion, guardrail scanning, hybrid retrieval, and contradiction NLI with conditional pause at HITL checkpoint.'}
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-amber-400" />
                <span>{isAr ? 'بروتوكول أدوات FastMCP' : 'FastMCP Tool Contracts'}</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                {isAr
                  ? '3 أدوات معيارية تشمل خادم FastMCP المستقل للاسترجاع الهجين والتحقق من الأدلة وتنفيذ التعديلات المشروطة بتوقيع بشري.'
                  : '3 concrete tools including standalone FastMCP server for hybrid search, cross-encoder verification, and guarded state mutations.'}
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                <span>{isAr ? 'عزل Prompt Injection التام' : 'Strict Input Sanitization'}</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                {isAr
                  ? 'لا يُسمح للمستند المرفوع بتغيير تعليمات النظام أو استدعاء أدوات حساسة. تُعامل المدخلات كبيانات بحتة فقط.'
                  : 'Uploaded documents are treated strictly as untrusted data buffers, preventing instruction hijacking or arbitrary tool execution.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
