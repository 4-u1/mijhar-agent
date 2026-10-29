description: how to audit an attached document and present the findings

Use when the officer attaches a document or asks for an audit.
1. Call audit_document with the doc_id from the attachment note. Never ask the officer to paste the text.
2. The pipeline runs guard, claim extraction, retrieval, verification and scoring, then stops at the human gate. It writes nothing.
3. Present: risk score, threats (kinds only), then contradicted claims first, each with the passage id that contradicts it.
4. If threats were redacted, say so plainly: those sentences never reached any model.
5. End with the next step: the officer can ask you to request publication.
