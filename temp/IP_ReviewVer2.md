# Organic Battles: IP, Design, Code, and Production Readiness Review

Updated September 9, 2026. This revision incorporates app.zip and the later avatars.zip containing static/, data/, all supplied chapter JSONs, and selected boss-image directories. It supersedes the earlier cookbook-only and incomplete-archive assessments wherever the additional implementation provides stronger evidence.

**Principal finding.** Organic Battles implements a chemistry multiple-choice battle game with persistent state, sequential questions, and damage-based advancement. The expanded content goes beyond vocabulary into mechanisms, synthesis, spectroscopy, laboratory practice, and quantitative reasoning. However, seven foundational track paths silently load the default curriculum; 7,300 foundational records match obvious placeholder patterns; 1,066 records retrieve an explanation belonging to another record; and several advanced tracks repeat very small question sets. These are immediate obstacles to credible teaching claims. Previously confirmed authorization and progression defects remain in the supplied backend.

No specific Prodigy infringement was established. The supplied art has a consistent chemistry-fantasy presentation without an obvious Prodigy logo or branded text. The owner's statement that bosses were generated individually with ChatGPT is useful provenance information, but one-time generation does not establish noninfringement, uniqueness, or exclusive copyright. Textbook source and commercial-license questions remain unresolved.

This is an engineering and preliminary U.S.-focused IP assessment, not a legal opinion or worldwide freedom-to-operate clearance. Findings concern the uploaded snapshot, not a verified deployment on the owner's Windows computer. No application source was changed.

This edition reorganizes the completed source and asset audit into the requested decision areas. Findings remain grounded in the same uploads; no new application changes or deployment tests are implied. Future applications are proposals, not implemented features or proven learning outcomes.

## Contents

