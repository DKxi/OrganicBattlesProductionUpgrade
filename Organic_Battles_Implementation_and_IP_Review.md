# Organic Battles: Implementation, Learning Design, and IP Review

Reviewed September 8, 2026. This report supersedes the earlier cookbook-only assessment wherever the supplied code provides stronger evidence.

**Principal finding.** The supplied backend implements a chemistry vocabulary battle game with persistent state, sequential questions, and damage-based advancement. It does not implement the cookbook’s stated combat formulas, turn-based cooldowns, or a mastery assessment system. Several defects allow progression without learning and could expose the question bank. No specific Prodigy infringement was established from the supplied material, but the incomplete asset collection and absent provenance records prevent IP clearance.

This is an engineering and preliminary U.S.-focused IP assessment, not a legal opinion or worldwide freedom-to-operate clearance. All application findings concern the uploaded snapshot, not a verified deployment on the owner’s computer.

**Evidence and limits**

The uploaded app.zip contains 74 files. Its SHA-256 is `afbf2fb03b89a759e3bdb6a27af7fb6c8d7018d83b63fccb3f8b5f300e833cc8`.

| Supplied | Missing from this ZIP |
|---|---|
| Modular Python backend; compatibility adapters | Entire `static/` directory, including frontend JavaScript and CSS |
| HTML page template | Runtime `data/` directory and `tracks_config.json` |
| Eight PNGs under `avatars/`, including carbonyl-dragon.png | Dedicated `bosses/` directory and referenced track-specific boss artwork |
| `temp/chapter_01_final_progression.json`, containing 50 questions | Full foundational and advanced question banks and manifests |
| Tests, dependency manifests, bestiary/design documents | Asset creation records, grants/assignments, and a complete third-party license inventory |

The template requires `/static/js/main.js`, `/static/js/tracks-config.js`, and `/static/css/game.css`; these are absent. A live browser playthrough, image preloading/unloading review, and browser compatibility assessment cannot be completed from this archive. Referenced assets in Markdown do not count as supplied images.

Methods: static inspection of routes, domain rules, loaders, persistence, configuration, HTML, tests, and supporting documents; structural examination of all 50 sample JSON questions; visual inspection of all eight supplied PNGs; execution of original domain modules and isolated original route function bodies with fake repositories and fixture users. A harmless temporary fixture placed the supplied sample under `data/chapter_01.json` for loader and file-resolution checks. Original application files were not modified.

FastAPI, SQLAlchemy, and pytest were unavailable in the runtime, and dependency installation did not complete. Therefore there was no full HTTP integration run, full pytest run, concurrent database test, or deployed exploit attempt. Seven existing domain-test functions were executed directly and passed. Route harness results establish the function behavior under controlled inputs; they do not substitute for end-to-end deployment verification.

The ZIP contains 64 test-function definitions. This does not substantiate the cookbook’s claim of 198+ passing tests; parametrization and a larger omitted suite could alter the total. Several supplied tests explicitly require missing manifests, chapter banks, assets, and frontend files.

**Corrections to the previous analysis**

| Earlier cookbook-based account | Actual supplied implementation |
|---|---|
| Base damage 20 / 35 / 50 | Active combat catalog uses 20 / 30 / 45 |
| Cooldowns 0 / 1 / 2 turns | 1.5 / 5 / 10 seconds after answer resolution |
| Wrong answers cause 15 or 20% backfire plus boss damage | Full selected spell damage hits the player; no additional boss counterattack on that branch |
| Correct-answer counterattacks occur only in low-HP rage mode | Any surviving boss has a 50% counterattack chance |
| Counterattack damage scales by chapter | Route uses the domain default: random integer 10–25 |
| Question order unknown | Sequential within the selected bank, wrapping modulo bank size |
| Answer shuffling unknown | Backend preserves source order; missing frontend prevents final presentation verification |
| Stable question IDs absent from sample schema | Actual sample has IDs and difficulty/topic/type labels, but loader discards these in runtime question tuples |
| Explanation display unknown | API returns answer and explanation after submission; HTML has an explanation control; browser behavior remains unverified |
| Boss health precedence unknown | Maximum health value among question records assigned to that boss |
| Boss strategy object governs runtime | Loader derives behavior from question rows and first appearance, not `boss_strategy` |
| Boss defeat establishes advancement eligibility | Advance endpoint does not verify defeat |
| Question keys likely remain private | Pending question payload excludes keys, but the image resolver can expose JSON files from searched folders |

