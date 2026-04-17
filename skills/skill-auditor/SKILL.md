---
name: skill-auditor
description: "Use this skill whenever the user wants to audit, review, inspect, or check a SKILL for logic consistency, content completeness, or quality issues. Triggers include: '审查这个SKILL'、'检查SKILL逻辑'、'审计技能'、'检查这个skill'、'review this skill'、'audit this skill'、'检查skill的完整性'。 Also use when the user pastes SKILL.md content and asks for review, or when the user says '帮我检查一下这个技能' or similar. This skill performs deep inspection of ALL files in the SKILL folder — every file type including SKILL.md, scripts (.py/.js/.ts), configurations (.json/.yaml), evals, assets, and any other present files. No file is excluded from audit by type."
---

# Skill Auditor

## Purpose

Perform deep audit of a SKILL folder to identify logic inconsistencies, completeness gaps, and quality issues. **Report findings only — do NOT auto-fix unless user explicitly asks.**

## Core Principle: Verify Before Report

Auditing requires **understanding before judging**. A finding is only valid after verification. Never report a suspected issue without tracing its full logic path first.

---

## Workflow

### Step 0: Language Adaptation (Before Everything Else)

**Language matching is mandatory.** The audit report must be output in the same language the user used in their request.

- If user writes in **Chinese** → entire report in **Chinese**
- If user writes in **English** → entire report in **English**
- Mixed language? → Use the dominant language of the user's message

**This is not a style preference — it is a structural requirement enforced before Step 1.**

---

### Step 1: Locate the SKILL Folder

User may provide:
- A path to a SKILL folder directly
- A path to a single SKILL.md file (infer folder from it)
- Content pasted directly (in this case, analyze the pasted content but note you cannot verify file-level issues)

**If user pastes content without a clear task:**
→ Ask before proceeding (bilingual prompt):
  - 中文："请确认审查范围：A) 仅审查这份内容本身 / B) 假设这是完整 SKILL 并按标准流程审查"
  - English: "Please confirm scope: A) Audit only this content / B) Treat as complete SKILL and follow standard process"
→ Wait for user's choice before starting

If given a path to SKILL.md only, treat the parent directory as the SKILL folder.

