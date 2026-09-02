# Thinking Level Benchmark: Task Specifications

**Benchmark:** T14 — OpenAI Luna Thinking Level Benchmark  
**Model:** `openai/gpt-5.6-luna` (native Codex auth)  
**Thinking levels:** `low`, `medium`, `high`, `xhigh`, `max`  
**Schema version:** 1.0  

---

## T1: Geometric Series Proof (Baseline) ✅

**Category:** Quick math  
**Difficulty:** Easy  
**Status:** Completed — smoke test only (low vs max)

**Prompt:**
> Explain in 2-3 sentences why the infinite series 0.9 + 0.09 + 0.009 + ... equals exactly 1.

**Scoring:** Pass/fail (correct explanation)

---

## T2: Pivot Reaction Force (Physics Derivation)

**Category:** Physics  
**Difficulty:** Medium  
**Status:** Ready to run

**Prompt:**
> A uniform rod of mass m and length L is pivoted at one end and released from rest in horizontal position. Find the reaction force at the pivot when the rod passes through the vertical position. Show your work clearly.

**Correct answer:** R = 5mg/2

**Trap:** Most solvers assume F = mg or apply energy conservation without separating translational and rotational dynamics.

**Scoring rubric (100 points):**
- **40 pts** — Correct final answer (R = 5mg/2 or equivalent)
- **30 pts** — Correct approach:
  - Uses energy conservation to find angular velocity at vertical
  - Applies Newton's second law for CM motion
  - Applies rotational dynamics
  - Correctly combines to find reaction force
- **20 pts** — Identifies the trap (explicitly explains why R ≠ mg)
- **10 pts** — Clean derivation (no logical gaps, correct algebra)

---

## T3: Markov Chain Asymmetry (Probability)

**Category:** Probability  
**Difficulty:** Medium  
**Status:** Ready to run

**Prompt:**
> You flip a fair coin until you see either HT or TT. Which sequence appears first on average? What is the expected number of flips for each? Show your reasoning.

**Correct answers:**
- E[HT] = 4 flips
- E[TT] = 3 flips

**Trap:** They look symmetric but aren't. Low thinking assumes E[HT] = E[TT] by symmetry.

**Scoring rubric (100 points):**
- **40 pts** — Correct values (E[HT] = 4, E[TT] = 3)
- **30 pts** — State machine / Markov chain approach (defines states, transition probabilities)
- **20 pts** — Explains the asymmetry (why TT is faster than HT)
- **10 pts** — Clean derivation with proper equations

---

## T4: Async Closure Bug (Code Review)

**Category:** Code review  
**Difficulty:** Medium-Hard  
**Status:** Ready to run

**Prompt:**
> What does this code output and why?
> ```javascript
> for (var i = 0; i < 3; i++) {
>   setTimeout(() => console.log(i), 100);
> }
> ```
> Fix it so it prints 0, 1, 2. Then explain what happens if we change `var` to `let` instead.

**Correct output:** `3 3 3` (not `0 1 2`)

**Trap:** Classic closure-in-loop. The follow-up (`var` → `let`) tests block scoping depth.

**Scoring rubric (100 points):**
- **40 pts** — Correctly predicts output (`3 3 3`) and explains why
- **30 pts** — Provides correct fix (IIFE or `let` or `bind`)
- **20 pts** — Correctly explains `let` behavior (block scoping, new binding per iteration)
- **10 pts** — Discusses edge cases (e.g., `const` in loop head, `for...of` behavior)

---

## T5: Ramsey Planner on Graph (Optimization)

**Category:** Planning / Optimization  
**Difficulty:** Hard  
**Status:** Ready to run

**Prompt:**
> Consider a directed graph G = (V, E) where each node v ∈ V represents a production unit with production function f_v(k) = k^α (0 < α < 1). Capital can be allocated across nodes subject to a global budget constraint. Derive the Bellman equation for maximizing total discounted utility over T time steps, with depreciation rate δ and discount factor β. Describe the structure of the optimal policy and discuss when centralized vs. decentralized solutions are appropriate.

**Trap:** Low thinking writes a generic Bellman equation without recognizing network structure. Max thinking discusses:
- Decentralized solution (if no network externalities)
- Centralized solution (if cross-node spillovers exist)
- Computational complexity (curse of dimensionality)
- When approximation methods are needed

**Scoring rubric (100 points):**
- **40 pts** — Correct Bellman equation
- **30 pts** — Network structure insight (how graph topology affects allocation)
- **20 pts** — Policy insight (decentralized vs. centralized, when each applies)
- **10 pts** — Computational complexity discussion

---

## Protocol

### For each task:
1. Launch 5 subagents in parallel (one per thinking level)
2. Each receives identical prompt
3. Wait for all completions
4. Record: runtime, input tokens, output tokens
5. Score outputs (blind — without knowing which level produced which)

### JSON result format:
```json
{
  "run_id": "t14-t2-low-20260902-001",
  "benchmark": "t14",
  "task": "pivot-force",
  "thinking_level": "low",
  "model": "openai/gpt-5.6-luna",
  "provider": "openai",
  "timestamp": "2026-09-02T12:00:00Z",
  "runtime_seconds": 45,
  "tokens": {
    "input": 28000,
    "output": 420
  },
  "score": {
    "total": 65,
    "breakdown": {
      "answer": 40,
      "approach": 15,
      "trap": 10,
      "clean": 0
    }
  },
  "self_corrections": 0,
  "notes": "Got answer right but missed the trap explanation"
}
```