Source references below use paths relative to the uploaded project and identify functions or approximate starting lines.

**Scoring, rewards, and combat**

`app/domain/combat/spells.py` defines nine selectable catalog spells:

| Tier | Spells | Base damage | Cooldown |
|---|---|---:|---:|
| Basic | Fire Spark; Acid Shot; Carbon Punch | 20 | 1.5 seconds |
| Medium | Resonance Burst; Nucleophile Strike; Chiral Slash | 30 | 5 seconds |
| Strong | Mechanism Storm; Stereochemical Rift; Spectral Obliteration | 45 | 10 seconds |

Within each tier, damage and cooldown are identical. The supplied combat evaluator has no chemistry-specific weaknesses, attack directions, reagent requirements, elemental resistance, status ailments, mana cost, healing spells, or avatar-dependent statistics. Spells differ mechanically by strength and cooldown, with naming and visuals providing the rest of their identity.

In normal JSON content with three damage entries, the available concrete spells are Fire Spark, Resonance Burst, and Mechanism Storm. Custom values alter damage but not cooldown durations. If boss damage metadata is empty, the select route’s availability restriction can disappear, so malformed content can expose all nine catalog spells.

`loader.py` also contains an older `BUILTIN_SPELLS` table with 20/35/50 values and 0/1/2 cooldown values. This is a competing representation, not the active combat catalog. Consolidate the tables to prevent further documentation/UI divergence.

For damage D, `evaluate_combat_turn` applies:

- Correct: boss HP becomes max(0, boss HP − D). If the boss survives, it has a 50% chance to damage the player by a uniformly selected integer from 10 through 25.
- Incorrect: player HP becomes max(0, player HP − D); boss HP is unchanged; no boss counterattack is added.
- A killing correct hit suppresses counterattack.
- A correct answer can still result in player defeat through the counterattack.

The evaluator supports injected randomness for tests, but the real answer route supplies neither a roll nor a counterattack value. Live outcomes are random, with expected damage of 8.75 per surviving correct hit. The boss tuple’s attack field is not passed into the evaluator. The cookbook’s low-HP rage restriction is not present.

A strong spell is consequently a risk/reward choice: higher damage shortens exposure to counterattacks but also increases the cost of a mistake. At 65 damage, three wrong strong casts kill a 150-HP player even with no other incoming damage. Avoid communicating failure as evidence of weak understanding when randomness can kill an otherwise accurate player.

Cooldowns are timestamps, set when an answer resolves. Time reading feedback can consume a cooldown; waiting can restore a strong spell without spending another turn. Cooldowns belong to individual spell IDs, not tiers. In nine-spell mode a player can rotate same-tier spells. No forced timer requires immediate answers or immediate casting.

The durable numerical state is HP, boss position, completion records, and a version counter. There is no implemented XP formula, level growth, score total, currency, shop, or reward-award rule in the supplied backend. `rewards_json` is read and returned, but no award mutation was found. Cosmetic rewards mentioned in the prompt remain requirements rather than demonstrated implementation. Avatar selections are stored, but the combat function does not consume them.

Evidence: `app/domain/combat/rules.py:13`, `app/domain/combat/spells.py`, `app/api/v1/battle.py:97`, `app/api/v1/game.py:38`.

**Question selection and answer validation**

A spell selection checks player HP, boss HP, a pending spell, catalog membership, cooldown, and available JSON spell ranks. It resolves content in this order: recognized environment override; user-selected content; default JSON mode.

Question-bank fallback order is:

1. Current chapter plus boss slug.
2. Boss slug across the bundle.
3. Current chapter’s question bank.
4. Entire bundle’s question bank.

Selection is `cursor % len(bank)`. The key is `chapter:boss_slug`; it contains no track identifier. The cursor advances on every resolved answer, including an incorrect answer. There is no runtime sampling by difficulty, diagnosis of misconceptions, spaced review, or prioritization of missed concepts. After a pool is exhausted it cycles back to the beginning in the same order. Retrying a boss preserves the cursor. There is no protection against an empty bank before modulo selection.

