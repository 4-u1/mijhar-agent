---
title: MIJHAR مِجهر · Evidence-Audit Agent
emoji: 🔎
colorFrom: green
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
short_description: Evidence-audit AI agent with MCP tools and a signed human gate
---

# مِجهر · MIJHAR

An evidence-audit agent that drives a governed LangGraph pipeline, with a signed human decision before any write.
SDAIA Academy · Advanced Agentic AI Systems Engineering capstone · **Yazeed Hamad Alharthi · يزيد حمد الحارثي**.

Open the app at `/agent/`. It asks for a client key: set the Space secrets below, then open
`https://<your-space>.hf.space/agent/#ck=<client key>&rid=<reviewer id>&rk=<reviewer key>` (the fragment never reaches the server).

**Space secrets (Settings → Variables and secrets):**

| Secret | Value |
|---|---|
| `MIJHAR_SIGNING_SECRET` | 64 random hex chars |
| `MIJHAR_CLIENT_KEYS` | `ui:<sha256 of your client key>` |
| `MIJHAR_REVIEWERS` | `eng.demo:<sha256 of your reviewer key>` |
| `OPENROUTER_API_KEY` + `MIJHAR_ALLOW_LIVE=1` | optional: real model (text leaves the Kingdom, see SECURITY.md) |

Without a model key the agent runs on the offline planner (labelled in the UI). Storage is ephemeral on free Spaces:
the ledger resets when the Space restarts. Full documentation: the GitHub repository README.

🇸🇦 تم تطوير وبناء هذا المشروع ضمن مسار **هندسة أنظمة الذكاء الاصطناعي التوكيلي المتقدمة** تحت إشراف ورعاية
**الهيئة السعودية للبيانات والذكاء الاصطناعي (SDAIA)** · **أكاديمية سدايا — @SDAIAAcademy**
