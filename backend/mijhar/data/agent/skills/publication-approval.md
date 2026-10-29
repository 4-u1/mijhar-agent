description: rules for asking the human officer to approve publication of a certificate

Use when the officer asks to publish, approve, certify or sign.
1. A completed audit (status awaiting_human) must exist. If not, run audit_document first or say none exists.
2. Call request_publication with the job_id and a one-line note. It only opens an approval card for the officer.
3. You cannot approve, sign or publish. Do not describe the outcome until a harness event reports it.
4. If the audit has threats or contradicted claims, state them before asking, so the officer signs knowingly.
5. After the harness reports the decision, report it exactly: decision, reviewer, ledger tx hash if COMMITTED.
