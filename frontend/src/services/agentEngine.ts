// CLIENT-SIDE DEMO ONLY. The scanner below is a lightweight illustration used by the Upload and Red-Team tabs.
// It is NOT a security boundary. The real guard (Unicode/Arabic normalisation, redaction, fail-closed) is
// backend/mijhar/guard.py. The former placeholder retrieval scorers (random, non-BM25) were removed.
import { AuditJob, Claim, EvidenceItem, SecurityThreat, AuditStepLog, HITLDecision, LangGraphNode } from '../types/audit';

export const LANGGRAPH_NODES: LangGraphNode[] = [
  {
    id: 'node-1',
    key: 'ingest_document',
    nameAr: 'استيعاب المستند وتجزئته',
    nameEn: 'Document Ingestion & Chunking',
    descriptionAr: 'قراءة المستند وحساب بصمة SHA-256 وتقسيمه إلى مقاطع دلالية مع حفظ إحداثيات كل فقرة.',
    descriptionEn: 'Reads document buffer, computes cryptographic hash, splits into semantic chunks with provenance offsets.',
    phase: 'preprocess',
    tools: ['doc_parser_mcp', 'hash_generator'],
    inputSchema: '{ raw_document: bytes | string, filename: string, mime_type: string }',
    outputSchema: '{ document_id: string, chunks: Chunk[], sha256: string, token_count: number }',
  },
  {
    id: 'node-2',
    key: 'security_guardrail',
    nameAr: 'درع فحص حقن الأوامر (Prompt Injection)',
    nameEn: 'Adversarial & Injection Guardrail',
    descriptionAr: 'مسح المستند لاكتشاف أي تعليمات خفية أو محاولات تجاوز صلاحيات النموذج (Indirect Prompt Injection).',
    descriptionEn: 'Scans text against indirect prompt injections, canary leakage, and hidden instruction overrides before LLM context.',
    phase: 'analysis',
    tools: ['prompt_armor_guard', 'canary_validator'],
    inputSchema: '{ chunks: Chunk[], context_scope: string }',
    outputSchema: '{ is_safe: boolean, threats_detected: SecurityThreat[], sanitized_chunks: Chunk[] }',
  },
  {
    id: 'node-3',
    key: 'extract_claims',
    nameAr: 'استخراج الادعاءات الفنية والقانونية',
    nameEn: 'Proposition & Claim Extraction',
    descriptionAr: 'تفكيك النص إلى ادعاءات ذرية قابلة للتحقق وربط كل ادعاء بالمقطع الأصلي ومؤشر الثقة.',
    descriptionEn: 'Decomposes clauses into atomic verifiable propositions linked to document coordinates and confidence ratings.',
    phase: 'analysis',
    tools: ['claim_extractor', 'entity_normalizer'],
    inputSchema: '{ sanitized_chunks: Chunk[] }',
    outputSchema: '{ claims: Claim[], total_claims: number }',
  },
  {
    id: 'node-4',
    key: 'hybrid_retrieval',
    nameAr: 'الاسترجاع الهجين (BM25 + تضمين متجهي)',
    nameEn: 'Hybrid Retrieval Engine (BM25 + Dense)',
    descriptionAr: 'استعلام المراجع التنظيمية والأنظمة الوطنية باستخدام مطابقة الكلمات المفتاحية BM25 والتضمين الدلالي المتجهي.',
    descriptionEn: 'Queries statutory corpora using Reciprocal Rank Fusion (RRF) between lexical BM25 and dense embeddings.',
    phase: 'verification',
    tools: ['hybrid_search_mcp', 'dense_vector_store'],
    inputSchema: '{ claims: Claim[], top_k: number, min_hybrid_score: number }',
    outputSchema: '{ claim_evidence_map: Record<string, EvidenceItem[]> }',
  },
  {
    id: 'node-5',
    key: 'verify_evidence',
    nameAr: 'مضاهاة الأدلة وتحديد الموقف (Stance)',
    nameEn: 'Evidence Cross-Verification & Stance',
    descriptionAr: 'تحليل العلاقة المنطقية بين كل ادعاء والأدلة المسترجعة (مؤيد / معارض / محايد) باستخدام نموذج Cross-Encoder.',
    descriptionEn: 'Performs natural language inference (NLI) to classify evidence as supporting, refuting, or neutral.',
    phase: 'verification',
    tools: ['cross_encoder_verifier', 'confidence_calibrator'],
    inputSchema: '{ claims: Claim[], claim_evidence_map: Record<string, EvidenceItem[]> }',
    outputSchema: '{ verified_claims: Claim[], overall_confidence: number }',
  },
  {
    id: 'node-6',
    key: 'detect_contradictions',
    nameAr: 'رصد التناقضات وحساب المخاطر',
    nameEn: 'Contradiction Detection & Risk Scoring',
    descriptionAr: 'تحديد التناقضات المباشرة مع الأنظمة الرسمية أو التناقضات الذاتية داخل الوثيقة، واحتساب مؤشر الخطر الإجمالي.',
    descriptionEn: 'Aggregates irreconcilable factual divergences and calculates deterministic composite risk index.',
    phase: 'verification',
    tools: ['contradiction_resolver', 'risk_scorer'],
    inputSchema: '{ verified_claims: Claim[], threats: SecurityThreat[] }',
    outputSchema: '{ risk_score: number, contradiction_summary: string, requires_hitl: boolean }',
  },
  {
    id: 'node-7',
    key: 'hitl_gate',
    nameAr: 'بوابة المراجعة والاعتماد البشري (HITL)',
    nameEn: 'Human-in-the-Loop Governance Gate',
    descriptionAr: 'إيقاف مسار التنفيذ التلقائي وعرض الفروقات والنتائج على المدقق البشري المرخص لاعتماد التقرير أو رفضه.',
    descriptionEn: 'Interrupts autonomous graph execution with MemorySaver state checkpoint until explicit human signature.',
    phase: 'governance',
    tools: ['hitl_permission_gate', 'digital_signature_validator'],
    inputSchema: '{ audit_payload: AuditReport, risk_score: number, requires_hitl: boolean }',
    outputSchema: '{ hitl_decision: HITLDecision, write_permitted: boolean }',
  },
  {
    id: 'node-8',
    key: 'mutate_commit',
    nameAr: 'تنفيذ الإجراء وكتابة السجل المركزي',
    nameEn: 'Central Registry Mutation Commit',
    descriptionAr: 'لا يُنفذ إلا بعد التحقق من الموافقة البشرية الصريحة والصلاحيات، لتحديث السجل المركزي أو إصدار شهادة التدقيق.',
    descriptionEn: 'Enforces permission barrier; only commits database mutations or webhook dispatch if authorized by human decision.',
    phase: 'commit',
    tools: ['execute_audit_action_mcp', 'audit_ledger_writer'],
    inputSchema: '{ hitl_decision: HITLDecision, target_system: string, payload: any }',
    outputSchema: '{ transaction_hash: string, published_status: string, timestamp: string }',
  },
];

