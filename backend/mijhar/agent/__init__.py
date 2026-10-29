"""MIJHAR agent layer: a tool-using agent loop on top of the governed audit pipeline.

    officer  ->  agent loop (model chooses tools)  ->  tools  ->  audit graph (deterministic, human gate)

The model decides WHAT to do (which tool, in what order, when to ask for approval, how to explain).
It never sees raw documents, holds no write tool, and cannot sign. See AGENTS.md section 11 onwards.
"""
