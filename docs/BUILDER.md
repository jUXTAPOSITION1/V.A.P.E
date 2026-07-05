# Builder — Self-Improving Code Generation Agent

`agents/builder.py`

Builder is V.A.P.E.'s self-improvement engine. It generates production-ready Python —
new tools, playbooks, and improvement proposals — **grounded in Memory** and gated by a
two-tier security validator. Every successful output is appended back to Memory, so the
system's capability compounds over time.

---

## Lifecycle of a generation

```
task ──▶ search Memory (grounding) ──▶ build prompt ──▶ LLM (tier=deep)
      ──▶ extract code ──▶ security validate ──▶ append skill to Memory ──▶ return
```

1. **Ground** — `search_memory(task)` pulls the most relevant prior lessons/skills.
2. **Prompt** — grounding + Memory stats are injected into the Builder system prompt.
3. **Generate** — routed through the multi-provider `agents/llm.py` layer at `tier="deep"`.
4. **Validate** — two-tier security review (see below).
5. **Append** — safe outputs are stored as `skill` entries via `auto_append_to_memory`.

---

## Usage

```python
from agents.builder import Builder

builder = Builder()

code, meta = builder.generate_code(
    task="Create a keyless recon helper that checks Base contract verification status",
    tier="deep",
)

if code:
    builder.auto_append_to_memory(code, meta)
```

### Propose an improvement to an existing module

```python
code, meta = builder.propose_improvement(
    module="agents/run.py",
    issue="Add Memory grounding before the LLM call",
)
```

### CLI

```bash
python agents/builder.py "Create a playbook for static analysis on new Solidity repos"
python agents/builder.py --improve "agents/run.py: add memory grounding"
python agents/builder.py --stats
```

---

## Security validation (two tiers)

Builder never ships arbitrary dangerous code, but it also must not reject ordinary,
legitimate Python. So validation is split:

### BLOCK (hard reject — `is_safe = False`)

Arbitrary code execution, shell execution, and unsafe deserialization:

`eval(`, `exec(`, `__import__`, `os.system(`, `os.popen(`, `subprocess.call/Popen/run(`,
`pickle.load/loads`, `marshal.load`, `yaml.load(`, `shell=True`, plus destructive
filesystem ops (`os.remove`, `shutil.rmtree`) on delete/remove tasks.

### WARN (advisory — recorded, non-blocking)

Common, legitimate patterns that merely deserve a reviewer's eye and slightly lower the
stored confidence: `open(`, `requests.`, `urllib.request`, `import os`, `sys.argv`,
`input(`.

```python
from agents.builder import validate_security

is_safe, notes = validate_security(code, task)
# is_safe == False  → generation rejected
# is_safe == True   → notes may still contain advisory 'review:' items
```

This design was a deliberate fix: an earlier version hard-rejected `import os`, `open(`,
`requests.get`, and `json.loads`, which would have rejected nearly every real file.

---

## Grounding & interconnection

- **Reads Memory** before every generation (`_ground_in_memory`).
- **Writes Memory** after every safe generation (category `skill`).
- **LLM layer** — uses `agents/llm.py`, so it inherits the free multi-provider fallback
  chain (Groq → Cerebras → OpenRouter → GitHub Models → Together).
- **Graceful degradation** — if no provider key is set, `Builder.llm_ready` is `False`
  and generation returns empty without crashing.

---

## Audit trail

Every generation is recorded in-process:

```python
builder.get_audit_trail()  # list of {timestamp, task, code_len, provider, safe}
builder.get_stats()        # {total_tasks, safe_tasks, total_code_chars}
```

---

*Builder turns accumulated Memory into new capability — safely, and with a full audit
trail behind every line it writes.*
