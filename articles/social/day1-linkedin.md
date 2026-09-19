LinkedIn post for Day 1 (English, links to the dev.to post)

---

A schema-valid JSON can still be garbage.

I've spent the last few days testing Jev, a new calibrated-decision model from TypeSafe — not an LLM, a model purpose-trained to answer yes/no and scoring questions with real, calibrated confidence. I used it as a QC gate sitting on top of a Google ADK agent's structured output.

The point isn't "is the AI's answer good." It's that **structured output only guarantees the JSON is well-formed** — Gemini's `response_schema`, OpenAI's `response_format`, doesn't matter which. None of them check whether the *content* actually makes sense. A caption can be schema-valid and still be a sentence that physically doesn't fit in the 3 seconds it's assigned to.

Along the way I verified two details that a surprising number of blog posts get wrong:
→ ADK's real field is `output_schema`, not `response_schema` — set the wrong one and it fails silently, no error, just a schema constraint that quietly does nothing
→ Pydantic discriminated unions break Azure's structured-output mode outright — live 400, `'oneOf' is not permitted`

Full write-up, real code, real test output — all runnable from the repo:
https://dev.to/gde/valid-schema-wrong-content-using-jev-to-guard-a-google-adk-agent-57o6

Part 1 of a 3-part series. Part 2 rebuilds the same agent on Microsoft Agent Framework — same schema, same QC call, and a couple of real cross-cloud surprises.

#GoogleADK #AIAgents #GoogleDeveloperExpert #MicrosoftMVP
