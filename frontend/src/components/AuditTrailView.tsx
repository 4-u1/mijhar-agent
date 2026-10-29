import React, { useState } from 'react';
import { 
  History, 
  Terminal, 
  Clock, 
  Coins, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Search,
  Filter
} from 'lucide-react';
import { AuditJob, AuditStepLog, Language } from '../types/audit';
import { SYNTHETIC_BENCHMARKS } from '../data/syntheticBenchmarks';

interface AuditTrailViewProps {
  job: AuditJob;
  language: Language;
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({ job, language }) => {
  const isAr = language === 'ar';

  const benchmark = SYNTHETIC_BENCHMARKS.find(b => b.job.id === job.id) || SYNTHETIC_BENCHMARKS[0];
  const logs = benchmark.logs;

  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterToolType, setFilterToolType] = useState<string>('all');

  const filteredLogs = logs.filter(log => {
    const matchesStatus = filterStatus === 'all' || log.status === filterStatus;
    const matchesTool = filterToolType === 'all' || log.toolType === filterToolType;
    return matchesStatus && matchesTool;
  });

  const totalTokens = logs.reduce((acc, l) => acc + l.tokenUsage.prompt + l.tokenUsage.completion, 0);
  const totalCost = logs.reduce((acc, l) => acc + l.tokenUsage.costUsd, 0).toFixed(4);
  const totalDuration = logs.reduce((acc, l) => acc + l.durationMs, 0);

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs font-mono text-cyan-400 mb-1">
            {job.id} · EXECUTION TELEMETRY & AUDIT TRAIL
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            {isAr ? 'سجل تتبع التنفيذ وتكاليف الحوسبة' : 'Execution Trace & Telemetry Audit Log'}
          </h1>
          <p className="mt-0.5 text-xs sm:text-sm text-slate-400">
            {isAr
              ? 'سجل غير قابل للتعديل يوثق كافة خطوات التنفيذ واستدعاءات أدوات MCP، ومعدلات استهلاك الرموز وزمن الاستجابة.'
              : 'Verifiable execution log detailing node durations, FastMCP tool dispatches, token expenditures, and containment events.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
            {isAr ? 'إجمالي الرموز:' : 'Tokens:'} <strong className="text-cyan-400">{totalTokens.toLocaleString()}</strong>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
            {isAr ? 'التكلفة:' : 'Cost:'} <strong className="text-emerald-400">${totalCost}</strong>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">{isAr ? 'زمن المعالجة الإجمالي' : 'Total Latency'}</div>
            <div className="text-xl font-mono font-bold text-white mt-1 tabular-nums">
              {totalDuration} ms
            </div>
          </div>
          <Clock className="w-6 h-6 text-cyan-400 opacity-60" />
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">{isAr ? 'أدوات FastMCP المستدعاة' : 'MCP Tools Dispatched'}</div>
            <div className="text-xl font-mono font-bold text-cyan-400 mt-1 tabular-nums">
              {logs.filter(l => l.toolType === 'mcp_server').length} / {logs.length}
            </div>
          </div>
          <Terminal className="w-6 h-6 text-cyan-400 opacity-60" />
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">{isAr ? 'حالات التنبيه والإنذار' : 'Warnings & Security Alerts'}</div>
            <div className="text-xl font-mono font-bold text-amber-400 mt-1 tabular-nums">
              {logs.filter(l => l.status === 'warning' || l.status === 'error').length}
            </div>
          </div>
          <AlertTriangle className="w-6 h-6 text-amber-400 opacity-60" />
        </div>
      </div>

      {/* Table Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">{isAr ? 'تصفية حسب الحالة:' : 'Status:'}</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none"
          >
            <option value="all">{isAr ? 'كافة الحالات' : 'All Statuses'}</option>
            <option value="success">{isAr ? 'ناجحة (Success)' : 'Success'}</option>
            <option value="warning">{isAr ? 'تنبيه (Warning)' : 'Warning'}</option>
            <option value="error">{isAr ? 'خطأ / اعتراض (Error)' : 'Error'}</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400">{isAr ? 'نوع الأداة:' : 'Tool Type:'}</span>
          <select
            value={filterToolType}
            onChange={(e) => setFilterToolType(e.target.value)}
            className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none"
          >
            <option value="all">{isAr ? 'كافة الأدوات' : 'All Tools'}</option>
            <option value="mcp_server">FastMCP Server</option>
            <option value="internal">Internal Engine</option>
          </select>
        </div>
      </div>

      {/* Audit Step Logs Table */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'الخطوة' : 'Step'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'عقدة المسار' : 'Graph Node'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'الأداة المنفذة' : 'Tool / Protocol'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'المدة' : 'Latency'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'الرموز / التكلفة' : 'Tokens / Cost'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'الحالة' : 'Status'}</th>
                <th className="py-3 px-4 text-start font-medium">{isAr ? 'ملخص المخرجات' : 'Output Payload'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 text-slate-300">
                  <td className="py-3 px-4 font-bold text-slate-400">
                    #{log.stepIndex}
                  </td>

                  <td className="py-3 px-4 font-sans font-medium text-slate-200 whitespace-nowrap">
                    <div>{isAr ? log.nodeNameAr : log.nodeNameEn}</div>
                    <div className="text-[10px] font-mono text-slate-500">{log.nodeName}</div>
                  </td>

                  <td className="py-3 px-4 whitespace-nowrap">
                    <span className="text-cyan-400">{log.toolName}</span>
                    <span className={`ms-1.5 text-[9px] px-1 py-0.2 rounded ${
                      log.toolType === 'mcp_server' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/60' : 'bg-slate-900 text-slate-500'
                    }`}>
                      {log.toolType === 'mcp_server' ? 'MCP' : 'Core'}
                    </span>
                  </td>

                  <td className="py-3 px-4 tabular-nums whitespace-nowrap">
                    {log.durationMs} ms
                  </td>

                  <td className="py-3 px-4 tabular-nums whitespace-nowrap">
                    <div>{log.tokenUsage.prompt + log.tokenUsage.completion} tok</div>
                    <div className="text-[10px] text-slate-500">${log.tokenUsage.costUsd.toFixed(4)}</div>
                  </td>

                  <td className="py-3 px-4 whitespace-nowrap">
                    {log.status === 'success' ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>SUCCESS</span>
                      </span>
                    ) : log.status === 'warning' ? (
                      <span className="text-amber-400 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>ALERT</span>
                      </span>
                    ) : (
                      <span className="text-rose-400 flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" />
                        <span>ERROR</span>
                      </span>
                    )}
                  </td>

                  <td className="py-3 px-4 max-w-xs truncate text-slate-400">
                    {log.payloadPreview}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