The active question persists as a tuple of prompt, choice strings, and answer string. JSON fields including question ID, topic, difficulty, question type, and correct-option label are discarded. This prevents robust concept-level tracking and makes question identity depend on text.

`grade_answer` compares stripped, lowercased strings. The client must submit answer text rather than just A/B/C/D. The route does not require the submitted string to be one of the listed choices. Punctuation, internal whitespace, Unicode superscripts, and chemical-equivalence normalization are not handled. This is workable for exact MCQ text but not a chemistry structure grader.

The loader trusts `correct_answer`; when that field is missing it silently chooses the first option. It does not use `correct_option` or any `options[].correct` flag as the authoritative answer. Malformed content could therefore reward an incorrect choice. Require one authoritative answer ID and validate every content record before deployment.

A positive finding: `format_game_state` returns only prompt and choices for a pending question. Answer and explanation are returned after submission. However, the generated turn ID is neither included in the normal state nor required by `AnswerRequest`, which contains only `answer`. No question identity is submitted either. A delayed answer can be interpreted against a newer pending turn.

Evidence: `battle.py:31`, `battle.py:97`, `game.py:38`, `loader.py:213`, `rules.py:8`.

**Confirmed explanation collision**

Ten sample records use the identical prompt “Which term–description pairing is correct?” Their options and explanations differ. The loader assigns `explanations[prompt] = ...`, replacing the prior explanation each time. The answer endpoint looks up that same prompt key.

Loading the supplied 50-question sample produced nine mismatches between the question’s own explanation and the explanation retrieved at runtime. Grading still uses the active question’s answer, so the API can correctly mark an answer while providing an unrelated explanation. This is an instructional correctness bug, not merely an analytics issue.

Damage maps also use prompt-based keys. For question-specific values, even `(chapter, boss, prompt)` can collide when a boss contains repeated stems. Boss-specific fallbacks can further obscure which value should apply. Use `(track, content_version, question_id)` as stable identity and store explanation and damage with the active question snapshot.

Evidence: `loader.py:218`, `loader.py:231`, `battle.py:117`. Reproduced with the original loader and supplied sample.

**The supplied question bank and what it teaches**

All 50 sample records were structurally examined. This file is in `temp/`, so it is not loaded by the project’s default content path. Conclusions about it must not be generalized to omitted production tracks.

| Measure | Result |
|---|---:|
| Questions / unique IDs | 50 / 50 |
| Boss groups | 5, with 10 questions each |
| Topics | 10, each appearing 5 times |
| Difficulty labels | 20 easy, 20 medium, 10 hard |
| Unique prompt strings | 41 |
| Answer positions A / B / C / D | 10 / 14 / 13 / 13 |
| Missing explanations | 0 |
| Correct-option label versus answer-text mismatches | 0 |
| Explanations exactly equal to answer text | 10 |
| Runtime explanation mismatches after loading | 9 |

Topics are pi bond, sigma bond, covalent bond, polar covalent bond, formal charge, dipole moment, electronegativity, valence electron, constitutional isomer, and hybridization. Five question formats occur ten times each: term-to-definition, definition-to-term, concept recognition, term/definition pairing, and concept discrimination.

These are vocabulary-recognition and definition-discrimination tasks. Even the hard questions ask the player to identify a definition from alternatives. They do not require formal-charge calculation, interpreting a molecule, assigning hybridization to a particular atom, predicting a reaction, drawing arrows, interpreting spectra, or constructing a synthesis.

Thus, “hard” is an author-assigned label, not demonstrated mechanistic complexity. Multiple phrasings of ten terms should not be presented as fifty distinct concepts. Generic restatement of an answer offers less instructional help than explaining the misconception behind each distractor.

Boss names do not strictly constrain their question topics. For example, the first Orbital Ogre questions concern pi bonds, formal charge, and polar covalent bonds. That can be legitimate cumulative review, but a promise that each boss specifically teaches its named concept needs an explicit objective map.

**Progression can omit most difficult material even during honest play**