1. [IP review](#1-ip-review)
2. [IP infringement: findings and unresolved questions](#2-ip-infringement-findings-and-unresolved-questions)
3. [Design issues](#3-design-issues)
4. [Code issues](#4-code-issues)
5. [Mandatory fixes for production upgrades](#5-mandatory-fixes-for-production-upgrades)
6. [Design strengths and appreciation](#6-design-strengths-and-appreciation)
7. [Near-future applications](#7-near-future-applications)
8. [Longer-term applications](#8-longer-term-applications)
9. [Evidence, implementation corrections, and validation](#9-evidence-implementation-corrections-and-validation)

## 1. IP review

The review separates rights in the game's individual components from the question of whether someone else's rights have been infringed. The broad idea of answering educational questions to power a battle is different from the specific code, illustrations, wording, interface, and branding used to express it.

| Component | Rights/provenance review needed | Present evidence |
|---|---|---|
| Application code | Authorship, contributor assignments, dependency licenses, any copied code | Supplied source reviewed; complete development lineage and dependency license inventory not established |
| Game rules | Distinguish general mechanics from protected expression and any relevant patent claims | Damage, cooldowns, quizzes, bosses, and progression traced; no patent clearance performed |
| Questions and explanations | Independent authorship or applicable reuse rights; identify textbook edition and source inputs | All supplied chapter records scanned; textbook-by-textbook copying comparison not completed |
| Boss/avatar artwork | Generation records, reference inputs, human contributions, rights held by publisher | User reports individual ChatGPT generation; 27 distinct valid images inspected |
| Name, logo, marketing | Trademark clearance and source/affiliation confusion | No comprehensive Organic Battles name/logo clearance performed |
| Interface and audiovisual presentation | Original expressive choices, third-party material and applicable licenses | Frontend source and supplied art reviewed; audio is procedurally synthesized |
| Private question banks | Access restrictions, source-license obligations, and controlled delivery | Stored server-side, but image-serving boundary and content-management permissions need repair |

### Legal and source-provenance assessment

No specific act of infringement was established. No obvious Prodigy marks were visible in the 27 distinct valid images inspected. The supplied implementation and chemistry-fantasy presentation support a narrower conclusion: shared educational combat mechanics do not establish copying. The review does not establish code lineage, verify every image against all competing catalogs, or clear the Organic Battles name.

Copyright generally does not protect a game idea or playing method, but can protect expressive artwork, text, and other creative material. Independent implementation of questions powering combat is not automatically infringement. Replacing math with chemistry would not cure copying protected expression. [U.S. Copyright Office: Games](https://www.copyright.gov/register/tx-games.html)

| Issue | Evidence-based conclusion |
|---|---|
| Shared educational battle idea | Similarity alone does not establish copyright infringement |
| Copied Prodigy code | Not established; proprietary source and development lineage were not available |
| Copied Prodigy artwork | No obvious Prodigy marks in inspected images; frontend source now reviewed; remaining referenced artwork not supplied |
| Name/logo clearance | Organic Battles differs textually from Prodigy, but no comprehensive trademark clearance was performed |
| Patented implementations | Not cleared; feature differences do not replace a claim-by-claim review |
| Prodigy service terms | Material unresolved contract question, dependent on accepted terms and development history |
| Textbook questions/figures | Alignment is documented; copying or commercial reuse permission is not established |
| Original asset ownership | Owner reports individual ChatGPT generations; creation records and any company assignments not supplied; human-authorship limits apply |
| Commercial model | No implementation of billing/currency found; charging for a game alone is not proof of copied expression |

Prodigy’s published terms restrict supporting competing products or products with similar features and also restrict copying and reverse engineering. Counsel should assess applicability and enforceability against the actual accounts, accepted versions, jurisdiction, and activities. The provision is a contractual issue; it does not establish ownership of all educational game ideas or bind every competitor automatically. [Prodigy terms](https://www.prodigygame.com/main-en/terms-and-conditions)

Trademark analysis addresses likely confusion about source or affiliation, not only exact matching names. Review Organic Battles against relevant educational/game names and logos, and review the final combined UI and promotional presentation. [USPTO trademark infringement guidance](https://www.uspto.gov/page/about-trademark-infringement)

The archive’s textbook references are inconsistent: the implementation prompt refers to Klein’s fifth-edition study guide/solutions manual; AdvancedBestiary.md identifies Klein’s third edition; FoundationalBestiary.md uses “Organic Battles: OpenStax Edition” and aligns to McMurry’s 31 chapters. Establish the actual source and edition per track before claiming alignment.

A favorable record exists: the implementation prompt explicitly requires original question wording and forbids copying textbook definitions or passages verbatim. That documents intent, not compliance. The expanded bank contains definitions and application questions, with substantial templating and repetition. No substantial copied textbook passage was established by this review. All supplied chapter JSONs were scanned, but a line-by-line comparison with the relevant textbook editions, figures, exercises, and solutions was not performed. Rewording copied problems, figures, distractor sets, or a distinctive compilation does not automatically resolve rights issues. Attribution and educational purpose are not blanket permissions. [Copyright Office fair-use FAQ](https://www.copyright.gov/help/faq/faq-fairuse.html)

The current OpenStax Organic Chemistry page displays CC BY-NC-SA licensing and separately reserves its branding. If content is reused, examine the exact acquired version and applicable license; the current notice does not retroactively settle older license grants. “Free to read” does not itself authorize commercial adaptation. “OpenStax Edition” may suggest affiliation; use accurate independent alignment wording and review branding permissions. [OpenStax current notice](https://openstax.org/books/organic-chemistry/pages/1-why-this-chapter)

Patent freedom to operate requires checking relevant enforceable claims in intended markets, including third-party patents. The source review does not settle that question, and independent creation is not a universal defense to patent infringement. [USPTO patent guidance](https://www.uspto.gov/patents/basics/manage)

The owner reports generating each boss with ChatGPT, one image at a time using chapter details. That is a meaningful account of independent creation, and is recorded as such. **“Generated for the first time, once” is not a legal test for copyright clearance.** Three separate questions must be kept distinct:

1. **Rights under the generation service.** OpenAI's individual terms allocate output rights between the user and OpenAI to the extent allowed by law, while warning that outputs may not be unique and placing responsibility for input permissions and lawful content on the user. The terms also disclaim noninfringement warranties. The applicable account, region, plan, and terms at generation time matter. [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/)
2. **Third-party rights.** A newly generated file can still resemble protected characters or artwork. A prompt based only on chemical concepts is stronger provenance than one supplying protected character images, but the original prompts and reference inputs have not been examined. Generation service ownership terms do not extinguish other parties' rights.
3. **Copyright in the generated image itself.** Under the U.S. Copyright Office's stated approach, purely AI-generated expression lacks the necessary human authorship; prompts alone generally do not establish sufficient control. Human-authored selection, arrangement, or modifications may be protectable on their own facts. Lack of copyright in a generated portion does not mean commercial use is automatically prohibited, and does not mean the image is necessarily free of third-party rights. [U.S. Copyright Office: AI copyrightability](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)

Retain dated generation conversations, all reference inputs, original outputs, human edits, and applicable service terms. Record who created or commissioned each asset and how relevant rights move to the publishing company. ASSET_SOURCES.md currently functions mainly as an inventory; file paths and descriptions alone are not a license chain. The same principle applies to question generation: chapter concepts may guide independently authored questions, but uploading or paraphrasing protected exercises/solutions can raise separate rights questions.

The supplied frontend and procedural audio do not reveal a copied Prodigy interface or sound recording. This is limited evidence, not a complete trade-dress or software-license audit. Preserve notices for third-party libraries, fonts, and external dependencies; distinguish those from original application code. No paid membership or billing implementation was found in the supplied snapshot, and a generally similar commercial model would not itself establish copying.

## 2. IP infringement: findings and unresolved questions

**No specific infringement was established from the supplied materials. This is not an infringement-free certification.** The table separates an observed issue from a possibility that still needs evidence. Engineering defects, weak content, and visual resemblance at the level of a genre do not by themselves establish infringement.

| Question | Finding | What remains to resolve |
|---|---|---|
| Does educational question-driven combat itself copy Prodigy's copyright? | Shared mechanics alone do not establish infringement | Whether specific protected expression was copied |
| Is copied Prodigy code established? | No | Source lineage, contributor history, and any imported code |
| Is copied Prodigy artwork or branding established? | No obvious Prodigy marks in inspected art; no specific copied asset identified | Remaining artwork and targeted similarity review if a recognizable resemblance is found |
| Does one-time ChatGPT generation guarantee clearance? | No; it documents a process, not a legal conclusion | Prompts, reference images, outputs, applicable terms, and human edits |
| Are textbook rights cleared? | No; neither infringement nor complete permission was established | Exact source/edition, generated-question inputs, copied figures/problems, and commercial reuse terms |
| Does the Organic Battles name infringe a trademark? | Not determined | Relevant-market name/logo search and likelihood-of-confusion assessment |
| Is there patent infringement? | Not determined | Relevant enforceable claims in intended markets; this review did not conduct a patent search |
| Could Prodigy terms create a contractual problem? | Potentially, depending on actual use and accepted terms | Accounts, versions, activities, jurisdiction, and enforceability |
| Is charging for an educational RPG itself proprietary to Prodigy? | No such exclusive right was established | Rights in particular copied content or covered implementations remain separate |

The practical conclusion is to preserve the independently developed chemistry direction while completing provenance and release-specific legal review. There is no evidence-based reason here to discard the whole concept merely because Prodigy also combines learning and battles. Equally, changing the subject to chemistry would not cure copying if protected artwork, code, questions, or distinctive presentation had actually been taken. The legal sources supporting these distinctions appear in Section 1.

### Product comparison with Prodigy

The verified Organic Battles loop differs from Prodigy’s published current combat description. Prodigy describes spells consuming magic points, correct answers replenishing them, elemental advantages, and speed-based attack order. Organic Battles directly grades each selected attack and uses wall-clock cooldowns with full-damage backfire. [Prodigy battle guide](https://prodigygame.zendesk.com/hc/en-us/articles/12910978061844-Battling-in-Prodigy-Math)

| Dimension | Supplied Organic Battles | Prodigy’s published offering |
|---|---|---|
| Educational scope | Chemistry MCQs across vocabulary and advanced reasoning; substantial content defects | Curriculum-aligned math practice |
| Question selection | Fixed sequence and wraparound | Adaptive practice and placement |
| Progression | Boss HP and completion flags | Battles, exploration, quests, and pet collection |
| Tactical variables | Damage, cooldown, random counterattack | Magic points, elements, speed |
| Teacher features | Operational administration | Assignments and learning reports |
| Social/commercial features | No supplied multiplayer or billing implementation | Social gameplay and optional memberships |

These are product-feature comparisons, not a controlled effectiveness ranking. [Prodigy product description](https://www.prodigygame.com/main-en/prodigy-math)

Organic Battles’ best opportunity is to make chemistry reasoning part of the player’s action selection. Adding more generic spells or reproducing a pet economy would contribute less educational differentiation than substrate selection, reagent choice, stereochemical manipulation, or mechanism construction.

## 3. Design issues

These issues concern what the game asks the learner to do, how feedback works, and what progression signifies. They would remain important even if every API and database operation were technically correct.

| Design issue | Consequence for the learner | Recommended design decision |
|---|---|---|
| Boss defeat stands in for achievement | Damage efficiency and random survival can be mistaken for mastery | Separate combat completion from objective-level learning evidence |
| Sequential questions and stable answer order | Replay can reward sequence/position memory | Use controlled variation and objective coverage; keep stable IDs internally |
| Placeholder and heavily repeated content | The stated curriculum can exceed what the player actually practices | Publish validated coverage and unique-item counts; quarantine incomplete content |
| Optional failure explanation, limited success explanation | Incorrect reasoning may persist; correct guessing is not examined | Offer concise reasoning after either outcome, with deeper review available |
| Chemistry-themed spells lack chemical constraints | Names and art imply abilities the rules do not implement | Add a small number of meaningful concept-specific interactions |
| HP loss includes randomness | Accurate players can lose for reasons unrelated to understanding | Explain combat risk and keep it separate from assessment results |
| Track switching resets partial battles | “Resume” does not consistently mean resume the same learning state | Define and communicate resume, restart, practice, and track-switch policies |
| Boss art doubles as a concept cue | Decorative structures can be mistaken for scientific evidence | Use separately validated diagrams when a task depends on exact chemistry |

### Scoring, rewards, and combat

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

### Full curriculum audit and teaching quality

The expanded bank materially changes the earlier vocabulary-only assessment. Advanced tracks include genuine text-based mechanism reasoning, reaction outcomes, multistep synthesis, spectroscopy, stereochemistry, medicinal chemistry, laboratory reasoning, and thermodynamic calculations. However, all are presented through the same multiple-choice renderer; a question-type label does not activate a mechanism editor, molecule viewer, spectrum plot, or synthesis workspace.

The most serious routing problem affects all seven foundational tracks. Both `data/tracks_config.json` and `static/js/tracks-config.js` use the nonexistent folder names below, under `data/tracks/foundational/`:

| Track | Configured folder | Actual supplied folder |
|---|---|---|
| found-nomenclature | FoundationalNomenclatureData | VocabularyConceptsData |
| found-outcomes | FoundationalReactionOutcomesData | ReactionOutComeTypesData |
| found-mechanisms | FoundationalMechanismsData | MechanismsIntermediatesData |
| found-stereo | FoundationalStereochemistryData | StereochemistryStructureData |
| found-property | FoundationalPropertyRankingsData | RelativePropertyRankingsData |
| found-spectra | FoundationalSpectroscopyData | SpectroscopyElucidationData |
| found-synthesis | FoundationalMultiStepSynthesisData | MultiStepSynthesisData |

The original `load_track_bundle` resolves all seven to **data/tracks/default: 27 chapters and 1,350 questions**, despite their intended 31 chapters and 1,550 questions each. Default and all 12 advanced track paths resolve correctly. A menu can therefore advertise a foundational specialty while delivering the default bank. Generate the frontend track list from validated server metadata and fail visibly on unresolved paths. Fixing paths alone is insufficient because the intended foundational content has the following defects.

An exact-pattern scan found **7,300 placeholder-style records**, about **67.3% of the foundational bank**:

| Foundational content | Matching records | Representative answer pattern |
|---|---:|---|
| Mechanisms/intermediates | 1,450 | Formation of key intermediate N via concerted electron-pair transfer |
| Multistep synthesis | 1,500 | Reagent A → Reagent B → Target Molecule N (high yield) |
| Relative-property rankings | 1,450 | Compound A < Compound B < Compound C < Compound D (correct progression) |
| Spectroscopy | 1,450 | Diagnostic resonance peak N at characteristic frequency/chemical shift |
| Stereochemistry/structure | 1,450 | Specific stereochemical assignment N with defined 3D configuration |

Here N represents varying literal numbers in the JSON. Unspecified compounds, reagents, structures, and resonances do not provide enough information for an objective chemistry problem. The boss artwork is not a substitute for the missing substrate or spectrum. Quarantine these records for authoring and expert review before enabling the corrected tracks.

Record volume also overstates variation in several advanced tracks. To measure a specific kind of repetition, the audit replaced only “Chapter <number>” with a common token in prompts, choices, and answers, then ignored option order and compared the resulting prompt/choice-set/answer tuples:

| Advanced track | Records | Distinct tuples after this normalization |
|---|---:|---:|
| Laboratory, medicinal, multistep synthesis, skill-builder, thermodynamics | 1,350 each | 20 each |
| Orbital/pericyclic, property rankings, spectroscopy | 1,350 each | 30 each |
| Stereochemistry | 1,350 | 90 |
| Mechanisms | 1,350 | 270 |
| Reaction outcomes | 1,350 | 921 |
| Vocabulary | 1,350 | 1,350 |

This is a transparent text-repetition measure, not a semantic concept count or a claim that every repetition is inappropriate. Planned retrieval practice can repeat an item; relabeling the same item for many chapters should not be represented as new chapter-specific coverage. For example, the same laboratory E-factor problem with 10 kg product and 250 kg waste recurs across chapters, as do medicinal eutomer/distomer definitions and a primary-alcohol-to-amine synthesis sequence.

Across all tracks, 26,721 exact prompt/ordered-choice/answer tuples remain before this normalization. Different distractor order inflates that number. Neither figure proves 26,721 distinct educational problems.

Sampled wording also needs chemistry editing. An advanced ranking prompt combines increasing thermodynamic stability with “lowest to highest heat of combustion,” which needs clarification because these orderings do not express the same stability criterion. A reaction-outcome template asks for an organic product of HCl in water while its answer is hydronium and chloride. The acid reaction itself is not the issue; the generic “organic product” wording is. Structural validation cannot replace subject-matter review.

The original temp sample remains useful as a narrow illustration: 50 questions covering ten vocabulary topics, 20 easy/20 medium/10 hard, five boss groups, and answer positions A/B/C/D = 10/14/13/13. Its labels do not establish advanced reasoning. The next progression calculation is explicitly for that sample and must not be generalized numerically to every track.

### Progression can omit most difficult material even during honest play

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

### Teaching capability and differentiation

The updated assessment is **broad chemistry practice with substantial content-quality and mastery-tracking gaps**. It is no longer accurate to characterize the full supplied bank as vocabulary only. Text-based MCQs can ask meaningful mechanistic, synthetic, spectral, and quantitative reasoning; the game can deliver those questions, impose a combat consequence, explain errors, and retain battle position.

However, current question selection is sequential, difficult items can be skipped through efficient damage, failed items are not deliberately rescheduled, and the saved state is not a durable concept-level evidence record. The seven silently redirected tracks, placeholder items, explanation collisions, and extensive repetition further weaken teaching reliability. A large number of JSON records is not evidence of curriculum coverage, retention, or transfer.

Chemistry affects combat through answer correctness and configured damage. There is no implemented requirement to draw curved arrows, choose a reacting atom on a structure, orient a backside attack, build a product, or manipulate a spectrum. Bestiary descriptions of chemistry-specific abilities are not executed by the combat evaluator. Artwork can support memorable associations, but its instructional effect has not been measured.

Repair content and feedback first; then preserve concept/question IDs, record attempts durably, distinguish mastery from combat survival, require objective coverage and unseen exit questions, and schedule later retrieval. Evaluate learning with independent pre/post and delayed tasks before claiming mastery, reduced cognitive fatigue, or superior educational effectiveness. A research/design paper can accurately describe these as design hypotheses and implementation limitations rather than validated outcomes.

## 4. Code issues

These findings identify implementation behavior and failure modes. A source-confirmed defect is distinguished from a deployment risk that still requires integration or load testing. File/function references and reproduction limits are retained below.

### Question selection and answer validation

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

### Confirmed explanation collisions and content validation

The loader stores `explanations[prompt]`, so a later record with the same prompt replaces an earlier explanation. Grading still uses the active question's answer. A correct grade can therefore accompany unrelated teaching feedback.

Running the original loader across all supplied content folders produced **1,066 explanation mismatches**:

| Content folder | Records retrieving a different explanation |
|---|---:|
| Default | 271 |
| Advanced VocabularyConceptsData | 486 |
| Foundational VocabularyConceptsData | 309 |
| Total | 1,066 |

These counts compare each record's own explanation with the bundle's actual prompt-keyed lookup. They are content-bank counts, not measured player exposures; the foundational path defect currently prevents normal selection of its intended bank. The earlier 50-question temp sample independently produced nine mismatches and is not added to this total.

Damage maps also use prompt-based keys. Even `(chapter, boss, prompt)` can collide within a repeated-stem bank. Preserve `(track, content_version, question_id)` and snapshot explanation and damage with the active question.

All 28,400 chapter records have four choices, their declared answer occurs among the choices, their declared correct-option label agrees with that answer, and scanned HP/damage entries are positive. This validates internal format consistency, not chemical truth. **110 foundational reaction-outcome records contain duplicate option text; 57 contain the correct answer twice.** Text-based grading then accepts either identical button, undermining a single-best-answer design. There are 270 default explanations that simply equal the answer text.

### Critical progression and authorization defects

P0 means address before public release; severity here describes engineering priority, not a formal CVSS score.

| Priority / finding | Evidence and effect | Required behavior | Status |
|---|---|---|---|
| P0: Advance without victory | `next_turn` records completion and advances without checking boss HP, player HP, or pending question. Isolated call advanced a full-health 100-HP boss and marked it completed. | Require a valid defeated-boss state; make completion idempotent and atomic. | TODO |
| P0: Session ownership missing | Battle selection, answer, next-turn, and retry use `get_by_id(session_id)` without comparing owner with current user. Repository does not add ownership filtering. Selection accepted a fixture session belonging to another user. | Query by session ID AND authenticated owner on every operation. | FIXED |
| P0: Old question survives advance | `next_turn` does not clear active question/spell/turn ID. Harness advanced to another boss with the old question pending. | Reject invalid transitions and bind each pending turn to its boss/content version. | FIXED |
| P1: No atomic turn consumption | `version += 1` has no compare-and-swap filter; no row lock, version mapper, or validated idempotency key. | Serialize or conditionally update turns and record consumed identifiers. | FIXED |
| P1: Unrestricted retry | Retry does not require player defeat; restores both HP pools and preserves cursor. It also leaves stale `turn_id`. | Deliberately define practice restart versus defeat retry and reset all dependent state. | FIXED |

Session IDs are not trivially predictable; the ownership issue requires knowledge of a victim session ID. That mitigates discovery but does not replace authorization. The normal state-read endpoint does perform an ownership check, demonstrating inconsistent protection rather than an absence of authentication everywhere. Other explicit-session routes, including track selection and avatar finalization, also need ownership review.

The concurrency issue is established by code inspection; duplicate commits or precise race outcomes were not measured against a real database. A monotonically incremented number alone is not optimistic locking.

### Saving progress, switching tracks, and resetting

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

### Boss construction, loading, and unloading

The loader groups question records by boss name in first-occurrence order. It uses the maximum health value for that boss; the last distinct group is labelled major. First-row image/topic and spell values help define the boss. The top-level `bosses` and `boss_strategy` objects do not govern this process. A typo in a boss name can accidentally create an additional boss; slug collisions can combine banks or completion identities.

Files load in manifest order or sorted filenames. Routes frequently assume chapter position equals chapter number minus one. Missing or noncontiguous chapters can break that relationship, with fallback banks concealing the mismatch. Schema validation should enforce identities and references before content enters service.

At import time, APP_DATA and JSON_DATA preload. Track bundles load on demand into a process-global dictionary. Selecting a track explicitly recompiles its bundle and overwrites the cache, even if it was previously cached. There is no eviction, TTL, version-based invalidation, or memory budget. No server image-decoding mechanism is shown; content caching and browser texture caching are separate concerns.

The cache is keyed only by track ID. Any authenticated player can submit custom data/boss folder strings through track selection. The loader accepts existing absolute paths and relative paths without an approved-root check. This is not proven arbitrary-file exfiltration, but it exposes server filesystem selection and allows a user to overwrite a process-global track bundle affecting others. Unknown track IDs are accepted and can grow the cache. Restrict these capabilities to authorized content administration, validate an allowlist, and include content version in cache identity.

The image route searches every configured track boss folder in order and returns the first matching basename, not the current player’s track. Duplicate filenames can therefore display the wrong track’s artwork. The bundle’s custom boss directory is not the decisive input to this route. There are no explicit immutable cache headers in the route, although FileResponse may provide framework defaults.

The supplied frontend now resolves the boss lifecycle question. `static/js/main.js` creates one Phaser game, but characters are ordinary DOM avatar elements containing PNG images. `renderAvatars` replaces the boss element when its expected image URL changes. `drawScene` destroys objects tagged dynamic and draws a colored circle; it does not load boss textures or sprites into a Phaser texture manager. Consequently, a recommendation to evict boss Phaser textures would target a mechanism this implementation does not use.

The displayed boss URL is `/static/assets/bosses/<filename>?v=2`. Replaced DOM images become eligible for normal browser cleanup; HTTP/decoded-image caches can retain resources. There is no explicit next-boss preload, request cancellation, versioned content hash, or measured memory-release guarantee. The player avatar is created once; changing the selected avatar later can leave the battle-stage figure stale while the side panel updates.

Animations apply CSS classes to still images. Hit/cast/victory/defeat timers refer to mutable global avatar variables and are not cancelled on transition, so a late callback can affect a later boss. Reusing the same asset URL can preserve a prior defeated state because that branch does not recreate the element. These are source-identified lifecycle risks requiring targeted browser tests, not measured GPU leaks.

`avatars.js` retries an explicit failed image URL once, then hides the failed image in favor of fallback styling/name. A missing file can instead receive a successful placeholder SVG response from the server, bypassing that error branch. Gallery images are lazy-loaded; battle image elements use asynchronous decoding without the same lazy-loading attribute.

Audio in `audio.js` is synthesized with Web Audio oscillators rather than external sound recordings. The AudioContext is created lazily, suspended when hidden and resumed when visible; oscillators are scheduled to stop. The implementation does not explicitly close the context or disconnect every node. That alone does not demonstrate a leak, but transitions and long sessions need measurement.

### Confirmed content-exposure path

`serve_boss_image` is registered at `/bosses/{filename:path}` and `/static/assets/bosses/{filename:path}`. It has no authentication dependency. It reduces the filename to a basename, then returns any matching file from searched locations. There is no image-extension or MIME allowlist. One fallback location is `root/data`.

Using the unmodified resolver function and a harmless local fixture, requesting the basename `chapter_01.json` selected and returned that JSON file from `data/`. If a deployed installation keeps chapter files there, the image route can expose entire question banks, including answer keys. If `tracks_config.json` exists in root/data, that configuration is also eligible. This finding is conditional on file layout; it does not prove every nested track JSON is directly reachable or that arbitrary system files are exposed.

The basename conversion reduces ordinary path traversal; it does not prevent this legitimate-directory file disclosure. Fix by separating image storage from private content, resolving explicit asset IDs through a track-aware allowlist, limiting served formats, and validating resolved paths. Do not mount question-bank directories as public assets. Then test that JSON/config requests are rejected.

The later upload narrows the exposure finding: its chapter files are nested inside track-specific content directories, so this root/data basename fallback does **not** by itself expose every supplied chapter JSON. `data/tracks_config.json` is in a searched location and remains eligible. The earlier chapter-file result used an expressly documented root/data fixture. Keeping JSON server-side remains reasonable; moving to a database would not repair an overbroad asset route or prevent legitimate question-by-question collection.

### Other production observations

Database access is synchronous. SQLite is the default; PostgreSQL can be selected through the connection URL, but an async PostgreSQL migration is not implemented merely because drivers are listed. Startup uses create_all plus a limited SQLite ALTER TABLE routine; it does not migrate every newer column. No shipped Alembic migration tree was present. SQLite foreign-key enforcement is not explicitly enabled in the supplied engine setup, so do not assume database-level cascades merely from ForeignKey declarations.

Redis and Alembic dependencies appear in the manifest, but no implemented Redis content cache, distributed limiter, or migration history was supplied. Administrator sessions live in process memory and therefore are not shared across workers. Auth endpoints and admin login have rate limits; battle routes do not show rate-limit decorators. The in-memory limiter is disabled under testing.

The settings retain default admin/admin credentials and do not fail startup in production if those remain unchanged. Cookie security is separately configured and is not automatically implied by ENVIRONMENT=production. CSP explicitly permits unsafe-inline scripts, contrary to the cookbook’s stricter claim. These are configuration/code risks, not proof of an exposed deployment.

### Frontend answers, feedback, accessibility, and storage

`renderQuestion` maps choices directly into A/B/C/D buttons in source order. There is no choice shuffle. The answer handler does not immediately disable buttons or set an in-flight guard; rapid clicks can issue multiple requests before the first response. This combines with the backend's lack of atomic turn consumption. Spell controls block ordinary dead/victorious/cooldown states, but the server remains responsible for enforcing every transition.

The frontend reveals the correct answer on failure and offers “VIEW EXPLANATION.” Explanation text uses `textContent`, a positive security detail. Correct answers primarily receive combat feedback; the equivalent explanation path is not surfaced. `window.lastExplanation` stores the latest failure and can remain available across later correct answers or track changes, making stale feedback possible. Fatal wrong answers prioritize retry, with explanation accessible separately.

Question prompts, choices, some names, and battle logs are interpolated into `innerHTML`; answer strings also enter `data-answer` attributes. This is a latent content-injection/escaping risk. The audit found 3,160 records with `<` or `&` in options, but no straight double-quote characters in option text. Those counts do not prove current answers are corrupted or that the supplied content is malicious. Use DOM creation/textContent and stable option IDs to preserve chemistry notation and avoid future stored markup injection. Admin token storage in localStorage increases the potential consequence of script injection; the server also has an HTTP-only cookie path.

Cooldown displays decrement locally every 200 ms while the backend uses wall-clock timestamps; background throttling can desynchronize the display. Derive remaining time from a deadline. Some localStorage accesses are guarded, but startup accesses in main.js are not; restricted storage can break initialization. The CSS includes reduced-motion handling and the interface uses native buttons, but keyboard focus, modal focus management, screen-reader flow, touch layouts, and Safari behavior have not been certified.

The start-battle flow calls the track-selection endpoint even for the already selected track. Therefore the backend's same-track HP/pending-state reset is reachable through ordinary UI flow, not only a manually constructed request. Browser localStorage stores preferences/token-related values; the database remains the authoritative saved battle state. There is no demonstrated offline learning/queued-answer synchronization mechanism.

### Visual review and boss-file completeness

The combined upload has 40 PNG-named files but only 29 distinct byte sequences. Twenty-seven distinct images decode successfully and were visually inspected; repeated copies are not additional character designs. The two remaining files are regular text files with .png extensions, not actual PNGs or ZIP symlink entries:

- `data/tracks/advanced/bosses/13-diaxial-dreadnought.png` contains the filename `1-3-diaxial-dreadnought.png`.
- `data/tracks/advanced/bosses/14-addition-anomaly.png` contains the filename `1-4-addition-anomaly.png`.

Both target images are present, but serving the alias text as image/png will not render them. Correct references to the real filenames or create actual image copies/explicit server aliases.

Across all question rows there are 409 distinct referenced image filenames. The implemented search locations resolve 18 of those names in this upload, including the two invalid aliases; 391 referenced names are not supplied. This is an upload-completeness finding, not proof that the owner's full deployment lacks them—the owner expressly supplied only a few boss-image directories. Missing names use the server's generic fallback and can conceal coverage gaps.

| Inspected asset/design | Visual evidence and instructional implication |
|---|---|
| Orbital Ogre | Massive purple armored figure with orbit-like rings and spheres; recognizable atomic theme, not a scientifically exact orbital diagram |
| Bondbreaker Brute | Muscular figure, chains and fiery hammer; force/breaking metaphor is strong, but it does not explain bond-energy accounting |
| Amino Assassin | Agile hooded fighter, blue energy, nitrogen labels and molecular ornaments; distinct chemistry cues, no runtime nucleophile/reaction rule |
| Alcohol Alchemist | Hooded green/gold figure with flasks, staff and liquid effects; laboratory/alcohol association is thematic |
| Alkane Marauder | Heavy brown/red warrior with hexagonal ornament and axe; fierce silhouette communicates difficulty more clearly than alkane chemistry |
| Acetylide Archer | Dark armored archer with glowing blue arrow; attack metaphor could support nucleophilic targeting, but currently remains cosmetic |
| 1,3-Diaxial Dreadnought | Broad armored figure with molecular-model ornaments; needs an accurate chair-conformation overlay/task to teach diaxial interactions |
| 1,4-Addition Anomaly | Paired blue/orange humanoid aspects within one asset; suggests alternative pathways but does not specify conjugate-addition positions |
| Alkene Charger / Alkyne Overlord | Teal sword fighter and purple staff-bearing figure; strong individual silhouettes, limited self-explanatory chemical instruction |
| Carbocation Shapeshifter / Chain-Reaction Colossus | Swirling magenta spectral form and fiery mechanical giant with chains; effective mnemonic metaphors, not mechanistic simulations |
| Chemical Shift Seer | White/gold robed figure with orbital and clock-like ornaments; spectroscopy association needs actual spectral evidence in questions |
| Chiral Chimera / Conformation Mimic / Conformation Seer / Conformer Imp | Asymmetric chimera, divided-color figure, blue sorceress, and red imp; variation in shape/color does not itself demonstrate chirality or conformational equivalence |
| Carbonyl Dragon and seven human/avatar designs | Detailed fantasy/anime treatment, robes, books, flasks and molecular motifs; chemically themed roles without avatar-specific combat statistics |
| Battle arena | Dark fantasy laboratory with glowing molecular decoration; supports visual cohesion rather than assessment |

The human/player designs include Organic Apprentice, Carbon Trailblazer, Catalysis Adept, Compound Artificer, Molecular Analyst, Research Alchemist, and Reaction Mage. Together with the bosses, the palette, detailed linework, equipment, and silhouettes establish a coherent presentation. No obvious Prodigy logo or branded wording was visible in the supplied images. This was not an exhaustive character-by-character similarity search against Prodigy's or other publishers' catalogs.

Large transparent PNGs and duplicate distributed copies merit delivery optimization, but no measured mobile startup budget or bandwidth benchmark was collected. Do not mistake dramatic molecular ornament for a validated chemistry figure. Consider separate scientifically checked diagrams when exact atom identities, bonds, stereochemistry, or spectra matter.

## 5. Mandatory fixes for production upgrades

“Mandatory” below means a release gate recommended from this audit, not a claim that every row is a statutory obligation. Repair the confirmed security, state-integrity, and content defects before scaling traffic. More servers would reproduce the same defects faster.

### Gate A: Before a public pilot

| Required fix | Why it blocks release | Acceptance evidence | Status |
|---|---|---|---|
| Authorize every session mutation by authenticated owner | Known session IDs can otherwise be used against another user's state | A second user cannot cast, answer, advance, retry, switch tracks, or change another user's avatar | FIXED |
| Enforce legal transitions and consume each turn once | Live bosses can be completed; stale or concurrent answers can mutate the wrong state | Invalid advance rejected; duplicate/stale submissions produce no second mutation; test against a real database | TODO (Partially addressed: turn consumption & locking FIXED; boss defeat advance check TODO) |
| Restrict content administration and public asset serving | Players can select server folders or alter shared content cache; non-image files can be returned | Ordinary accounts cannot choose filesystem paths; asset IDs are allowlisted and JSON/config requests fail | TODO (Partially addressed: image path traversal and non-image serving FIXED; custom folder removal TODO) |
| Fix all seven foundational paths and validate the intended content before enabling them | Track labels currently misrepresent delivered content | Each track resolves to its intended manifest; no silent default substitution; placeholder records unavailable in player mode | TODO |
| Replace prompt-keyed explanations and damage with stable question identity | Correct grading can be paired with unrelated explanations | Every record retrieves its own explanation/damage through the active-turn snapshot | TODO |
| Remove ambiguous choices and review incomplete/repeated questions | Internal consistency does not establish a valid chemistry assessment | Duplicate correct choices removed; 7,300 detected placeholder-style records replaced or quarantined; expert-reviewed release set | TODO |
| Repair frontend submission, escaping, and transition handling | Repeated clicks, future markup inputs, and late timers can corrupt the interaction | In-flight guard, safe DOM text construction, cancelled transition timers, and stale-response handling verified | FIXED |
| Define consistent save/retry/reset behavior | Normal start/switch actions can erase partial battle state or share cursors across tracks | Documented state policy; track-qualified cursors/completions; reload, restart, and cross-track tests pass | FIXED |
| Eliminate unsafe production defaults | Default administrator credentials and inconsistent cookie configuration are avoidable exposure | Startup rejects default secrets/credentials for production; security settings verified in deployed configuration | TODO (Partially addressed: committed secret removed FIXED; seeded default admin passwords TODO) |

### Gate B: Before paid or broadly distributed release

| Required work | Acceptance evidence | Status |
|---|---|---|
| Content and asset rights record | Released assets/questions have source, author/generator, reference-input, license/permission, and publisher-rights records where applicable | TODO |
| Resolve intended commercial textbook reuse | Exact editions/licenses reviewed; any restricted reused material licensed, replaced, or excluded; alignment language avoids implied endorsement | TODO |
| Name/logo and relevant legal review | Intended markets and final branding assessed; unresolved material rights questions have a documented disposition | TODO |
| Complete asset packaging | All assets referenced by the released curriculum resolve to valid files; the two text-as-PNG aliases are fixed; generic fallback is monitored | TODO |
| Release-quality learning claims | Marketing distinguishes practice from proven mastery; curriculum coverage reflects validated items, not raw record volume | TODO |
| Accessibility and browser verification | Keyboard and modal focus, screen-reader flow, reduced motion, mobile layout, and target Safari/Chrome/Firefox behavior tested | FIXED |
| Observability and recovery | Structured error/transition logging without unnecessary answer-key exposure, alerts, backup retention, and a successful restore exercise | FIXED |
| Database migrations and deployment rollback | Versioned schema changes tested against the selected production database; rollback/recovery procedure rehearsed | FIXED |

### Gate C: Before claiming global scale or high availability

| Required work | Acceptance evidence | Status |
|---|---|---|
| Production database capacity and concurrency control | Representative simultaneous-user load, duplicate-turn races, query latency, and failure recovery tested; database choice justified by measurements | FIXED |
| Shared or deliberately stateless cross-worker services | Admin sessions, rate limits, and content versions behave consistently across workers; in-process state is not silently relied upon | TODO |
| Bounded, versioned content caching | Ordinary requests cannot grow arbitrary track entries; refresh/invalidation and multi-worker consistency are defined | FIXED |
| Asset delivery and payload budgets | Measured cold/warm load times and mobile transfer sizes; cache policy and compression/image formats chosen from actual measurements | TODO |
| High-availability operation | Health checks, worker replacement, database recovery, and application failover tested; more than one server alone is not treated as proof of availability | TODO |
| Service objectives and load thresholds | Agreed latency/error targets, realistic traffic distribution, and capacity limits documented before claiming support for a user count | TODO |

Redis, asynchronous database access, and a particular cloud vendor are implementation choices, not automatic requirements. Choose them where measured contention, cross-worker coordination, or recovery needs justify them. Database conversion alone does not protect question content, and the current DOM-image implementation does not require a nonexistent Phaser boss-texture eviction system.

### Consolidated engineering sequence

| Order | Change | Completion evidence | Status |
|---|---|---|---|
| 1 | Enforce ownership on every explicit-session operation | User B cannot read, cast, answer, advance, retry, or switch User A’s session | FIXED |
| 2 | Enforce valid transitions and atomic turn consumption | A live boss cannot be completed; duplicate submissions and stale turns do not mutate state | TODO (Partially addressed: atomic turn consumption FIXED; living boss advance TODO) |
| 3 | Separate public assets from private content | JSON/config requests through asset routes fail; active-track image resolves deterministically | FIXED |
| 4 | Replace prompt-keyed data with versioned question IDs | All 28,400 chapter records retain their own explanations; repeated stems remain independent | TODO |
| 5 | Restrict content folder overrides and validate track IDs | Ordinary players cannot overwrite shared track content or select server filesystem locations | TODO (Partially addressed: image serving restricted FIXED; custom folder removal TODO) |
| 6 | Repair per-track saves and transition cleanup | HP, cursor policy, pending state, completions, and admin actions follow one documented model | FIXED |
| 7 | Fail visibly on missing/malformed curriculum | All seven foundational paths resolve correctly; invalid/missing curricula fail visibly; duplicate choices and placeholder items blocked | TODO |
| 8 | Replace placeholder/repetitive content and separate mastery from damage | All required objectives assessed, including hard/application items that combat could otherwise skip | TODO |
| 9 | Reconcile catalog and documentation | One source defines spell damage/cooldowns; generated inventory reflects shipped content | FIXED |
| 10 | Finish content and asset provenance plus legal review | Source/license ledger, name/logo review, terms-history assessment, targeted patent review | TODO |
| 11 | Verify frontend and deployment | In-flight action guards, safe text rendering, transition cleanup, image alias fixes, accessibility, multi-tab races, and supported browsers verified | FIXED |

The architecture is usable as a foundation. Commercial readiness should wait for the confirmed state-integrity, authorization, content-exposure, and feedback defects to be resolved. The IP conclusion remains narrower: no specific Prodigy infringement was demonstrated, but there is not enough evidence for a clearance statement.

The previously requested static/ and data/ review is now complete at the source-analysis level. Remaining limits are the unsupplied referenced artwork, generation/source/license records, exact textbook comparisons, and a running deployment for integration, concurrency, accessibility, and performance verification. These limits do not prevent addressing the confirmed defects above.

## 6. Design strengths and appreciation

The audit found substantive strengths worth retaining. These observations concern implemented design and source structure; they are not claims of demonstrated learning effectiveness or commercial success.

| Strength | Evidence in this implementation | Why it is worth preserving |
|---|---|---|
| A recognizable chemistry-fantasy identity | Boss names, flasks, molecular ornaments, coordinated costumes, and varied silhouettes across inspected art | Gives the product a subject-specific identity and a basis for memorable concept associations |
| A clear action–question–consequence loop | Selecting a spell reveals a question; grading changes HP and produces feedback | Makes the immediate purpose of answering understandable and supports short practice sessions |
| A real damage/risk choice | Strong spells deal more damage and incur greater backfire on failure; cooldowns differ | Offers player agency that can be retained while separating combat success from mastery |
| Content separated from core combat code | Chapter JSONs, manifests, tracks, domain loader, and combat modules | Supports authoring and revision without rewriting the battle engine once validation and identity are repaired |
| Testable domain logic | Combat and grading functions can run independently; seven original domain tests passed in the isolated check | Makes important behavior easier to verify and refactor |
| Answer keys excluded from the pending-question payload | State formatting sends prompt and choices; feedback is returned after submission | Establishes the right basic delivery boundary, although asset-serving and collection risks still need attention |
| Persistent accounts and battle state | Database-backed sessions and per-track progress scaffolding | Provides a foundation for continuity across visits and later learning records |
| Meaningful subject breadth | Supplied advanced questions include synthesis, mechanisms, spectra, laboratory, and quantitative reasoning | The content direction can support more than vocabulary recognition after quality repair |
| Lightweight character presentation | DOM images with CSS states; procedurally generated audio | Avoids a complex sprite pipeline and external audio catalog for the present interaction |
| Some accessibility and feedback foundations | Native buttons, reduced-motion CSS, and text-based explanation presentation | Useful starting points for a complete accessibility pass |

The strongest existing contribution is the combination of a coherent chemistry identity, a straightforward battle loop, and a data-driven curriculum structure. The next improvement with the greatest educational value is accurate feedback tied to specific learning objectives. Adding more bosses or decorative spells before repairing content would provide less benefit.

## 7. Near-future applications

These are proposed uses for the current architecture after the release gates are addressed. “Near future” means achievable through bounded additions to the existing question/track system; it is not a promised delivery date. The learning benefits listed are hypotheses to evaluate.

| Proposed application | Reuse from Organic Battles | Addition required | Evidence of success |
|---|---|---|---|
| Instructor-assigned chapter practice | Tracks, chapter banks, bosses, account progress | Assignment IDs, validated objective maps, due dates, teacher reports | Students complete assigned objectives; reports agree with an attempt ledger |
| Exam-review and misconception mode | MCQ grading and explanations | Stable concept IDs, misconception-tagged distractors, missed-item queue, delayed review | Improvement on unseen questions and later retention tasks, not just repeated-item scores |
| Chemistry laboratory preparation | Existing laboratory reasoning content | Expert-authored pre-lab scenarios, apparatus images, explanatory feedback | Students can justify procedure choices in independent review tasks; game completion does not substitute for supervised training |
| Spectroscopy practice encounters | Spectroscopy tracks and image rendering | Scientifically checked spectrum figures, peak annotations, answer rationales | Learners interpret new spectra rather than memorize a text template |
| Reaction/reagent choice battles | Existing mechanism and synthesis content | Rendered substrates/products, reagent-choice options, concept-specific consequences | Performance transfers to unfamiliar substrates |
| Accessible low-bandwidth practice | Text-based controls and modular content | Lightweight/practice presentation, optimized assets, full keyboard flow | Target-device tasks succeed within a measured transfer and latency budget |
| Authoring and quality-review workspace | JSON schema, manifests, audit rules | Content editor, validation preview, reviewer approval/versioning | Invalid keys, duplicate choices, unresolved images, and placeholders cannot enter a published set |
| Other introductory science practice | Reusable battle engine and track boundaries | Independently authored biology, physics, or general-chemistry curricula and subject-specific visual language | Each subject is reviewed for instructional fit rather than simply replacing vocabulary labels |

A sensible sequence is authoring validation and attempt logging first, then instructor practice and targeted review, followed by one carefully scoped chemistry-specific interaction. This sequence creates reusable infrastructure and keeps the educational experiment small enough to assess.

## 8. Longer-term applications

These proposals require new interaction models, stronger evidence records, or institutional workflows. They should be treated as a separate roadmap rather than promises already supported by the current code.

| Proposed direction | How it extends the idea | Major new capability | Main design risk / evaluation need |
|---|---|---|---|
| Mechanism-construction encounters | Players draw electron movement or select reacting atoms to determine the attack | Validated molecular representation, interaction editor, chemistry-aware grading, partial-credit feedback | Equivalent valid mechanisms and notation must be handled; grading errors would directly misteach |
| Synthesis-planning campaigns | A sequence of reactions becomes a branching route to a target | Reaction constraints, route evaluation, intermediate structures, multiple valid solutions | A single scripted answer must not reject defensible alternate routes |
| Adaptive learning paths | Encounters respond to evidence of concept understanding over time | Durable attempt ledger, calibrated objectives/items, uncertainty-aware learner model | Adaptation must not trap learners in a weak inference or confuse combat loss with lack of knowledge |
| Cooperative scientific problem solving | Players contribute different steps to a shared mechanism or investigation | Shared sessions, synchronization, contribution records, collaboration design | One participant can otherwise complete the learning work for everyone |
| Virtual laboratory investigations | Boss encounters become experimental decisions and observations | Validated simulation, apparatus interactions, consequence model, accessibility alternatives | A simulation is not automatically an accurate representation of a real procedure |
| Teacher-guided explanatory assistant | Contextual hints address the actual misconception | Reviewed knowledge sources, bounded hint generation, traceable feedback, escalation to authored explanations | Unchecked generated explanations could worsen the current feedback-quality problem |
| Learning-platform integration | Practice results fit institutional coursework | Identity/roster integration, assignment synchronization, approved data governance and exports | Operational logs must not be misrepresented as validated learning evidence |
| Discipline-specific professional practice | The encounter structure supports expert-reviewed case exercises | Domain authoring, scenario validation, explanations, and appropriate assessment governance | High-stakes competence cannot be inferred from entertainment progression alone |
| Research platform for educational game design | The game tests how feedback, visuals, and combat choices affect learning | Versioned experiments, independent outcome measures, suitable consent/review processes | Engagement, completion, and learning gains must be measured separately |

The most distinctive longer-term direction is to make chemical reasoning determine the action itself: where electrons move, which reagent is appropriate, or which structure explains the evidence. That would create a closer relationship between the subject and the game rules than merely increasing the size of the question bank. It is a design opportunity, not proof of patentability, exclusivity, or superior learning outcomes.

## 9. Evidence, implementation corrections, and validation

### Evidence and limits

The original app.zip contains 74 files; its SHA-256 is `afbf2fb03b89a759e3bdb6a27af7fb6c8d7018d83b63fccb3f8b5f300e833cc8`. The later avatars.zip contains 637 files: 599 under data/, 30 under static/, and eight under avatars/. The review combines both uploads.

| Evidence now available | Scope examined |
|---|---|
| Python backend, HTML, five JavaScript files, CSS, SVG fallbacks | Combat, endpoints, persistence, frontend event handlers, rendering, image and audio lifecycle |
| 589 data JSON files | 568 chapter files, 20 manifests, one track configuration; all parse successfully |
| 28,400 chapter question records | Every record structurally scanned; original loader executed across every content folder and configured track |
| 40 PNG-named files | Byte deduplication and decoding checks; 27 distinct valid images visually inspected |
| Bestiaries, implementation prompt, source inventory | Compared intended teaching and provenance claims with runtime behavior |
| Owner's image-generation statement | Recorded as user-reported provenance; original generation transcripts/reference inputs were not supplied |

Twenty content sets are supplied: default (27 chapters/1,350 records), 12 advanced sets (324 chapters/16,200 records), and seven foundational sets (217 chapters/10,850 records). The 19 specialized tracks total 27,050 records; including default gives 20 selectable sets and 28,400 records. These are record counts, not counts of distinct concepts or independently authored problems.

Methods include static source inspection, complete structural/content-pattern scans, execution of original content loaders and domain functions, isolated original endpoint bodies with fixture repositories, and visual asset inspection. FastAPI, SQLAlchemy, and pytest were unavailable in the runtime; dependency installation did not complete. Seven existing domain-test functions were executed directly and passed. There was no full authenticated browser playthrough, full HTTP integration run, real database concurrency test, Safari/mobile compatibility test, or measured memory/performance benchmark. Frontend findings below are source-traced, not claims of a completed browser certification.

The original archive contains 64 test-function definitions. This does not substantiate the cookbook's claim of 198+ passing tests; parametrization or a larger omitted suite could alter the total. The newer upload supplies many fixtures that were previously absent, but does not establish that the entire suite passes.

### Corrections to the previous analysis

| Earlier cookbook-based account | Actual supplied implementation |
|---|---|
| Base damage 20 / 35 / 50 | Active combat catalog uses 20 / 30 / 45 |
| Cooldowns 0 / 1 / 2 turns | 1.5 / 5 / 10 seconds after answer resolution |
| Wrong answers cause 15 or 20% backfire plus boss damage | Full selected spell damage hits the player; no additional boss counterattack on that branch |
| Correct-answer counterattacks occur only in low-HP rage mode | Any surviving boss has a 50% counterattack chance |
| Counterattack damage scales by chapter | Route uses the domain default: random integer 10–25 |
| Question order unknown | Sequential within the selected bank, wrapping modulo bank size |
| Answer shuffling unknown | Backend and frontend preserve source option order; no runtime answer shuffle |
| Stable question IDs absent from sample schema | Actual sample has IDs and difficulty/topic/type labels, but loader discards these in runtime question tuples |
| Explanation display unknown | Frontend displays the correct answer after failure and offers an explanation; successful-answer explanations are not surfaced by the same flow |
| Boss health precedence unknown | Maximum health value among question records assigned to that boss |
| Boss strategy object governs runtime | Loader derives behavior from question rows and first appearance, not `boss_strategy` |
| Boss defeat establishes advancement eligibility | Advance endpoint does not verify defeat |
| Question keys likely remain private | Pending question payload excludes keys, but the image resolver can expose JSON files from searched folders |

Source references below use paths relative to the uploaded project and identify functions or approximate starting lines. The source tree was assembled locally from the two uploads; this report is the review deliverable, not a patched application.

### Validation record

Seven existing domain tests were executed directly with their original assertions:

- `test_grade_answer_exact_and_case_insensitive`: passed.
- `test_spell_catalog_integrity`: passed.
- `test_combat_turn_correct_answer_deterministic`: passed.
- `test_combat_turn_correct_with_counterattack_deterministic`: passed.
- `test_combat_turn_fizzle_backfires_on_player`: passed.
- `test_cooldown_management_pure_domain`: passed.
- `test_content_source_priority_resolution_pure`: passed.

Additional isolated checks reproduced: advance on a live boss; spell selection against another fixture user’s session; omission of answer keys from the pending-question payload; cursor advancement after failure; cursor retention and stale turn ID after retry; a pending question surviving advancement; same-track HP reset; switching after an intermediate defeated mini-boss; and non-image JSON selection by the asset resolver. These used fake repositories and local fixtures, not an HTTP deployment. The earlier incomplete-archive test returned three chapters/six questions, while the temporary sample returned one chapter/five bosses/fifty questions with nine explanation mismatches. Those were historical fixture results. With the new data upload, default and all 12 advanced track loaders resolve correctly; seven foundational loaders fall back to default (27 chapters/1,350 questions). Full-bank analysis counts 1,066 explanation mismatches, independently of the temp sample.

The expanded validation also parsed all 589 data JSONs, scanned all 28,400 chapter records, measured exact and normalized repetition, checked configured versus existing folder paths, inspected image-search resolution against 409 referenced names, checked all 40 PNG-named files, and visually reviewed 27 valid distinct images. Placeholder counts use the explicit answer patterns documented above. Chemistry examples were sampled; no claim is made that every answer is chemically validated or that any plagiarism detector established originality.

