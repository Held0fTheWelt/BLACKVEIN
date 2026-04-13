# MVP comparative evaluation playbook (God of Carnage)

Operational pack for **Phase 2 — Earliest differentiation test** in `docs/MVPs/MVP_World_Of_Shadows/ROADMAP_MVP_WORLD_OF_SHADOWS.md`: same evaluator goal, two arms, shared feedback against assumptions **H1–H3**.

## Arms

| Arm | What the evaluator uses | Authority model |
|-----|-------------------------|----------------|
| **A — World of Shadows** | Player frontend play shell: start a run for the GoC template, `POST` turns via backend → world-engine (`/play/.../execute`). | Engine validates and commits; AI proposes. |
| **B — Generic baseline** | `python scripts/mvp_generic_llm_baseline_chat.py` (after `OPENAI_API_KEY` is set). | Plain chat completions; no runtime contract. |

Frozen opening brief and Arm B system instructions: `scripts/data/mvp_goc_baseline_opening.json`.

## Preconditions (both arms)

- Same **evaluator goal framing** text as in the JSON field `evaluator_goal_framing` (facilitator reads it aloud or pastes it once).
- Suggested **turn budget**: 6–10 player turns per arm (adjust for session length; keep arms comparable).
- Same **time box** per arm where possible (e.g. 20–25 minutes).
- Arm A requires a running stack (backend, world-engine, frontend) and a logged-in test account.

## Facilitator session script

1. **Consent & setup** — Explain two short scenes back-to-back; no wrong answers; notes may be taken.
2. **Randomize arm order** — Coin flip whether A or B is first to reduce order bias.
3. **Goal framing** — Read `evaluator_goal_framing` from `mvp_goc_baseline_opening.json` verbatim.
4. **Arm A** — Guide the evaluator through play start → shell → natural-language turns. Point out that narration and committed scene/consequence fields are **product signals**, not things to “optimize.”
5. **Short reset** — One minute neutral break; no discussion of comparison yet.
6. **Arm B** — Run the baseline script; evaluator plays the same role style (first person, same rough turn count).
7. **Feedback** — Immediately collect the form below (written or typed).

## Scoring / feedback form (H1–H3)

**Evaluator ID:** _______________ **Date:** _______________ **Arm order:** A first / B first (circle)

### H1 — Perceived qualitative difference

1. Which experience felt **more like a held-together dramatic scene** vs **generic chat**? (1 = strong chat feel, 5 = strong scene feel)  
   Arm A: [1–5]   Arm B: [1–5]

2. In one or two sentences, what **felt different** between the two (if anything)?

### H2 — Freedom vs shaping

3. Where did your input feel **free enough** vs **pushed or invisible-rails**?  
   Arm A: [1–5 free]   Arm B: [1–5 free]

4. Did either arm feel **frustratingly restricted**? Which and why?

### H3 — Validation / commit as visible value

5. In Arm A, did **later turns** seem to **remember** earlier choices or consequences? (1 = not at all, 5 = clearly) — _______

6. In Arm B, did **continuity** feel as strong as Arm A, stronger, or weaker? Brief note: _______________

### Overall

7. Would you **continue playing** either experience beyond the test? Arm A Y/N  Arm B Y/N

8. **Risk flag:** Did anything feel “engineering demo” rather than “playable drama”? Where?

## After sessions

- Aggregate answers by H1–H3; map to roadmap **Phase 2 exit criteria** (clear / weak / invisible difference).
- Do **not** treat Arm B as ground truth for canon; it is only a comparison control.

## References

- Roadmap: `docs/MVPs/MVP_World_Of_Shadows/ROADMAP_MVP_WORLD_OF_SHADOWS.md` §9–§11.
- Primary runtime path (Arm A): `docs/technical/runtime/a1_free_input_primary_runtime_path.md`.
- Baseline CLI: `scripts/mvp_generic_llm_baseline_chat.py`.