The sample stores questions in easy-then-medium-then-hard order. Taking the strongest available spell, answering correctly, waiting for its cooldown, and surviving counterattacks gives this possible path:

| Boss | HP | Strong damage | Correct hits to defeat | Hard questions reached |
|---|---:|---:|---:|---:|
| Orbital Ogre | 100 | 45 | 3 | 0 |
| Bondbreaker Brute | 200 | 50 | 4 | 0 |
| Hybridization Goblin | 300 | 55 | 6 | 0 |
| Polarity Phantom | 400 | 60 | 7 | 0 |
| Molecular Property Titan | 500 | 65 | 8 | 2 |
| Total | | | 28 | 2 |

This is a conditional successful path, not a promise of survival: random counterattacks can interrupt it. It demonstrates that all five bosses can be defeated after 28 of 50 questions, encountering only 2 of 10 hard questions. Twenty-two questions, including eight hard ones, can remain unseen.

Do not solve this solely by inflating boss HP. Require objective coverage and a small independent exit assessment, while allowing combat efficiency to remain rewarding. Revisit the concept later to distinguish immediate recognition from retention.

**Critical progression and authorization defects**

P0 means address before public release; severity here describes engineering priority, not a formal CVSS score.

| Priority / finding | Evidence and effect | Required behavior |
|---|---|---|
| P0: Advance without victory | `next_turn` records completion and advances without checking boss HP, player HP, or pending question. Isolated call advanced a full-health 100-HP boss and marked it completed. | Require a valid defeated-boss state; make completion idempotent and atomic. |
| P0: Session ownership missing | Battle selection, answer, next-turn, and retry use `get_by_id(session_id)` without comparing owner with current user. Repository does not add ownership filtering. Selection accepted a fixture session belonging to another user. | Query by session ID AND authenticated owner on every operation. |
| P0: Old question survives advance | `next_turn` does not clear active question/spell/turn ID. Harness advanced to another boss with the old question pending. | Reject invalid transitions and bind each pending turn to its boss/content version. |
| P1: No atomic turn consumption | `version += 1` has no compare-and-swap filter; no row lock, version mapper, or validated idempotency key. | Serialize or conditionally update turns and record consumed identifiers. |
| P1: Unrestricted retry | Retry does not require player defeat; restores both HP pools and preserves cursor. It also leaves stale `turn_id`. | Deliberately define practice restart versus defeat retry and reset all dependent state. |

Session IDs are not trivially predictable; the ownership issue requires knowledge of a victim session ID. That mitigates discovery but does not replace authorization. The normal state-read endpoint does perform an ownership check, demonstrating inconsistent protection rather than an absence of authentication everywhere. Other explicit-session routes, including track selection and avatar finalization, also need ownership review.

The concurrency issue is established by code inspection; duplicate commits or precise race outcomes were not measured against a real database. A monotonically incremented number alone is not optimistic locking.

**Saving progress, switching tracks, and resetting**

SQLAlchemy persists one active GameSession per user because `user_id` has a unique constraint. Active HP, question, spell, cooldown timestamps, cursor map, logs, and completion list can survive process restarts through the database. Re-entering `/game/new` returns the existing session instead of automatically resetting it.

Track changes archive only chapter, boss index, completion list, and update time under `User.progress_json['tracks']`. Incoming state restores those positions, then restores full player and boss health and clears the pending question and cooldowns. Exact battle state is not archived per track.

The cursor map remains on the active session and lacks track ID, so tracks sharing chapter and boss slugs share question positions accidentally. Reward state also has no implemented per-track awarding or archival rules.

Several gate exceptions are confirmed:

- Selecting the same track skips the gate and resets HP and pending questions. The harness reset 50 player HP and 40 boss HP to 150 and 100.
- After any mini-boss reaches zero HP, before advancement, the gate’s conditions can all be false. A different track can be selected before the chapter ends; reproduced after boss index 1.
- `/user/mode` and `/user/content-source` provide another switching path without the chapter gate or equivalent track archival.
- Environment content overrides may mean a selected track is not the content actually formatted or played.