// Security injection attack signatures for detection
export const INJECTION_PATTERNS = [
  /\[SYSTEM\s*(INSTRUCTION|COMMAND|OVERRIDE).*?\]/i,
  /ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules|prompts)/i,
  /print\s+(the\s+)?(env|environment|variables|api\s*key|secret)/i,
  /disregard\s+(all\s+)?(security|ethics|evaluations|contradictions)/i,
  /<!--\s*IMPORTANT.*?-->/i,
  /!\s*\[.*?\]\(https?:\/\/.*?leak.*?\)/i,
  /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/i,
  /system_role:\s*admin/i,
];

/**
 * Client-side guardrail scanner for detecting prompt injections and adversarial payloads
 */
export function scanForPromptInjections(text: string, jobId: string): SecurityThreat[] {
  const threats: SecurityThreat[] = [];

  INJECTION_PATTERNS.forEach((pattern, index) => {
    const match = text.match(pattern);
    if (match) {
      threats.push({
        id: `THR-${Date.now()}-${index}`,
        jobId,
        attackType: pattern.toString().includes('ignore') ? 'instruction_override' :
                    pattern.toString().includes('print') || pattern.toString().includes('leak') ? 'data_exfiltration_canary' :
                    'indirect_prompt_injection',
        severity: 'critical',
        rawPayload: match[0],
        detectedLocationAr: `تم الرصد عند الإزاحة النصية: ${match.index ?? 0}`,
        detectedLocationEn: `Detected at character offset: ${match.index ?? 0}`,
        containmentStatus: 'blocked',
        mitigationNotesAr: 'تم اعتراض نمط حقن الأوامر وعزله بواسطة درع الأمان لمنع اختراق نموذج التدقيق.',
        mitigationNotesEn: 'Prompt injection pattern intercepted and isolated by security guardrail, preventing context leakage.',
        confidenceScore: 0.985,
        timestamp: new Date().toISOString(),
      });
    }
  });

  return threats;
}
