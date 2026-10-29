import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle, 
  ExternalLink, 
  Search, 
  Filter, 
  BookOpen, 
  Layers, 
  Scale,
  Sparkles,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';
import { AuditJob, Claim, EvidenceItem, Language, ClaimStatus } from '../types/audit';
import { SYNTHETIC_BENCHMARKS } from '../data/syntheticBenchmarks';

interface ClaimDetailViewProps {
  job: AuditJob;
  language: Language;
  onNavigateTab: (tab: string) => void;
}

export const ClaimDetailView: React.FC<ClaimDetailViewProps> = ({
  job,
  language,
  onNavigateTab,
}) => {
  const isAr = language === 'ar';
  
  // Find current benchmark scenario
  const benchmark = SYNTHETIC_BENCHMARKS.find(b => b.job.id === job.id) || SYNTHETIC_BENCHMARKS[0];
  const claims = benchmark.claims;

  const [selectedClaimId, setSelectedClaimId] = useState<string>(claims[0]?.id || '');
  const [statusFilter, setStatusFilter] = useState<'all' | ClaimStatus>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const selectedClaim = claims.find(c => c.id === selectedClaimId) || claims[0];
  const relatedEvidence: EvidenceItem[] = selectedClaim ? (benchmark.evidenceMap[selectedClaim.id] || []) : [];

  const filteredClaims = claims.filter(c => {
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const textToSearch = isAr ? c.textAr : c.textEn;
    const matchesQuery = textToSearch.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesQuery;
  });

  const supportingEvidence = relatedEvidence.filter(e => e.stance === 'supports');
  const contradictingEvidence = relatedEvidence.filter(e => e.stance === 'refutes');

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs font-mono text-cyan-400 mb-1">
            {job.id} · {isAr ? job.categoryAr : job.categoryEn}
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            {isAr ? 'مصفوفة الادعاءات وتدقيق الأدلة والتناقضات' : 'Claims & Evidence Contradiction Matrix'}
          </h1>
          <p className="mt-0.5 text-xs sm:text-sm text-slate-400">
            {isAr 
              ? 'مقارنة كل ادعاء بالأدلة النظامية المسترجعة عبر الاسترجاع الهجين، وتصنيف الأدلة إلى مؤيدة ومعارضة مع رصد التناقضات.'
              : 'Cross-verifying claims against regulatory corpora retrieved via hybrid fusion; classifying supporting vs. contradicting evidence.'}
          </p>
        </div>

        {job.status === 'hitl_pending' && (
          <button
            onClick={() => onNavigateTab('hitl')}
            className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap self-start md:self-auto shadow-sm"
          >
            {isAr ? 'الانتقال لبوابة الاعتماد البشري' : 'Review in HITL Station'}
          </button>
        )}
      </div>

      {/* Main Layout: Claims List (4 cols) + Evidence & Contradiction Detail (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Claims Directory (5 cols) */}
        <div className="lg:col-span-5 rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-3 flex flex-col">
          {/* Search & Filter Bar */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute top-2.5 start-3 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={isAr ? 'بحث في الادعاءات المستخرجة...' : 'Search claims...'}
                className="w-full py-2 ps-9 pe-3 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Filter Tabs (Interactive segmented buttons allowed under skill) */}
            <div className="flex items-center gap-1 p-1 bg-slate-950/80 rounded-lg border border-slate-800 text-[11px] overflow-x-auto">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
                  statusFilter === 'all' ? 'bg-slate-800 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'الكل' : 'All'} ({claims.length})
              </button>
              <button
                onClick={() => setStatusFilter('contradicted')}
                className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
                  statusFilter === 'contradicted' ? 'bg-rose-950/60 text-rose-300 font-medium' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'تناقضات' : 'Contradicted'} ({claims.filter(c => c.status === 'contradicted').length})
              </button>
              <button
                onClick={() => setStatusFilter('verified')}
                className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
                  statusFilter === 'verified' ? 'bg-emerald-950/60 text-emerald-300 font-medium' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'موثقة' : 'Verified'} ({claims.filter(c => c.status === 'verified').length})
              </button>
              <button
                onClick={() => setStatusFilter('inconclusive')}
                className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
                  statusFilter === 'inconclusive' ? 'bg-amber-950/60 text-amber-300 font-medium' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {isAr ? 'غير محسومة' : 'Inconclusive'} ({claims.filter(c => c.status === 'inconclusive').length})
              </button>
            </div>
          </div>

          {/* Claims List */}
          <div className="space-y-2 flex-1 overflow-y-auto max-h-[560px]">
            {filteredClaims.map((claim) => {
              const isSelected = selectedClaim?.id === claim.id;
              return (
                <div
                  key={claim.id}
                  onClick={() => setSelectedClaimId(claim.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-slate-800/90 border-cyan-500 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] mb-1.5">
                    <span className="font-mono text-cyan-400 font-medium">{claim.id}</span>
                    <span className={`font-medium ${
                      claim.status === 'contradicted' ? 'text-rose-400' :
                      claim.status === 'verified' ? 'text-emerald-400' : 'text-amber-400'
                    }`}>
                      {claim.status === 'contradicted' ? (isAr ? 'تناقض نظامي' : 'Contradicted') :
                       claim.status === 'verified' ? (isAr ? 'موثق بمصدر' : 'Verified') :
                       (isAr ? 'غير محسوم' : 'Inconclusive')}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 font-medium line-clamp-2 leading-relaxed">
                    {isAr ? claim.textAr : claim.textEn}
                  </p>

                  <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-2">
                    <span>{isAr ? claim.documentSectionAr : claim.documentSectionEn}</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono">{claim.offset}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Claim Evidence Deep-Dive Inspector (7 cols) */}
        {selectedClaim ? (
          <div className="lg:col-span-7 space-y-6">
            
            {/* Selected Claim Banner */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-cyan-400 font-bold">{selectedClaim.id}</span>
                  <span className="text-slate-500">·</span>
                  <span className="text-slate-400">{isAr ? selectedClaim.documentSectionAr : selectedClaim.documentSectionEn}</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-slate-400">{isAr ? 'نسبة الثقة في الاستخراج:' : 'Extraction Confidence:'}</span>
                  <span className="font-mono font-bold text-white tabular-nums">
                    {(selectedClaim.confidenceScore * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 text-sm font-medium text-white leading-relaxed">
                "{isAr ? selectedClaim.textAr : selectedClaim.textEn}"
              </div>

              {/* Contradiction / Verification Explanation Box */}
              <div className={`p-3.5 rounded-lg border text-xs leading-relaxed ${
                selectedClaim.status === 'contradicted' ? 'bg-rose-950/20 border-rose-800/60 text-rose-200' :
                selectedClaim.status === 'verified' ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-200' :
                'bg-amber-950/20 border-amber-800/60 text-amber-200'
              }`}>
                <div className="flex items-center gap-1.5 font-semibold mb-1">
                  {selectedClaim.status === 'contradicted' && <AlertTriangle className="w-4 h-4 text-rose-400" />}
                  {selectedClaim.status === 'verified' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                  {selectedClaim.status === 'inconclusive' && <HelpCircle className="w-4 h-4 text-amber-400" />}
                  <span>
                    {selectedClaim.status === 'contradicted' ? (isAr ? 'تفاصيل التناقض المرصود:' : 'Contradiction Analysis:') :
                     selectedClaim.status === 'verified' ? (isAr ? 'سند التحقق المرجعي:' : 'Verification Basis:') :
                     (isAr ? 'سبب عدم الحسم:' : 'Inconclusive Analysis:')}
                  </span>
                </div>
                <p className="text-slate-300">
                  {isAr ? selectedClaim.explanationAr : selectedClaim.explanationEn}
                </p>
              </div>
            </div>

            {/* Contradicting Evidence Section */}
            {contradictingEvidence.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{isAr ? 'أدلة نظامية معارضة ومناقضة (Refuting Evidence):' : 'Refuting & Contradicting Evidence:'}</span>
                </div>

                {contradictingEvidence.map((ev) => (
                  <div key={ev.id} className="p-4 rounded-xl bg-slate-900/60 border border-rose-900/40 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-rose-300">
                        {isAr ? ev.titleAr : ev.titleEn}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">{ev.publicationDate}</span>
                    </div>

                    <p className="text-xs text-slate-300 bg-slate-950/80 p-3 rounded-lg border border-slate-800 leading-relaxed">
                      "{isAr ? ev.excerptAr : ev.excerptEn}"
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] pt-1">
                      <div className="flex items-center gap-2 text-slate-400">
                        <span>{isAr ? ev.sourceAuthorityAr : ev.sourceAuthorityEn}</span>
                        <span aria-hidden="true">·</span>
                        <a
                          href={ev.referenceUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline flex items-center gap-1"
                        >
                          <span>{isAr ? 'المرجع الرسمي' : 'Statutory Reference'}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      {/* Score Metrics (BM25, Dense, Hybrid) */}
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span>BM25: <strong className="text-slate-200">{ev.bm25Score}</strong></span>
                        <span aria-hidden="true">/</span>
                        <span>Dense: <strong className="text-slate-200">{ev.denseScore}</strong></span>
                        <span aria-hidden="true">/</span>
                        <span>Hybrid: <strong className="text-cyan-400">{ev.hybridScore}</strong></span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Supporting Evidence Section */}
            {supportingEvidence.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{isAr ? 'أدلة نظامية مؤيدة ومعتمدة (Supporting Evidence):' : 'Supporting Evidence:'}</span>
                </div>

                {supportingEvidence.map((ev) => (
                  <div key={ev.id} className="p-4 rounded-xl bg-slate-900/60 border border-emerald-900/40 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-emerald-300">
                        {isAr ? ev.titleAr : ev.titleEn}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">{ev.publicationDate}</span>
                    </div>

                    <p className="text-xs text-slate-300 bg-slate-950/80 p-3 rounded-lg border border-slate-800 leading-relaxed">
                      "{isAr ? ev.excerptAr : ev.excerptEn}"
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] pt-1">
                      <div className="flex items-center gap-2 text-slate-400">
                        <span>{isAr ? ev.sourceAuthorityAr : ev.sourceAuthorityEn}</span>
                        <span aria-hidden="true">·</span>
                        <a
                          href={ev.referenceUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline flex items-center gap-1"
                        >
                          <span>{isAr ? 'المرجع الرسمي' : 'Official Citation'}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span>BM25: <strong className="text-slate-200">{ev.bm25Score}</strong></span>
                        <span aria-hidden="true">/</span>
                        <span>Dense: <strong className="text-slate-200">{ev.denseScore}</strong></span>
                        <span aria-hidden="true">/</span>
                        <span>Hybrid: <strong className="text-cyan-400">{ev.hybridScore}</strong></span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        ) : (
          <div className="lg:col-span-7 flex items-center justify-center p-12 rounded-xl bg-slate-900/40 border border-slate-800 text-slate-500 text-sm">
            {isAr ? 'حدد أي ادعاء من القائمة لعرض تفاصيل الأدلة والتناقضات' : 'Select a claim to inspect its evidence and contradiction profile.'}
          </div>
        )}

      </div>
    </div>
  );
};