Admin session deletion clears the user’s entire progress JSON, potentially deleting all archived track progress. Admin reset writes an older top-level progress shape while track switching reads nested tracks; these models are inconsistent. Admin resets retain old question cursors and completion records unless other omitted logic intervenes. Completed boss IDs also omit chapter identity, so repeated slugs within one track can collapse distinct completions.

Ordinary battle answers keep only the last ten log entries. There is no durable attempt ledger capturing question ID, submitted option, correctness, elapsed time, hint use, and concept outcome. Completion cannot currently support trustworthy learning analytics.

Evidence: `game.py:163`, `game.py:276`, `users.py:21`, `admin.py:240`, `SessionRepository.delete`, `database/models.py`.

**Boss construction, loading, and unloading**

The loader groups question records by boss name in first-occurrence order. It uses the maximum health value for that boss; the last distinct group is labelled major. First-row image/topic and spell values help define the boss. The top-level `bosses` and `boss_strategy` objects do not govern this process. A typo in a boss name can accidentally create an additional boss; slug collisions can combine banks or completion identities.

Files load in manifest order or sorted filenames. Routes frequently assume chapter position equals chapter number minus one. Missing or noncontiguous chapters can break that relationship, with fallback banks concealing the mismatch. Schema validation should enforce identities and references before content enters service.

At import time, APP_DATA and JSON_DATA preload. Track bundles load on demand into a process-global dictionary. Selecting a track explicitly recompiles its bundle and overwrites the cache, even if it was previously cached. There is no eviction, TTL, version-based invalidation, or memory budget. No server image-decoding mechanism is shown; content caching and browser texture caching are separate concerns.

The cache is keyed only by track ID. Any authenticated player can submit custom data/boss folder strings through track selection. The loader accepts existing absolute paths and relative paths without an approved-root check. This is not proven arbitrary-file exfiltration, but it exposes server filesystem selection and allows a user to overwrite a process-global track bundle affecting others. Unknown track IDs are accepted and can grow the cache. Restrict these capabilities to authorized content administration, validate an allowlist, and include content version in cache identity.

The image route searches every configured track boss folder in order and returns the first matching basename, not the current player’s track. Duplicate filenames can therefore display the wrong track’s artwork. The bundle’s custom boss directory is not the decisive input to this route. There are no explicit immutable cache headers in the route, although FileResponse may provide framework defaults.

Browser unload behavior is not auditable because the Phaser scene/JavaScript code is missing. No claim about texture cleanup, preloading, aborting old requests, GPU memory, audio lifecycle, or Safari behavior is justified from Python alone.

**Confirmed content-exposure path**

`serve_boss_image` is registered at `/bosses/{filename:path}` and `/static/assets/bosses/{filename:path}`. It has no authentication dependency. It reduces the filename to a basename, then returns any matching file from searched locations. There is no image-extension or MIME allowlist. One fallback location is `root/data`.

Using the unmodified resolver function and a harmless local fixture, requesting the basename `chapter_01.json` selected and returned that JSON file from `data/`. If a deployed installation keeps chapter files there, the image route can expose entire question banks, including answer keys. If `tracks_config.json` exists in root/data, that configuration is also eligible. This finding is conditional on file layout; it does not prove every nested track JSON is directly reachable or that arbitrary system files are exposed.

The basename conversion reduces ordinary path traversal; it does not prevent this legitimate-directory file disclosure. Fix by separating image storage from private content, resolving explicit asset IDs through a track-aware allowlist, limiting served formats, and validating resolved paths. Do not mount question-bank directories as public assets. Then test that JSON/config requests are rejected.

This is the main revision to the earlier assessment that server-side JSON could remain protected: the storage format is reasonable, but this file-serving route undermines the boundary.

**Other production observations**

Database access is synchronous. SQLite is the default; PostgreSQL can be selected through the connection URL, but an async PostgreSQL migration is not implemented merely because drivers are listed. Startup uses create_all plus a limited SQLite ALTER TABLE routine; it does not migrate every newer column. No shipped Alembic migration tree was present. SQLite foreign-key enforcement is not explicitly enabled in the supplied engine setup, so do not assume database-level cascades merely from ForeignKey declarations.

Redis and Alembic dependencies appear in the manifest, but no implemented Redis content cache, distributed limiter, or migration history was supplied. Administrator sessions live in process memory and therefore are not shared across workers. Auth endpoints and admin login have rate limits; battle routes do not show rate-limit decorators. The in-memory limiter is disabled under testing.

