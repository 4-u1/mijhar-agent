import React, { useEffect, useState } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  Unlock, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  FileEdit, 
  FileText,
  KeyRound,
  Database,
  ArrowRight,
  ArrowLeft,
  Stamp
} from 'lucide-react';
import { AuditJob, HITLDecision, Language } from '../types/audit';
import { SYNTHETIC_BENCHMARKS } from '../data/syntheticBenchmarks';
import { auditAndDecide, backendAvailable, API_URL } from '../services/api';

interface HITLApprovalModalProps {
  job: AuditJob;
  onDecisionSubmitted: (decision: HITLDecision) => void;
  language: Language;
}

export const HITLApprovalModal: React.FC<HITLApprovalModalProps> = ({
  job,
  onDecisionSubmitted,
  language,
}) => {
  const isAr = language === 'ar';
  const ArrowIcon = isAr ? ArrowLeft : ArrowRight;

  const benchmark = SYNTHETIC_BENCHMARKS.find(b => b.job.id === job.id) || SYNTHETIC_BENCHMARKS[0];

  const [reviewerName, setReviewerName] = useState<string>('');
  const [reviewerRole, setReviewerRole] = useState<string>('كبير مدققي نظم الذكاء الاصطناعي - معتمد من سدايا');
  const [comments, setComments] = useState<string>('');
  const [reviewerKey, setReviewerKey] = useState<string>('');
  const [clientKey, setClientKey] = useState<string>('');
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  useEffect(() => { backendAvailable().then(setBackendUp); }, []);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedReceipt, setSubmittedReceipt] = useState<HITLDecision | null>(job.hitlDecision || null);

  const isPending = job.status === 'hitl_pending' && !submittedReceipt;

  const handleDecision = async (decisionType: 'approved' | 'rejected' | 'revisions_requested') => {
    if (!comments.trim()) {
      setErrorMsg(isAr ? 'يرجى كتابة الملاحظات ومبررات القرار الرقابي قبل الاعتماد.' : 'Please provide mandatory audit rationale and reviewer notes.');
      return;
    }
    if (!reviewerName.trim() || !reviewerKey || !clientKey) {
      setErrorMsg(isAr ? 'معرّف المدقق ومفتاحه ومفتاح الواجهة مطلوبة.' : 'Reviewer ID, reviewer key and API key are required.');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);
    const wire = decisionType === 'approved' ? 'approve' : decisionType === 'rejected' ? 'reject' : 'revise';
    try {
      // The signature is issued by the backend only after the reviewer authenticates, and the
      // write happens there. Nothing in this component can mutate state or forge a signature.
      const out = await auditAndDecide({
        text: `${job.titleEn}\n${job.summaryEn}\n${job.sourceDocument}`,
        filename: `${job.id}.txt`, reviewer: reviewerName.trim(), reviewerKey, clientKey, decision: wire,
      });
      const committed = out.status === 'committed';
      const decision: HITLDecision = {
        jobId: job.id,
        decision: decisionType,
        reviewerName: out.reviewer ?? reviewerName,
        reviewerRole,
        comments,
        timestamp: (out.timestamp ?? new Date().toISOString()).replace('T', ' ').slice(0, 19),
        signatureHash: out.txHash ?? out.reportSha256,
        writeOperationPermitted: committed,
        affectedDatabaseMutation: committed ? {
          table: 'national_audit_registry',
          action: 'PUBLISH_CERTIFICATE',
          recordId: `CERT-${job.id}-SDAIA`,
        } : undefined,
      };
      setSubmittedReceipt(decision);
      onDecisionSubmitted(decision);
    } catch (e: any) {
      // Fail closed: on any error nothing is recorded and the job stays pending.
      setErrorMsg((isAr ? 'لم يُسجَّل القرار: ' : 'Decision NOT recorded: ') + (e?.message ?? 'unknown error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* View Header */}
      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2 text-xs font-mono text-amber-400 mb-1">
          <Lock className="w-3.5 h-3.5" />
          <span>HUMAN-IN-THE-LOOP (HITL) STATE MUTATION GATE</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          {isAr ? 'محطة المراجعة البشرية واعتماد الإجراءات الرقابية' : 'Human-in-the-Loop Governance & Authorization Gate'}
        </h1>
        <p className="mt-0.5 text-xs sm:text-sm text-slate-400">
          {isAr
            ? 'تطبيق لمبدأ الأمان الصارم: يمنع الوكيل من تنفيذ أي عمليات كتابة أو تعديل على قواعد البيانات دون التحقق من هوية وتوقيع المدقق البشري.'
            : 'Enforces strict agent safety: The autonomous agent is strictly forbidden from mutating central state or issuing certifications without verified human credentials.'}
        </p>
      </div>

      {/* Target Document & Risk Summary Card */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <div className="text-xs font-mono text-cyan-400">{job.id}</div>
            <h2 className="text-base font-bold text-white mt-0.5">
              {isAr ? job.titleAr : job.titleEn}
            </h2>
          </div>
          <div className="flex items-center gap-3 self-start sm:self-auto">
            <div className="text-end">
              <div className="text-[11px] text-slate-400">{isAr ? 'مؤشر الخطر الإجمالي' : 'Risk Rating'}</div>
              <div className={`text-base font-bold font-mono ${
                job.riskScore > 70 ? 'text-rose-400' : job.riskScore > 40 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {job.riskScore}/100
              </div>
            </div>
          </div>
        </div>

        {/* Flagged Issues Checklist */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
            <div className="font-semibold text-slate-200 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>{isAr ? 'التناقضات المرصودة للتحقق البشري:' : 'Contradictions Requiring Adjudication:'}</span>
            </div>
            <ul className="space-y-1.5 text-slate-300">
              {benchmark.claims.filter(c => c.status === 'contradicted').map((c) => (
                <li key={c.id} className="p-2 rounded bg-rose-950/20 border border-rose-900/40 text-[11px]">
                  <strong>{c.id}:</strong> {isAr ? c.textAr : c.textEn}
                </li>
              ))}
            </ul>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
            <div className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Database className="w-4 h-4 text-cyan-400" />
              <span>{isAr ? 'الإجراء المراد تنفيذه (Database Mutation):' : 'Pending State Mutation Target:'}</span>
            </div>
            <div className="text-slate-300 text-[11px] space-y-1 font-mono">
              <div>السجل المستهدف: <span className="text-white">national_audit_registry</span></div>
              <div>العملية المطلوبة: <span className="text-amber-400">PUBLISH_CERTIFICATE & INSERT</span></div>
              <div>حالة القفل: <span className={submittedReceipt?.writeOperationPermitted ? 'text-emerald-400' : 'text-rose-400'}>
                {submittedReceipt?.writeOperationPermitted ? (isAr ? '🔓 تم إلغاء القفل بتفويض بشري' : '🔓 Unlocked via verified signature') : (isAr ? '🔒 مقفول ومحمي بحاجز الأمان' : '🔒 Locked by security boundary')}
              </span></div>
            </div>
          </div>
        </div>
      </div>

      {/* Decision Form or Receipt */}
      {submittedReceipt ? (
        <div className="rounded-xl bg-slate-900/80 border border-emerald-500/40 p-6 space-y-4 shadow-lg shadow-emerald-950/20">
          <div className="flex items-center gap-3 text-emerald-400 border-b border-slate-800 pb-3">
            <Stamp className="w-6 h-6" />
            <div>
              <h3 className="text-base font-bold text-white">
                {isAr ? 'إيصال التوثيق الرقمي المعتمد للقرار البشري' : 'Immutable Cryptographic Audit Receipt'}
              </h3>
              <p className="text-xs text-slate-400">
                {isAr ? 'تم تسجيل القرار واعتماده بصمة التشفير الآمنة' : 'Signed and committed with SHA-256 cryptographic proof.'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1 text-slate-300">
              <div className="text-slate-500">{isAr ? 'المدقق المعتمد:' : 'Certified Reviewer:'}</div>
              <div className="text-white font-sans font-semibold">{submittedReceipt.reviewerName}</div>
              <div className="text-[11px] text-slate-400">{submittedReceipt.reviewerRole}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1 text-slate-300">
              <div className="text-slate-500">{isAr ? 'القرار الرقابي:' : 'Decision Issued:'}</div>
              <div className={`font-bold ${
                submittedReceipt.decision === 'approved' ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {submittedReceipt.decision.toUpperCase()} · {submittedReceipt.writeOperationPermitted ? (isAr ? 'تفويض الكتابة مفعل' : 'Write Permitted') : (isAr ? 'الكتابة محظورة' : 'Write Blocked')}
              </div>
              <div className="text-[11px] text-slate-400">{submittedReceipt.timestamp}</div>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1">
            <div className="text-[11px] text-slate-500">{isAr ? 'الملاحظات الرقابية:' : 'Reviewer Rationale:'}</div>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {submittedReceipt.comments}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1 font-mono text-xs">
            <div className="text-slate-500 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'بصمة التوقيع الرقمي (Signature Hash):' : 'Cryptographic Signature Hash:'}</span>
            </div>
            <div className="text-cyan-400 text-[11px] break-all">
              {submittedReceipt.signatureHash}
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-6 space-y-5">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <span>{isAr ? 'نموذج اعتماد المدقق البشري المرخص' : 'Certified Auditor Adjudication Form'}</span>
            </h3>
            <span className="text-xs font-mono text-amber-400">
              {isAr ? 'مطلوب للمتابعة' : 'Required for Progression'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">
                {isAr ? 'اسم المدقق المسؤول:' : 'Auditor Full Name:'}
              </label>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">
                {isAr ? 'الصفة الوظيفية والاعتماد:' : 'Professional Accreditation / Role:'}
              </label>
              <input
                type="text"
                value={reviewerRole}
                onChange={(e) => setReviewerRole(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">
              {isAr ? 'الملاحظات الرقابية ومبررات القرار:' : 'Regulatory Rationale & Audit Notes:'}
            </label>
            <textarea
              rows={3}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder={isAr ? 'اكتب الملاحظات التفصيلية حول التناقضات أو التوصيات بالإجراء اللازم...' : 'Enter your audit evaluation, risk assessment, and justification for this decision...'}
              className="w-full p-3 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 leading-relaxed"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">{isAr ? 'مفتاح المدقق (لا يُحفظ):' : 'Reviewer key (not stored):'}</label>
              <input type="password" autoComplete="off" value={reviewerKey} onChange={(e) => setReviewerKey(e.target.value)}
                dir="ltr" className="w-full px-3 py-2 text-xs font-mono bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">{isAr ? 'مفتاح الواجهة API (لا يُحفظ):' : 'API key (not stored):'}</label>
              <input type="password" autoComplete="off" value={clientKey} onChange={(e) => setClientKey(e.target.value)}
                dir="ltr" className="w-full px-3 py-2 text-xs font-mono bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500" />
            </div>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed" role="status">
            {backendUp === false
              ? (isAr ? `الخادم غير متصل (${API_URL}). لا يمكن توقيع أي قرار أو تسجيله.` : `Backend not reachable (${API_URL}). No decision can be signed or recorded.`)
              : (isAr ? 'يُوقَّع القرار ويُنفَّذ في الخادم فقط بعد مصادقة المدقق.' : 'The decision is signed and executed on the server only after reviewer authentication.')}
          </p>
          {errorMsg && <p className="text-xs text-red-400" role="alert">{errorMsg}</p>}

          {/* Action Decision Buttons */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-end gap-3 border-t border-slate-800">
            <button
              onClick={() => handleDecision('rejected')}
              disabled={isSubmitting || backendUp === false}
              className="w-full sm:w-auto px-4 py-2.5 text-xs font-semibold text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/80 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <XCircle className="w-4 h-4 text-rose-400" />
              <span>{isAr ? 'رفض العملية وحظر الكتابة' : 'Reject & Block State Mutation'}</span>
            </button>

            <button
              onClick={() => handleDecision('revisions_requested')}
              disabled={isSubmitting || backendUp === false}
              className="w-full sm:w-auto px-4 py-2.5 text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <FileEdit className="w-4 h-4 text-amber-400" />
              <span>{isAr ? 'طلب مراجعة وتعديلات إضافية' : 'Request Revisions'}</span>
            </button>

            <button
              onClick={() => handleDecision('approved')}
              disabled={isSubmitting || backendUp === false}
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg shadow-sm transition-colors flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4 text-slate-950" />
              <span>{isAr ? 'اعتماد العملية وتفويض الكتابة' : 'Approve & Permit Database Mutation'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
