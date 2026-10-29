import React, { useState } from 'react';
import { 
  Play, 
  RotateCcw, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ChevronRight, 
  ChevronLeft,
  Terminal, 
  Layers, 
  Cpu, 
  ShieldAlert, 
  ArrowRight,
  ArrowDown
} from 'lucide-react';
import { AuditJob, LangGraphNode, Language } from '../types/audit';
import { LANGGRAPH_NODES } from '../services/agentEngine';

interface LangGraphVisualizerProps {
  job: AuditJob;
  language: Language;
  onNavigateTab: (tab: string) => void;
}

export const LangGraphVisualizer: React.FC<LangGraphVisualizerProps> = ({
  job,
  language,
  onNavigateTab,
}) => {
  const isAr = language === 'ar';
  const ArrowIcon = isAr ? ChevronLeft : ChevronRight;

  const [activeNodeKey, setActiveNodeKey] = useState<string>('hitl_gate');
  const [simulatedCurrentNodeIdx, setSimulatedCurrentNodeIdx] = useState<number>(6); // Default at HITL Gate
  const [isRunning, setIsRunning] = useState<boolean>(false);

  const selectedNode = LANGGRAPH_NODES.find(n => n.key === activeNodeKey) || LANGGRAPH_NODES[6];

  const handleStepNext = () => {
    if (simulatedCurrentNodeIdx < LANGGRAPH_NODES.length - 1) {
      // If at HITL gate (idx 6) and job is not approved, block step!
      if (simulatedCurrentNodeIdx === 6 && job.status !== 'approved') {
        alert(isAr 
          ? 'تنبيه أمني: توقف مسار التنفيذ عند بوابة HITL. لا يمكن الانتقال لعقدة كتابة السجل المركزي (mutate_commit) دون موافقة بشرية معتمدة!'
          : 'Security Barrier: Graph execution interrupted at HITL gate. Cannot proceed to mutate_commit without explicit human sign-off!'
        );
        return;
      }
      const nextIdx = simulatedCurrentNodeIdx + 1;
      setSimulatedCurrentNodeIdx(nextIdx);
      setActiveNodeKey(LANGGRAPH_NODES[nextIdx].key);
    }
  };

  const handleReset = () => {
    setSimulatedCurrentNodeIdx(0);
    setActiveNodeKey(LANGGRAPH_NODES[0].key);
    setIsRunning(false);
  };

  const handleRunFull = () => {
    setIsRunning(true);
    let current = 0;
    setSimulatedCurrentNodeIdx(0);
    setActiveNodeKey(LANGGRAPH_NODES[0].key);

    const interval = setInterval(() => {
      current++;
      if (current >= 6) {
        // Stop at HITL
        setSimulatedCurrentNodeIdx(6);
        setActiveNodeKey(LANGGRAPH_NODES[6].key);
        setIsRunning(false);
        clearInterval(interval);
      } else {
        setSimulatedCurrentNodeIdx(current);
        setActiveNodeKey(LANGGRAPH_NODES[current].key);
      }
    }, 700);
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Cpu className="w-3.5 h-3.5" />
            <span>LANGGRAPH STATEGRAPH RUNTIME · MEMORYSAVER CHECKPOINT</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            {isAr ? 'مخطط عُقد الوكيل الذكي (LangGraph State Machine)' : 'LangGraph DAG State Machine Visualizer'}
          </h1>
          <p className="mt-0.5 text-xs sm:text-sm text-slate-400">
            {isAr
              ? 'تتبع حي لمسار تنفيذ العُقد الثمانية، وفحص حالة المدخلات والمخرجات وأدوات FastMCP المستدعاة في كل خطوة.'
              : 'Interactive execution trace across the 8 agent graph nodes with live state inspection and FastMCP tool call tracking.'}
          </p>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunFull}
            disabled={isRunning}
            className="px-3.5 py-1.5 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{isAr ? 'تشغيل المسار' : 'Simulate Run'}</span>
          </button>
          <button
            onClick={handleStepNext}
            disabled={isRunning || simulatedCurrentNodeIdx >= LANGGRAPH_NODES.length - 1}
            className="px-3 py-1.5 text-xs font-medium text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-700 disabled:opacity-40 rounded-lg flex items-center gap-1 transition-colors"
          >
            <span>{isAr ? 'الخطوة التالية' : 'Next Node'}</span>
            <ArrowIcon className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleReset}
            className="p-1.5 text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
            title={isAr ? 'إعادة التعيين' : 'Reset'}
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Interactive Visual DAG Pipeline */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
          <span>{isAr ? 'مسار التدفق التسلسلي والتفرع الشرطي (DAG Topology):' : 'DAG Execution Topology & Conditional Branches:'}</span>
          <span className="font-mono text-[11px] text-cyan-400">
            {isAr ? 'العقدة النشطة حالياً:' : 'Active Node:'} {LANGGRAPH_NODES[simulatedCurrentNodeIdx].key}
          </span>
        </div>

        {/* Nodes Grid (Horizontal on lg, Vertical on mobile) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
          {LANGGRAPH_NODES.map((node, idx) => {
            const isPassed = idx < simulatedCurrentNodeIdx;
            const isCurrent = idx === simulatedCurrentNodeIdx;
            const isSelected = activeNodeKey === node.key;
            const isHitlNode = node.key === 'hitl_gate';
            const isCommitNode = node.key === 'mutate_commit';

            return (
              <div
                key={node.key}
                onClick={() => setActiveNodeKey(node.key)}
                className={`p-3 rounded-xl border text-start cursor-pointer transition-all flex flex-col justify-between min-h-[110px] relative ${
                  isSelected
                    ? 'ring-2 ring-cyan-400/80 bg-slate-800/90 border-cyan-500 shadow-md'
                    : isCurrent
                    ? 'bg-cyan-950/30 border-cyan-500/50'
                    : isPassed
                    ? 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                    : 'bg-slate-950/30 border-slate-900 opacity-60 hover:opacity-90'
                }`}
              >
                {/* Node Top Meta */}
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className={`${isCurrent ? 'text-cyan-400 font-bold' : 'text-slate-500'}`}>
                    0{idx+1}
                  </span>
                  {isPassed ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : isCurrent ? (
                    isHitlNode ? (
                      <Clock className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                    )
                  ) : isHitlNode ? (
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                  ) : null}
                </div>

                {/* Node Title */}
                <div className="my-1.5">
                  <div className="text-xs font-semibold text-slate-100 line-clamp-2 leading-tight">
                    {isAr ? node.nameAr : node.nameEn}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
                    {node.key}
                  </div>
                </div>

                {/* Node Footer Phase */}
                <div className="pt-1 border-t border-slate-800/60 text-[9px] font-mono flex items-center justify-between">
                  <span className={`${
                    node.phase === 'governance' ? 'text-amber-400' :
                    node.phase === 'commit' ? 'text-emerald-400' : 'text-slate-400'
                  }`}>
                    {node.phase}
                  </span>
                  {node.tools.some(t => t.includes('mcp')) && (
                    <span className="text-cyan-400" title="Uses MCP Server">MCP</span>
                  )}
                </div>

                {/* Branch marker for HITL Gate */}
                {isHitlNode && (
                  <div className="absolute -bottom-2 start-1/2 -translate-x-1/2 px-1 text-[8px] font-mono bg-amber-500/20 text-amber-300 rounded border border-amber-500/30 whitespace-nowrap">
                    {isAr ? 'نقطة توقف HITL' : 'HITL Checkpoint'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Node State Inspector & Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Node Metadata & Tools (5 cols) */}
        <div className="lg:col-span-5 rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                {isAr ? 'عقدة المسار المحددة' : 'Selected Graph Node'}
              </span>
              <h3 className="text-base font-bold text-white mt-0.5">
                {isAr ? selectedNode.nameAr : selectedNode.nameEn}
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
              {selectedNode.phase}
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {isAr ? selectedNode.descriptionAr : selectedNode.descriptionEn}
          </p>

          {/* Tools Called */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'الأدوات المستدعاة في هذه العقدة:' : 'Tools Dispatched by Node:'}</span>
            </span>

            <div className="space-y-1.5">
              {selectedNode.tools.map((tool, i) => {
                const isMcp = tool.includes('mcp');
                return (
                  <div key={i} className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-200">{tool}()</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      isMcp ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/60' : 'bg-slate-900 text-slate-400'
                    }`}>
                      {isMcp ? 'FastMCP Protocol' : 'Internal Engine'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* HITL Notice if inspecting HITL Gate */}
          {selectedNode.key === 'hitl_gate' && (
            <div className="p-3.5 rounded-lg bg-amber-950/20 border border-amber-800/60 text-xs text-amber-200 space-y-1.5">
              <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                <Clock className="w-4 h-4" />
                <span>{isAr ? 'حاجز الأمان والاعتماد البشري (HITL Gate)' : 'Human-in-the-Loop Interruption'}</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                {isAr
                  ? 'هذه العقدة تستخدم MemorySaver لإيقاف الرسم البياني مؤقتًا وحفظ حالته. لا يُسمح بتجاوز هذه النقطة إلى عقدة mutate_commit إلا بتوقيع بشري معتمد.'
                  : 'Interrupts graph execution and checkpoints state. Node mutate_commit cannot be executed without cryptographic approval.'}
              </p>
              <button
                onClick={() => onNavigateTab('hitl')}
                className="mt-1 px-3 py-1.5 text-[11px] font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded transition-colors"
              >
                {isAr ? 'فتح شاشة الاعتماد الآن' : 'Open HITL Approval Gate'}
              </button>
            </div>
          )}
        </div>

        {/* Input / Output Schema Inspector (7 cols) */}
        <div className="lg:col-span-7 rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>{isAr ? 'مخطط البيانات وحالة الذاكرة (AuditState Payload)' : 'AuditState Input / Output Contracts'}</span>
            </span>
            <span className="text-[10px] font-mono text-slate-400">TypedDict AuditState</span>
          </div>

          <div className="space-y-3 flex-1 flex flex-col">
            <div>
              <div className="text-[11px] font-mono text-slate-400 mb-1">
                {isAr ? 'عقد المدخلات (Input Schema):' : 'Input Contract (Schema):'}
              </div>
              <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 font-mono text-xs text-cyan-300 overflow-x-auto">
                {selectedNode.inputSchema}
              </div>
            </div>

            <div className="flex-1">
              <div className="text-[11px] font-mono text-slate-400 mb-1">
                {isAr ? 'عقد المخرجات (Output Schema):' : 'Output Contract (Schema):'}
              </div>
              <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 font-mono text-xs text-emerald-300 overflow-x-auto">
                {selectedNode.outputSchema}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-mono text-slate-400 mb-1">
                {isAr ? 'عينة من حمولة الحالة الحية (Runtime State Snapshot):' : 'Runtime State Snapshot:'}
              </div>
              <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 font-mono text-[11px] text-slate-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
{JSON.stringify({
  node: selectedNode.key,
  job_id: job.id,
  risk_score: job.riskScore,
  status: job.status,
  hitl_checkpoint: selectedNode.key === 'hitl_gate' ? 'PAUSED_AWAITING_SIGNATURE' : 'PASS_THROUGH',
  tools_invoked: selectedNode.tools,
  timestamp: new Date().toISOString()
}, null, 2)}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