The settings retain default admin/admin credentials and do not fail startup in production if those remain unchanged. Cookie security is separately configured and is not automatically implied by ENVIRONMENT=production. CSP explicitly permits unsafe-inline scripts, contrary to the cookbook’s stricter claim. These are configuration/code risks, not proof of an exposed deployment.

**Visual assessment of the eight supplied assets**

All eight PNGs have alpha channels. Five larger player images are 1024×1536; three others are smaller. All have alpha extrema 0–254, rather than fully opaque 255 pixels. This is not a legal issue but suggests an export/processing characteristic to review against actual backgrounds. Large PNG sizes may affect mobile startup; measure loading with the missing frontend before changing formats.

| File | Visible design | Teaching/IP observation |
|---|---|---|
| player-research-alchemist.png | Older scholar, green robes, book, flask equipment and orbital staff | Strong chemistry-fantasy identity; generic orbital ornament is not an exact scientific diagram |
| player-catalysis-adept.png | Adventurer with teal/orange energy orbs and alchemical equipment | Catalyst identity is mostly thematic without an explanatory interaction |
| player-compound-artificer.png | Ornate robes, floating colored crystal/flame forms, instruments | Detailed fantasy presentation; compound construction is not mechanically shown |
| player-molecular-analyst.png | Glasses, book, blue coat, hovering molecular imagery | Recognizable scientific cues, but no actual analysis task established |
| player-carbon-trailblazer.png | Field chemist with green flask, molecular model and satchel | Tangible chemistry apparatus gives a clearer subject cue |
| reaction-mage.png | Purple-haired mage holding flame and reagent vials | Fantasy spell archetype; chemical specificity is limited |
| organic-apprentice.png | Glasses, lab coat, green flask and shoulder bag | Clear chemist role and a youthful anime presentation |
| carbonyl-dragon.png | Dark red/black dragon, flame, oxygen/carbon motif on wing | Only supplied creature illustration; identity and role in active combat cannot be inferred solely from its filename |

No obvious Prodigy logo or branded text was visible in these eight assets. This is not a character-by-character comparison with Prodigy’s entire catalog and cannot prove original authorship. The supplied human artwork is detailed, anime/fantasy-oriented. Generic robes, dragons, magic, and molecular motifs do not themselves identify a copied character. No assessment of the absent 155-boss collection is possible.

ASSET_SOURCES.md is principally an inventory of paths, sizes, and descriptions. It does not provide author identities, original sources, licenses, generation records, purchase records, or ownership assignments. “Stored locally” and “custom” are not provenance evidence. The document also references many images that are not in this ZIP.

**Teaching capability and differentiation**

The available implementation can deliver short vocabulary questions, impose a consequence, provide feedback, and record battle position. These features may support repeated practice. The sample’s balanced answer positions are a positive feature, although order repeats on replay.

The built-in fallback is much weaker: three chapters and fifteen bosses share the same six questions, all with the correct answer first in backend order. The original loader confirmed that the archive’s default JSON load falls back to this bank because the production data directory is absent. The missing frontend might shuffle choices, but that is unverified. Silent fallback should never be allowed to masquerade as a complete advanced curriculum.

No runtime mechanic asks the player to align an SN2 backside attack, select an electrophilic atom, count aromatic electrons, construct a Diels–Alder product, or interpret NMR. Those ideas appear in bestiary prose. The supplied evaluator only needs spell ID, an answer string, HP, and damage. It does not read a chemical structure or concept-specific boss ability. Consequently, chemistry is currently connected most strongly through question content and artwork, not through the combat rules themselves.

Recommended instructional changes: retain stable question/concept IDs; correct explanation collisions; author misconception-specific feedback; distinguish vocabulary recognition from application; require objective coverage and unseen exit items; schedule later review; log attempts durably; measure learning with independent pre/post and delayed tasks. A failed fight and a mastered concept should be separate state variables. Avoid claiming prevention of cognitive fatigue, dual-coding effectiveness, or mastery without evidence from the actual interaction and evaluation.

**Comparison with current Prodigy**

