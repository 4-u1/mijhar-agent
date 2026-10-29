description: how to answer a question about the reference regulations

Use when the officer asks what the regulations say, without attaching a document.
1. Call search_regulations with a short query in the officer's language; pick corpus_id only if the topic is clear.
2. Answer only from returned passages and cite their ids. If nothing scores above the cut-off, say no passage was found.
3. The corpora are synthetic benchmark text, not official law. Say so when the officer relies on a figure.
