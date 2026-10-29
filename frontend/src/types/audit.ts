export type Language = 'ar' | 'en';

export type AuditStatus = 'queued' | 'processing' | 'hitl_pending' | 'approved' | 'rejected' | 'completed';

export type ClaimStatus = 'verified' | 'contradicted' | 'unsubstantiated' | 'inconclusive';

export type EvidenceStance = 'supports' | 'refutes' | 'neutral';

export type RetrievalMethod = 'bm25' | 'dense_embedding' | 'hybrid';

export type ThreatSeverity = 'critical' | 'high' | 'medium';

export type AttackVector = 
  | 'indirect_prompt_injection'
  | 'instruction_override'
  | 'jailbreak_attempt'
  | 'data_exfiltration_canary'
  | 'system_prompt_leakage';

export interface AuditJob {
  id: string;
  titleAr: string;
  titleEn: string;
  categoryAr: string;
  categoryEn: string;
  sourceDocument: string;
  date: string;
  status: AuditStatus;
  riskScore: number; // 0 - 100
  claimsCount: number;
  verifiedCount: number;
  contradictionsCount: number;
  inconclusiveCount: number;
  injectionsDetected: number;
  summaryAr: string;
  summaryEn: string;
  targetSystem: string;
  totalTokens: number;
  totalCostUsd: number;
  totalDurationMs: number;
  hitlDecision?: HITLDecision;
}

export interface Claim {
  id: string;
  jobId: string;
  textAr: string;
  textEn: string;
  documentSectionAr: string;
  documentSectionEn: string;
  offset: string;
  confidenceScore: number; // 0.0 - 1.0
  status: ClaimStatus;
  supportingCount: number;
  contradictingCount: number;
  explanationAr: string;
  explanationEn: string;
  extractedAt: string;
}

export interface EvidenceItem {
  id: string;
  claimId: string;
  titleAr: string;
  titleEn: string;
  excerptAr: string;
  excerptEn: string;
  sourceAuthorityAr: string;
  sourceAuthorityEn: string;
  publicationDate: string;
  retrievalMethod: RetrievalMethod;
  bm25Score: number;
  denseScore: number;
  hybridScore: number;
  stance: EvidenceStance;
  referenceUrl: string;
  verifiedTimestamp: string;
}

export interface SecurityThreat {
  id: string;
  jobId: string;
  attackType: AttackVector;
  severity: ThreatSeverity;
  rawPayload: string;
  detectedLocationAr: string;
  detectedLocationEn: string;
  containmentStatus: 'blocked' | 'sanitized' | 'flagged';
  mitigationNotesAr: string;
  mitigationNotesEn: string;
  confidenceScore: number;
  timestamp: string;
}

export interface AuditStepLog {
  id: string;
  jobId: string;
  nodeName: string;
  nodeNameAr: string;
  nodeNameEn: string;
  stepIndex: number;
  timestamp: string;
  durationMs: number;
  toolName?: string;
  toolType?: 'internal' | 'mcp_server';
  tokenUsage: {
    prompt: number;
    completion: number;
    costUsd: number;
  };
  status: 'success' | 'warning' | 'error';
  payloadPreview: string;
}

export interface HITLDecision {
  jobId: string;
  decision: 'approved' | 'rejected' | 'revisions_requested';
  reviewerName: string;
  reviewerRole: string;
  comments: string;
  timestamp: string;
  signatureHash: string;
  writeOperationPermitted: boolean;
  affectedDatabaseMutation?: {
    table: string;
    action: 'INSERT' | 'UPDATE' | 'PUBLISH_CERTIFICATE';
    recordId: string;
  };
}

export interface LangGraphNode {
  id: string;
  key: string;
  nameAr: string;
  nameEn: string;
  descriptionAr: string;
  descriptionEn: string;
  phase: 'preprocess' | 'analysis' | 'verification' | 'governance' | 'commit';
  tools: string[];
  inputSchema: string;
  outputSchema: string;
}