The verified Organic Battles loop differs from Prodigy’s published current combat description. Prodigy describes spells consuming magic points, correct answers replenishing them, elemental advantages, and speed-based attack order. Organic Battles directly grades each selected attack and uses wall-clock cooldowns with full-damage backfire. [Prodigy battle guide](https://prodigygame.zendesk.com/hc/en-us/articles/12910978061844-Battling-in-Prodigy-Math)

| Dimension | Supplied Organic Battles | Prodigy’s published offering |
|---|---|---|
| Educational scope | Chemistry vocabulary in available sample | Curriculum-aligned math practice |
| Question selection | Fixed sequence and wraparound | Adaptive practice and placement |
| Progression | Boss HP and completion flags | Battles, exploration, quests, and pet collection |
| Tactical variables | Damage, cooldown, random counterattack | Magic points, elements, speed |
| Teacher features | Operational administration | Assignments and learning reports |
| Social/commercial features | No supplied multiplayer or billing implementation | Social gameplay and optional memberships |

These are product-feature comparisons, not a controlled effectiveness ranking. [Prodigy product description](https://www.prodigygame.com/main-en/prodigy-math)

Organic Battles’ best opportunity is to make chemistry reasoning part of the player’s action selection. Adding more generic spells or reproducing a pet economy would contribute less educational differentiation than substrate selection, reagent choice, stereochemical manipulation, or mechanism construction.

**Updated Prodigy and textbook IP assessment**

No specific act of infringement was established. A case-insensitive search of supplied text did not identify a Prodigy reference, and no Prodigy marks were visible in the eight supplied PNGs. This is limited negative evidence: there is no development history, full asset set, or comparison of source lineage.

Copyright generally does not protect a game idea or playing method, but can protect expressive artwork, text, and other creative material. Independent implementation of questions powering combat is not automatically infringement. Replacing math with chemistry would not cure copying protected expression. [U.S. Copyright Office: Games](https://www.copyright.gov/register/tx-games.html)

| Issue | Evidence-based conclusion |
|---|---|
| Shared educational battle idea | Similarity alone does not establish copyright infringement |
| Copied Prodigy code | Not established; proprietary source and development lineage were not available |
| Copied Prodigy artwork | No obvious branded assets in the eight inspected PNGs; absent bosses and frontend remain unreviewed |
| Name/logo clearance | Organic Battles differs textually from Prodigy, but no comprehensive trademark clearance was performed |
| Patented implementations | Not cleared; feature differences do not replace a claim-by-claim review |
| Prodigy service terms | Material unresolved contract question, dependent on accepted terms and development history |
| Textbook questions/figures | Alignment is documented; copying or commercial reuse permission is not established |
| Original asset ownership | Provenance/assignments not supplied |
| Commercial model | No implementation of billing/currency found; charging for a game alone is not proof of copied expression |

Prodigy’s published terms restrict supporting competing products or products with similar features and also restrict copying and reverse engineering. Counsel should assess applicability and enforceability against the actual accounts, accepted versions, jurisdiction, and activities. The provision is a contractual issue; it does not establish ownership of all educational game ideas or bind every competitor automatically. [Prodigy terms](https://www.prodigygame.com/main-en/terms-and-conditions)

Trademark analysis addresses likely confusion about source or affiliation, not only exact matching names. Review Organic Battles against relevant educational/game names and logos, and review the final combined UI and promotional presentation. [USPTO trademark infringement guidance](https://www.uspto.gov/page/about-trademark-infringement)

The archive’s textbook references are inconsistent: the implementation prompt refers to Klein’s fifth-edition study guide/solutions manual; AdvancedBestiary.md identifies Klein’s third edition; FoundationalBestiary.md uses “Organic Battles: OpenStax Edition” and aligns to McMurry’s 31 chapters. Establish the actual source and edition per track before claiming alignment.

A favorable record exists: the implementation prompt explicitly requires original question wording and forbids copying textbook definitions or passages verbatim. That documents intent, not compliance. The available sample consists of short definitions of standard chemical concepts; no substantial copied passage was established. Neither a full textbook comparison nor an audit of missing question banks was possible. Rewording copied problems, figures, distractor sets, or a distinctive compilation does not automatically resolve rights issues. Attribution and educational purpose are not blanket permissions. [Copyright Office fair-use FAQ](https://www.copyright.gov/help/faq/faq-fairuse.html)

The current OpenStax Organic Chemistry page displays CC BY-NC-SA licensing and separately reserves its branding. If content is reused, examine the exact acquired version and applicable license; the current notice does not retroactively settle older license grants. “Free to read” does not itself authorize commercial adaptation. “OpenStax Edition” may suggest affiliation; use accurate independent alignment wording and review branding permissions. [OpenStax current notice](https://openstax.org/books/organic-chemistry/pages/1-why-this-chapter)

Patent freedom to operate requires checking relevant enforceable claims in intended markets, including third-party patents. The source review does not settle that question, and independent creation is not a universal defense to patent infringement. [USPTO patent guidance](https://www.uspto.gov/patents/basics/manage)

For any AI-generated assets, retain prompts, reference inputs, dated outputs, human revisions, and governing service terms. If relying on copyright ownership, distinguish human-authored contributions from purely generated material. No determination of each asset’s origin can be made from appearance alone. [U.S. Copyright Office: AI copyrightability](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)

**Prioritized correction plan and acceptance criteria**

| Order | Change | Completion evidence |
|---|---|---|
| 1 | Enforce ownership on every explicit-session operation | User B cannot read, cast, answer, advance, retry, or switch User A’s session |
| 2 | Enforce valid transitions and atomic turn consumption | A live boss cannot be completed; duplicate submissions and stale turns do not mutate state |
| 3 | Separate public assets from private content | JSON/config requests through asset routes fail; active-track image resolves deterministically |
| 4 | Replace prompt-keyed data with versioned question IDs | All 50 sample explanations match their originating records; repeated stems remain independent |
| 5 | Restrict content folder overrides and validate track IDs | Ordinary players cannot overwrite shared track content or select server filesystem locations |
| 6 | Repair per-track saves and transition cleanup | HP, cursor policy, pending state, completions, and admin actions follow one documented model |
| 7 | Fail visibly on missing/malformed curriculum | No silent advanced-to-six-question fallback; invalid answer keys/HP/damage rejected |
| 8 | Separate mastery from damage | All required objectives assessed, including hard/application items that combat could otherwise skip |
| 9 | Reconcile catalog and documentation | One source defines spell damage/cooldowns; generated inventory reflects shipped content |
| 10 | Finish content and asset provenance plus legal review | Source/license ledger, name/logo review, terms-history assessment, targeted patent review |
| 11 | Inspect missing frontend and deployment | Browser memory, preload, answer display, accessibility, multi-tab races, and supported browsers verified |

The architecture is usable as a foundation. Commercial readiness should wait for the confirmed state-integrity, authorization, content-exposure, and feedback defects to be resolved. The IP conclusion remains narrower: no specific Prodigy infringement was demonstrated, but there is not enough evidence for a clearance statement.

To complete the remaining review, supply `static/`, `data/` including all tracks/manifests/configuration and images, the full boss collection, and source/license records. The already-reviewed backend need not be uploaded again unless it has changed.

**Validation record**

Seven existing domain tests were executed directly with their original assertions:

- `test_grade_answer_exact_and_case_insensitive`: passed.
- `test_spell_catalog_integrity`: passed.
- `test_combat_turn_correct_answer_deterministic`: passed.
- `test_combat_turn_correct_with_counterattack_deterministic`: passed.
- `test_combat_turn_fizzle_backfires_on_player`: passed.
- `test_cooldown_management_pure_domain`: passed.
- `test_content_source_priority_resolution_pure`: passed.

Additional isolated checks reproduced: advance on a live boss; spell selection against another fixture user’s session; omission of answer keys from the pending-question payload; cursor advancement after failure; cursor retention and stale turn ID after retry; a pending question surviving advancement; same-track HP reset; switching after an intermediate defeated mini-boss; and non-image JSON selection by the asset resolver. These used fake repositories and local fixtures, not an HTTP deployment. The loader returned three chapters/six questions for the incomplete archive and one chapter/five bosses/fifty questions for the supplied sample fixture. Nine explanation mismatches were counted.