**If the folder cannot be accessed** (permission denied, path doesn't exist, folder is empty):
→ Output directly: `无法审查 — [具体原因]`
→ Stop and do nothing more.

**If no path is provided and cannot be inferred from context:**
→ Ask the user to provide the SKILL folder path. Do not assume any default location.
→ Stop and wait for the user's response.

### Step 2: Read ALL Files in the SKILL Folder

A complete SKILL may contain multiple files. Read **every file present** — no file type exclusions:

```
SKILL.md              (required - always read)
├── references/          (read ALL files inside, any type: .md, .json, .txt, etc.)
├── scripts/             (read ALL scripts: .py, .js, .ts, .sh, .ps1, etc.)
├── assets/              (read ALL files: images, fonts, binary assets — inspect metadata and content)
├── evals/                (read ALL files: evals.json, eval_*.py, etc.)
└── [any other files]    (read ALL — no type exceptions)
```

**Never skip files by extension or type.** Read the full content of every file encountered. If `references/` exists, read every file inside it regardless of extension. If `scripts/` exists, read every script file. If `assets/` exists, inspect asset files. If `evals/` exists, read all evaluation files.

---

### Step 2.5: Understand Design Intent (Before Checking)

**This step is critical.** Before applying the 6 dimensions (Dimension 0 through Dimension 5), you MUST first establish a shared understanding of what this SKILL does.

---

#### Step 2.5.1: Design Intent Summary (MANDATORY — do this first)

Read **all files completely**, then answer in 2-3 sentences:

> **"这个 SKILL 是做什么的？核心流程是什么？"**
> **"What does this SKILL do? What is the core workflow?"**
>
> 一句话描述 + 核心执行路径（Step 1 → Step 2 → Step 3 → Step 4 → Step 5）

**If you cannot answer this question after reading all files → output a `[CANNOT UNDERSTAND]` finding and stop the audit. Do not proceed to Step 2.5.2 or the 5 dimensions.**

---

#### Step 2.5.2: Architecture Deep Dive

Only after Step 2.5.1 is clear, answer these questions:

1. **Step relationships**: How does data flow between steps? What are the inputs/outputs of each step? (e.g., Step 2 collects all files → Step 2.5 builds understanding → Step 3 applies 6 dimensions → Step 5 reports)

2. **Algorithm design intent**: For any algorithm or scoring logic, understand:
   - What problem does it solve?
   - Why was it designed this way?
   - Is "unusual" behavior actually intentional?

3. **Independent vs coupled components**: Are the 6 audit dimensions independent from each other? Are config files separate from execution logic?

4. **Multi-file architecture** (critical for full-folder audits): When a SKILL spans multiple files:
   - Which file is the source of truth for the described workflow (SKILL.md, a runner script, a config)?
   - Are there references between files (e.g., SKILL.md mentions `scripts/update.py`)? Do the referenced paths actually exist?
   - Do scripts define behavior that contradicts or extends what SKILL.md states?
   - Are config files (e.g., evals.json, params.json) actually loaded/used by the scripts, or are they dead references?
   - Is there implicit coupling (File A depends on File B's existence) that is not documented?
   - **Never assume file references are correct — always verify the actual files exist and match their descriptions.**

**Why this matters:**
- "Parameter X not used in code" → may be intentional (different step uses different values)
- "M and K seem mixed" → may be correct usage in context
- "Design seems inconsistent" → may be deliberate trade-off

**If you don't understand the design at any point, say so instead of forcing a finding.**

---

**⚠️ Skip Rules (apply before any dimension check):**
If a pattern is true for ALL skills, it is NOT a finding — it is framework design, not a skill defect. Examples:
- `user_message` param not documented in any SKILL.md
- YAML frontmatter format is identical across all skills
- Skill tool's own signature parameters (these are framework contract, not skill responsibility)

**When in doubt:** Ask "Is this unique to this SKILL, or is it true for every SKILL?" If the answer is "every SKILL," skip it.

---

### Step 3: Audit Against 6 Dimensions (with Verification)

For each dimension, identify **suspected issues** (not final findings yet).

---

#### Dimension 0 (Meta): Step Numbering Clarity

**Before auditing 5 dimensions, verify the workflow's own structural clarity.**

**Questions:**
- Is the step numbering internally consistent (e.g., Step 3 → Step 3.5 does not imply a 6th Dimension)?
- Are sub-steps clearly scoped to their parent step?

**Checks:**
- [ ] Step hierarchy is unambiguous (no semantic overlap between step numbers and dimension numbers)
- [ ] No step exists that describes itself as applying N dimensions but has sub-steps at the same level

---

#### Dimension 1: Trigger Condition Audit

**Questions:**
- Does the `description` field accurately describe all capabilities in the body?
- Are there under-trigger or over-trigger risks?
- Are excluded scenarios truly inconsistent with implementation?

**Checks:**
- [ ] Every capability in body is mentioned in description
- [ ] Every mentioned tool/library has actual usage
- [ ] Excluded scenarios match actual limitations

---

#### Dimension 2: Parameter Signature Audit

**Questions:**
- Are parameters described in docs actually received by implementation?
- Are parameters used in code actually documented?
- Are defaults, required/optional flags correct?

**Checks:**
- [ ] Name matches between description and code
- [ ] Type is correct
- [ ] Required/optional matches behavior
- [ ] Default values are accurate
- [ ] Value constraints are enforced

---

#### Dimension 3: Execution Flow Audit

**Questions:**
- Does the described sequence match actual code?
- Are all branches documented?
- Is the flow complete (every path has an end state)?

**Checks:**
- [ ] Step order matches implementation
- [ ] Each branch is documented
- [ ] Error cases have messages/handling
- [ ] No hidden steps
- [ ] No missing steps

---

#### Dimension 4: Exception Handling Audit

**Questions:**
- What happens when external dependencies fail?
- What happens with malformed inputs?
- Are timeouts handled?
- Are error messages actionable?

**Checks:**
- [ ] External failures → documented + handled
- [ ] Bad input → validation error (not crash)
- [ ] Timeouts → explicit handling
- [ ] Error messages → user-comprehensible

---

#### Dimension 5: Output Format Audit

**Questions:**
- Is success response structure fixed and documented?
- Is error response consistent with success structure?
- Are all returned fields documented?

**Checks:**
- [ ] Success format is consistent
- [ ] Error response has actionable info
- [ ] All fields are documented
- [ ] No undocumented side effects

---

### Step 3.5: Verify Before Reporting (Critical)

**Every suspected issue must be verified before it becomes a finding.**

For each suspected issue found in Step 3:

```
1. TRACE: Follow the code/data path completely
   - Where is the parameter defined?
   - Where should it be used?
   - Where is it actually used (if at all)?
   - What is the execution flow?

2. JUDGE: Is this truly a bug or is it design intent?
   - Does the design call for this behavior?
   - Is "X not used" actually correct because Y step uses different logic?
   - Is "M and K seem wrong" actually correct usage?

3. CLASSIFY the verification result:
   - ✅ CONFIRMED: Issue is real and needs fixing
   - ❌ NOT AN ISSUE: Design intent, not a bug
   - ⚠️ NEEDS CLARIFICATION: Cannot determine without user input
   - 🚫 CANNOT UNDERSTAND: AI could not establish design intent for this component
```

**Never skip verification.** If you cannot verify (e.g., missing code context), say "CANNOT VERIFY — [reason]" instead of guessing.

---

### Step 4: Data Flow Consistency Check

**⚠️ Applicability rule:** Perform these checks only if applicable. If the skill has no cross-file references, skip this step entirely (do NOT output anything).

1. **Trace data through steps** (if the skill has steps or stages):
   - Step A output → Step B input: Does format match?
   - Step B output → Step C input: Does field naming match?

2. **Verify metric consistency** (if the skill defines metrics):
   - If the SKILL mentions specific dimensions or scoring criteria, confirm each one is actually calculated
   - If the SKILL references specific thresholds, confirm they are loaded and used in the expected step

3. **Threshold configuration path** (if the skill uses configurable thresholds):
   - If a config file defines thresholds → trace to see if/when they are loaded and used
   - If "parameter defined but not used" is suspected → verify if it's intentional (e.g., different step uses different logic)

4. **Cross-file reference integrity** (multi-file skills only — skip for single-file skills):
   - If SKILL.md references `scripts/update.py` → confirm the file exists and the path matches exactly
   - If a config file is mentioned as being loaded → confirm the script actually reads it
   - If files have implicit dependencies (File A relies on File B's presence) → confirm both exist and the coupling is documented

**Drop low-value checks** (OS/network layer will catch these anyway):
- ❌ "URL references are valid" (skip — external availability is not a SKILL logic issue)

**Keep high-value checks**:
- ✅ Data format consistency across steps
- ✅ Metric calculation completeness
- ✅ Threshold configuration actual path
- ✅ Cross-file reference integrity (file paths that SKILL.md or scripts mention must actually exist at the stated path)

---

### Step 5: Report + Confirm Before Fixing

**核心原则：只报告，不改动；用户确认后再执行修复。**

#### 5.1 Report All Findings

After completing all dimension audits (Step 3) and Step 4:

**If no issues found at all:**
→ Output: `审计完成，未发现问题。`
→ End of audit — no interaction required.

**If issues found:** Output the findings table directly — do NOT record per-issue responses or ask for confirmation yet:

```
---

## 审计结果

| # | 维度 | 问题 | 级别 |
|---|------|------|------|
| 1 | Trigger Condition | 描述... | HIGH |
| 2 | Execution Flow | 描述... | MEDIUM |
| ... | ... | ... | ... |

**请告诉我要修复哪些问题**（例如：输入 "1,3" 修复 #1 和 #3；"all" 全部修复；"none" 全部跳过）
```

---

## Important Rules

1. **Verify before report.** Never elevate a suspected issue to a finding without tracing its full logic path.
2. **Understand design intent.** "Seems wrong" is not a finding. "Violates design intent without reasonable explanation" is.
3. **Report only.** Do NOT auto-fix unless user explicitly approves.
4. **Read ALL files.** An audit that only reads SKILL.md is incomplete.
5. **Be specific.** Reference exact file and line number when confirmed.
6. **No speculation.** If unverified, say "CANNOT VERIFY — [reason]".
7. **Prioritize.** Mark issues as HIGH/MEDIUM/LOW impact.
8. **Language adaptation.** See Step 0 — report language must match user's request language.
9. **Consistent numbering.** Rules must be consecutively numbered. Do not skip numbers.
10. **Skip framework patterns.** If a suspected issue turns out to be true for ALL skills (not just this one), it is a framework design, not a skill defect. Do not report it.
