# Organic Battles — High-Resolution Browser RPG Rebuild

You are a **senior Python web-game developer, Phaser game developer, UI/UX designer, and game architecture engineer**.

Rebuild the existing **Organic Battles** application from scratch as a polished, high-resolution browser-based educational RPG.

The existing repository is:

`https://github.com/DKxi/Organic-Battles`

Before writing code, inspect the complete repository, including:

- `organic_battles_codex_prompt.md`
- `README.md`
- `app.py`
- everything under `game/`
- everything under `data/`
- existing tests
- existing assets or asset directories

## CRITICAL SOURCE-OF-TRUTH RULE

The existing file:

`organic_battles_codex_prompt.md`

is the **functional and game-design source of truth**.

Preserve all gameplay requirements from that file unless this new prompt explicitly overrides a technical implementation requirement.

Do NOT simplify the game.

Do NOT convert it into a quiz website.

Do NOT eliminate bosses, chapters, spells, avatar customization, cooldowns, progression, animations, rewards, health, combat, or educational content.

The primary change is the **technology and visual quality**.

---

# 1. Primary Goal

The existing implementation uses Streamlit and therefore has relatively limited graphics, animation, avatar rendering, scene composition, and game-like presentation.

Rebuild Organic Battles so it feels much closer to a professionally developed **2D browser RPG / educational battle game**.

The finished game must have:

- high-resolution graphics
- detailed boss artwork
- high-resolution player avatars
- animated spell effects
- animated boss attacks
- particle effects
- environmental effects
- animated backgrounds where appropriate
- polished health bars
- polished spell cards
- cinematic boss introductions
- chapter maps
- damage indicators
- transitions
- victory effects
- defeat effects
- responsive browser rendering
- smooth animations
- professional typography
- coherent RPG visual design

The player must only need to open a URL in a modern browser.

There must be:

- no desktop installation
- no Python installation for players
- no Node installation for players
- no browser extension
- no game client installation
- no Unity
- no Godot
- no Electron
- no desktop Pygame window

Everything must run through a normal browser such as Chrome, Edge, Firefox, or Safari.

---

# 2. NEW REQUIRED TECHNOLOGY STACK

Replace Streamlit with the following architecture.

## Backend

Use:

**Python + FastAPI**

FastAPI is responsible for:

- application startup
- game-session APIs
- combat rules
- answer checking
- question generation
- boss progression
- chapter progression
- spell validation
- cooldown validation
- player HP
- boss HP
- rewards
- titles
- avatar validation/finalization
- persistence interfaces
- serving static web assets where appropriate

Keep important game logic in Python.

## Browser Game Engine

Use:

**Phaser 3**

Use Phaser for:

- scene rendering
- sprites
- WebGL rendering
- particles
- tweens
- spell animation
- boss animation
- avatar rendering
- damage numbers
- screen shake
- flashes
- projectiles
- aura effects
- environmental effects
- cinematic transitions
- chapter-map animation

Prefer WebGL with normal Phaser fallback behavior.

## Frontend Structure

Use:

- HTML5
- modern CSS
- plain JavaScript ES modules
- Phaser 3

Avoid introducing React, Vue, Angular, Svelte, Redux, or other frontend frameworks unless absolutely necessary.

**Do not create unnecessary frontend complexity.**

The purpose of JavaScript is primarily presentation and Phaser interaction.

Game rules should remain primarily understandable Python.

## Templates

FastAPI may use Jinja2 for the initial application shell if useful.

## Data

Continue using human-readable JSON files for chemistry vocabulary and other static game data where appropriate.

---

# 3. SIMPLICITY REQUIREMENT

This project may be reviewed by someone with intermediate Python knowledge.

Write code that is easy to understand and explain.

Prefer:

- Python functions
- small classes
- dataclasses where useful
- enums where useful
- dictionaries
- clear service modules
- clear API routes
- straightforward state machines
- type hints
- descriptive names
- comments explaining non-obvious behavior

Avoid:

- enterprise-style abstraction layers
- dependency-injection frameworks
- complex metaprogramming
- deep inheritance
- event-bus architectures unless truly necessary
- microservices
- GraphQL
- Kubernetes
- unnecessary databases
- excessive packages
- unnecessary build pipelines

This is a polished game, but the **programming architecture should remain understandable**.

---

# 4. SINGLE WEB APPLICATION

The entire game should deploy as one web application.

Target architecture:

```text
Browser
   │
   ├── HTML / CSS
   │
   ├── Phaser Game Client
   │
   └── High-resolution game assets
            │
            ▼
       FastAPI REST API
            │
            ▼
       Python Game Engine
       ├── combat
       ├── progression
       ├── questions
       ├── spells
       ├── bosses
       ├── avatar
       ├── rewards
       └── state
            │
            ▼
       JSON Vocabulary Data
```

Do NOT create a separate backend repository and frontend repository.

Keep deployment simple.

---

# 5. NO PLAYER-SIDE INSTALLATION

The deployed application must be completely playable by opening its URL.

Client-side JavaScript downloaded automatically by the browser is acceptable.

A player must NOT need to run:

```bash
npm install
pip install
python
uvicorn
```

Those commands are only for developers/deployment.

Prefer a deployment design that does not require a complicated Node production runtime.

If Phaser is obtained externally, use a stable version and structure the application so it can be self-hosted later.

Prefer serving all critical application assets from the application itself whenever practical.

---

# 6. PRESERVE THE COMPLETE EXISTING GAME

Preserve the existing Organic Battles gameplay.

The core loop remains:

```text
Choose Spell
    ↓
Receive Organic Chemistry Vocabulary Question
    ↓
Choose Answer
    ↓
Validate Answer
    ↓
Resolve Spell
    ↓
Animate Attack
    ↓
Apply Damage
    ↓
Boss Counterattack
    ↓
Continue Battle
```

Correct answer:

```text
Correct
→ Cast selected spell
→ Play full spell animation
→ Damage boss
→ Update boss HP
→ Display battle feedback
```

Incorrect answer:

```text
Incorrect
→ Spell fizzles/blanks
→ Play failed-spell effect
→ Cause zero damage
→ Reveal correct answer
→ Boss still receives counterattack opportunity
```

Bosses must retain the **50% hit / 50% miss counterattack mechanic**.

Do not change this probability.

---

# 7. PRESERVE ALL THREE CHAPTERS

## Chapter 1
### Foundations of Organic Chemistry

Boss order:

1. Hybridization Goblin
2. Functional Group Golem
3. Resonance Wraith
4. Resonance Dragon

Resonance Dragon:

**450 HP**

Preserve Chapter 1 chemistry topics from the original specification.

## Chapter 2
### Reaction Mechanisms

Boss order:

1. SN1 Knight
2. SN2 Assassin
3. E1 Sorcerer
4. Carbocation Shapeshifter
5. Mechanism Titan

Mechanism Titan:

**600 HP**

Preserve Chapter 2 chemistry topics from the original specification.

## Chapter 3
### Stereochemistry & Spectroscopy

Boss order:

1. Chiral Chimera
2. Enantiomer Elf
3. IR Specter
4. NMR Oracle
5. Stereochemistry Overlord

Stereochemistry Overlord:

**890 HP**

Preserve Chapter 3 chemistry topics from the original specification.

---

# 8. DO NOT CHANGE BOSS IDENTITIES

Keep every boss and its original chemistry/fantasy design concept.

### Hybridization Goblin

Maintain:

- green goblin creature
- orbitals floating around its head
- staff based on an sp³ tetrahedron

### Functional Group Golem

Maintain:

- stone giant
- glowing functional-group markings
- chemistry-integrated body design

### Resonance Wraith

Maintain:

- spectral appearance
- shifting resonance imagery
- glowing curved arrows

### Resonance Dragon

Maintain:

- massive dragon
- wings influenced by resonance structures
- shifting electron arrangements
- glowing curved-arrow breath

### SN1 Knight

Maintain carbocation-themed knight concept.

### SN2 Assassin

Maintain backside-attack themed rogue/assassin concept.

### E1 Sorcerer

Maintain elimination/carbocation sorcerer concept.

### Carbocation Shapeshifter

Maintain molecular-rearrangement shapeshifter concept.

### Mechanism Titan

Maintain:

- giant humanoid
- curved-arrow visual language
- reaction-coordinate imagery
- intermediate/transition-state transformations

### Chiral Chimera

Maintain mirrored/two-headed stereochemical design.

### Enantiomer Elf

Maintain left/right mirrored versions.

### IR Specter

Maintain spectral IR-wave visual design.

### NMR Oracle

Maintain magnetic-ring / chemical-shift design.

### Stereochemistry Overlord

Maintain:

- R/S split mask
- Newman-projection imagery
- IR/NMR energy attacks

Do NOT replace these with generic fantasy enemies.

---

# 9. HIGH-RESOLUTION ART DIRECTION

This version must substantially improve visual quality.

## Visual style

Use a coherent style:

**Organic Chemistry + Arcane Fantasy RPG + Modern Educational Game**

Aim for a polished illustrated-game appearance rather than photorealism.

Think:

- dramatic fantasy lighting
- luminous chemistry symbols
- molecular structures
- glass laboratory elements
- elemental energy
- glowing orbitals
- spectral chemistry diagrams
- dark atmospheric battle arenas
- highly readable colorful spell effects

Do not use emoji as primary artwork.

Emoji may only be used as a last-resort fallback.

---

# 10. ASSET QUALITY

Where raster artwork is used, design asset targets approximately as follows:

### Boss characters

Approximately:

`1024 × 1024`

with transparent backgrounds where appropriate.

### Main chapter/battle backgrounds

Approximately:

`1920 × 1080`

or larger source assets.

### Avatar components

Use high-resolution transparent assets capable of clean rendering on Retina/high-DPI displays.

### UI icons

Prefer:

- SVG
- vector shapes
- high-resolution transparent WebP/PNG

### Optimization

Use formats such as:

- WebP
- optimized PNG
- SVG

where appropriate.

Do not ship enormous uncompressed files unnecessarily.

Balance image quality and web performance.

---

# 11. ASSET CREATION REQUIREMENT

Do not simply create gray boxes that say:

`BOSS IMAGE HERE`

Create as much finished visual material as the coding environment allows.

Prefer, in order:

1. original finished graphical assets available through supported generation tools
2. original SVG/vector artwork
3. layered procedural Phaser artwork
4. sophisticated styled placeholders

If image-generation capability is available in the environment, use it to create the required original artwork.

If image generation is unavailable, create polished SVG/vector/procedural artwork instead.

**Never make emoji the intended final art direction.**

All assets must be original and safe to distribute with this game.

Do not copy commercial game artwork.

---

# 12. HIGH-DPI / RESPONSIVE RENDERING

The Phaser canvas must resize correctly.

Support common desktop and laptop screen sizes.

Also remain usable on tablets.

Use:

- responsive Phaser scaling
- aspect-ratio-aware scene composition
- high-DPI rendering
- device pixel ratio handling where reasonable
- maximum render-resolution cap where necessary for GPU performance

The game should look sharp on Retina/high-density displays without unnecessarily rendering at extreme resolutions.

---

# 13. BATTLE SCENE

The battle screen should be a genuine Phaser RPG scene rather than an HTML form.

Conceptually:

```text
┌──────────────────────────────────────────────────────────┐
│ Chapter / Area                           Settings        │
│                                                          │
│                   BOSS NAME                              │
│              Boss HP animated bar                        │
│                                                          │
│                    [BOSS]                                │
│                                                          │
│        projectile / spell / particle space              │
│                                                          │
│ [PLAYER]                                                 │
│ Player HP                                                │
│                                                          │
│ Fire Spark   Resonance Burst    Mechanism Storm         │
│                                                          │
│             Organic Chemistry Question                  │
│                                                          │
│          A        B        C        D                    │
│                                                          │
│ Battle feedback / compact battle log                    │
└──────────────────────────────────────────────────────────┘
```

Improve this significantly through professional visual design.

---

# 14. ANIMATED COMBAT

Animations should now be real browser animations rather than Streamlit pseudo-animation.

Use Phaser:

- tweens
- sprite animation
- particles
- masks
- blend modes
- alpha effects
- scale animation
- rotation
- motion paths
- camera shake
- camera flash
- hit stop where appropriate
- floating damage numbers
- animated health reduction
- projectile travel
- impact particles
- boss recoil
- player recoil

Keep animation durations short enough to maintain responsive gameplay.

---

# 15. PRESERVE ALL NINE SPELLS

## Basic

### Fire Spark

Visual:

- fast orange flame projectile
- sparks trailing behind
- warm light bloom
- fiery impact particles

### Acid Shot

Visual:

- glowing neon-green liquid projectile
- droplets
- bubbling/sizzling impact
- brief corrosive mist

### Carbon Punch

Visual:

- carbon-ring energy forms near player
- accelerates forward
- ring expands on impact
- hexagonal shockwave

## Medium

### Resonance Burst

Visual:

- resonance structures flash
- curved arrows rotate
- symbols combine into an energy orb
- orb strikes opponent
- zig-zag energy explosion

### Nucleophile Strike

Visual:

- electron lone-pair symbols appear
- spiral into a blue projectile
- projectile accelerates toward electrophilic target
- bright impact

### Chiral Slash

Visual:

- R and S symbols rotate
- mirrored energy blades form
- opposing slashes converge on boss

## Strong

### Mechanism Storm

Visual:

- curved arrows
- intermediates
- orbital particles
- vortex/tornado
- multiple impacts
- dramatic final explosion

### Stereochemical Rift

Visual:

- dimensional stereochemistry portal
- mirrored molecular fragments
- rotating wedge/dash geometry
- spiral beam
- distortion effect

### Spectral Obliteration

This should be one of the game's most impressive spells.

Visual:

- IR spectrum appears
- NMR waveform forms
- spectral energy combines
- screen energy builds
- enormous spectral beam/blast
- camera shake
- impact flash
- particle aftermath

Do not rename or replace these spells.

---

# 16. SPELL DAMAGE AND COOLDOWNS

Preserve the existing values exactly unless the source prompt contains a more authoritative value.

| Tier | Chapter 1 | Chapter 2 | Chapter 3 | Cooldown |
|---|---:|---:|---:|---:|
| Basic | 20 | 35 | 55 | 1–2 seconds |
| Medium | 30 | 50 | 80 | 5 seconds |
| Strong | 45 | 75 | 120 | 10 seconds |

Cooldowns must be genuine.

The backend should validate cooldown eligibility so changing browser JavaScript cannot trivially bypass them.

The frontend should display animated cooldown indicators.

---

# 17. PLAYER HEALTH

Default player HP:

**150**

Display an animated player HP bar.

HP cannot:

- exceed maximum
- fall below zero

When HP reaches zero:

- stop the battle
- play defeat animation
- display defeat screen/modal
- offer Retry
- preserve previously completed progression
- reset player and current boss appropriately

---

# 18. BOSS DAMAGE

Preserve:

| Boss Type | Damage |
|---|---:|
| Mini-Boss | 15 |
| Chapter 1 Major Boss | 20 |
| Chapter 2 Major Boss | 30 |
| Chapter 3 Major Boss | 45 |

Boss counterattack remains:

**50% hit / 50% miss**

If boss misses:

- animate player dodge or boss attack miss
- display MISS
- player receives no damage

If boss hits:

- animate boss attack
- animate player impact
- subtract correct HP
- update UI

---

# 19. TURN STATE MACHINE

Use an explicit state machine.

For example:

```text
SELECT_SPELL
    ↓
QUESTION_ACTIVE
    ↓
ANSWER_SUBMITTED
    ↓
SPELL_RESOLUTION
    ↓
BOSS_ATTACK
    ↓
CHECK_BATTLE_STATUS
    ↓
NEXT_TURN
```

Include additional animation states where useful without changing the game rules.

Prevent:

- duplicate answers
- duplicate spell damage
- multiple boss attacks
- double rewards
- question regeneration during active question
- repeated API requests from double-clicking
- cooldown bypasses

The **Python backend must remain authoritative for combat outcomes**.

---

# 20. API DESIGN

Keep APIs small and obvious.

Possible endpoints:

```text
POST /api/game/new
GET  /api/game/state

POST /api/avatar/preview
POST /api/avatar/finalize

POST /api/battle/start
POST /api/battle/select-spell
POST /api/battle/answer
POST /api/battle/next-turn
POST /api/battle/retry

GET  /api/progression
```

This is only a suggested structure.

Do not blindly create endpoints that are unnecessary.

Use Pydantic request/response models.

Return explicit JSON describing:

- state
- animation event
- player HP
- boss HP
- damage
- correctness
- correct answer when required
- boss attack result
- progression changes
- rewards
- next allowed action

The browser should render what the backend resolved.

---

# 21. AVATAR CREATOR

The player must create a permanent avatar before starting.

Preserve options including:

- female/male
- body type
- skin tone
- face shape
- hair style
- hair color
- eyes
- eyebrows
- clothing
- lab coat
- hoodie
- ORGO shirts
- goggles
- gloves
- backpacks
- cosmetic spell aura

Improve the avatar creator substantially.

Use layered graphical assets.

Example layers:

```text
body
skin
face
eyes
brows
hair-back
clothing
hair-front
accessory
aura
```

Update the avatar preview immediately when options change.

The avatar should look like a real game character rather than a collection of emoji.

---

# 22. PERMANENT AVATAR CONFIRMATION

Before accepting:

# FINALIZE YOUR AVATAR

Display clearly:

> Once you press ACCEPT, your avatar becomes permanent for your entire ORGO journey. You cannot change your appearance later. Choose wisely.

Require explicit ACCEPT.

After successful finalization:

- avatar appearance cannot be edited
- backend rejects later modification attempts
- frontend removes editing controls

---

# 23. CHAPTER MAP

Create a proper animated RPG progression map.

Show:

- chapter environment
- boss nodes
- completed nodes
- current boss
- locked bosses
- major boss
- chapter completion
- connecting path

For example:

```text
Hybridization Goblin
        ↓
Functional Group Golem
        ↓
Resonance Wraith
        ↓
Resonance Dragon
```

Visually distinguish:

- defeated
- available
- currently selected
- locked

Major bosses remain locked until all prerequisite mini-bosses are defeated.

Next chapters remain locked until the preceding major boss is defeated.

---

# 24. CHAPTER VISUAL IDENTITIES

Create distinct environments.

## Chapter 1

Organic chemistry foundations.

Potential visual vocabulary:

- molecular laboratory
- orbital energy
- bonds
- glowing functional groups
- blue / teal / amber chemistry magic

## Chapter 2

Reaction mechanisms.

Potential visual vocabulary:

- curved arrows
- unstable intermediates
- reaction energy
- carbocation glow
- kinetic laboratory machinery
- electric blue / violet / orange energy

## Chapter 3

Stereochemistry & spectroscopy.

Potential visual vocabulary:

- mirrored architecture
- spectral waves
- NMR rings
- IR beams
- R/S symbols
- deep violet / cyan / magenta spectral environment

Maintain one unified Organic Battles art direction.

---

# 25. QUESTIONS

Preserve vocabulary-based combat.

Support at minimum:

### Term → Definition

and

### Definition → Term

Use four-answer multiple choice.

Only one attempt per question.

Randomize answer positions.

Avoid immediate repetition.

Difficulty must increase naturally across chapters.

Keep chemistry wording educational rather than intentionally tricky.

Use concepts taught in:

**Klein Organic Chemistry, 5e Integrated Student Study Guide and Solutions Manual**

However:

**Do NOT copy textbook definitions or copyrighted passages verbatim.**

All definitions and question text must be originally written.

Preserve or improve the existing JSON vocabulary datasets.

---

# 26. QUESTION PRESENTATION

Questions should appear as part of the game scene.

Do not make them look like default HTML radio buttons.

Create polished answer panels/cards:

```text
┌──────────────┐  ┌──────────────┐
│      A       │  │      B       │
│   Answer     │  │   Answer     │
└──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐
│      C       │  │      D       │
│   Answer     │  │   Answer     │
└──────────────┘  └──────────────┘
```

Provide:

- hover state
- selected state
- correct state
- incorrect state
- keyboard accessibility where practical

---

# 27. REWARDS

Preserve titles:

- Resonance Slayer
- Mechanism Master
- Spectral Champion

Preserve cosmetic aura rewards.

Major boss victories should trigger a substantial reward sequence:

- victory animation
- particles
- unlocked item animation
- title reveal
- chapter completion banner

---

# 28. FINAL VICTORY

After defeating the **Stereochemistry Overlord**, create a cinematic completion scene.

Display:

- final avatar
- all chapters completed
- defeated bosses
- titles earned
- cosmetics unlocked
- completion statistics if useful

Prominently show:

# SPECTRAL CHAMPION

This should feel like completing an actual game.

---

# 29. AUDIO

Audio is optional but strongly preferred if appropriate original/publicly distributable assets can be included.

Possible sounds:

- UI click
- spell cast
- spell fizzle
- boss hit
- player hit
- boss miss
- victory
- defeat
- reward unlock
- chapter introduction

Provide:

- mute button
- volume control

Do not autoplay loud music before browser interaction.

The game must remain completely playable without audio.

---

# 30. SAVE / PERSISTENCE

A browser refresh should not unnecessarily erase an active game.

Implement a straightforward persistence strategy.

A reasonable initial approach is:

- server game session
- session identifier
- browser persistence/local storage for appropriate save metadata
- backend validation

Keep persistence behind a simple interface so a future SQLite/PostgreSQL/account system can be introduced without rewriting combat.

Do not introduce user registration for this version unless required.

---

# 31. SECURITY / AUTHORITATIVE GAME RULES

Do not trust client-supplied:

- damage
- boss HP
- player HP
- correct-answer status
- unlocked bosses
- unlocked chapters
- cooldown completion
- rewards

The backend computes these values.

The browser sends player actions.

The Python game engine returns results.

This keeps the architecture clean and prevents accidental state corruption.

---

# 32. PROPOSED REPOSITORY STRUCTURE

Use a clean structure approximately like:

```text
organic-battles/
│
├── app.py
├── requirements.txt
├── README.md
│
├── game/
│   ├── __init__.py
│   ├── models.py
│   ├── state.py
│   ├── combat.py
│   ├── progression.py
│   ├── questions.py
│   ├── avatar.py
│   ├── spells.py
│   ├── bosses.py
│   └── rewards.py
│
├── api/
│   ├── __init__.py
│   ├── game_routes.py
│   ├── battle_routes.py
│   └── avatar_routes.py
│
├── data/
│   ├── chapter1_vocab.json
│   ├── chapter2_vocab.json
│   └── chapter3_vocab.json
│
├── templates/
│   └── index.html
│
├── static/
│   ├── css/
│   │   └── game.css
│   │
│   ├── js/
│   │   ├── main.js
│   │   ├── api.js
│   │   ├── game/
│   │   │   ├── config.js
│   │   │   ├── state.js
│   │   │   └── animations.js
│   │   │
│   │   └── scenes/
│   │       ├── BootScene.js
│   │       ├── TitleScene.js
│   │       ├── AvatarScene.js
│   │       ├── MapScene.js
│   │       ├── BossIntroScene.js
│   │       ├── BattleScene.js
│   │       ├── RewardScene.js
│   │       ├── DefeatScene.js
│   │       └── VictoryScene.js
│   │
│   └── assets/
│       ├── avatars/
│       ├── bosses/
│       ├── spells/
│       ├── backgrounds/
│       ├── particles/
│       ├── ui/
│       └── audio/
│
├── tests/
│   ├── test_combat.py
│   ├── test_progression.py
│   ├── test_questions.py
│   ├── test_avatar.py
│   └── test_api.py
│
└── Dockerfile
```

Adjust where technically justified.

Do not turn every file into a class.

---

# 33. FASTAPI APPLICATION

Keep `app.py` easy to understand.

Conceptually it should:

1. create FastAPI app
2. install middleware if needed
3. register API routes
4. mount static files
5. render/serve the game page
6. run through Uvicorn

Avoid large business logic in `app.py`.

---

# 34. GRAPHICS PERFORMANCE

Do not sacrifice browser performance just to use large images.

Implement:

- asset preloading
- texture reuse
- lazy loading for later chapters where useful
- optimized WebP/PNG
- responsive asset scaling
- controlled particle counts
- cleanup of destroyed effects
- limited simultaneous effects
- sensible high-DPI limits

Target smooth gameplay on a normal modern laptop.

Aim for **60 FPS when hardware permits**.

Animations should gracefully degrade if needed.

---

# 35. ACCESSIBILITY / USABILITY

Include sensible accessibility features:

- readable font sizes
- sufficient contrast
- keyboard-accessible answers where practical
- visible selected states
- reduced-motion support where practical
- mute control
- clear cooldown state
- clear locked/unlocked state

Do not compromise the RPG design to make it look like a business application.

---

# 36. ERROR HANDLING

The application must not crash because:

- artwork is missing
- audio is missing
- question JSON temporarily fails
- player double-clicks
- network request is repeated
- HP reaches exactly zero
- boss HP reaches exactly zero
- cooldown has not expired
- session data is missing
- local browser save is malformed
- question pool runs low
- WebGL is unavailable

Provide Canvas/fallback behavior where Phaser supports it.

Missing cosmetic assets must not prevent gameplay.

---

# 37. TESTING

The Python game engine must be testable independently from Phaser.

At minimum test:

- correct answer applies correct damage
- incorrect answer applies zero damage
- 50/50 boss attack resolution logic
- boss damage values
- player HP boundaries
- boss HP boundaries
- spell cooldown behavior
- mini-boss progression
- major-boss locking
- chapter unlocking
- avatar permanence
- rewards
- defeat/retry
- final victory
- question randomization rules
- malformed actions
- duplicate turn protection

Also create basic FastAPI route/API tests.

---

# 38. DEVELOPMENT QUALITY

Before completion run:

```bash
pytest
```

and appropriate application checks.

Remove:

- TODOs for mandatory functionality
- debugging prints
- dead files
- unused imports
- abandoned Streamlit code
- placeholder navigation
- fake buttons
- nonfunctional menu items

Do not claim completion while required features are unfinished.

---

# 39. README

Rewrite `README.md` for the new architecture.

Explain:

- what Organic Battles is
- educational purpose
- screenshots
- technology stack
- architecture
- repository layout
- local developer setup
- how to run FastAPI
- how Phaser is loaded
- tests
- deployment
- game controls
- chapters
- bosses
- spell system
- avatar system
- content/copyright note

Clearly state that chemistry definitions/questions are originally written and do not reproduce the textbook verbatim.

---

# 40. DEPLOYMENT

The finished application must be deployable to a standard Python web-hosting environment.

Provide at least:

- normal Python startup instructions
- `requirements.txt`
- production Uvicorn command
- Dockerfile

A typical production command may resemble:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Do not require Streamlit Cloud.

Do not require client software.

The final deployed experience must simply be:

```text
Open URL
→ Game loads
→ Play Organic Battles
```

---

# 41. ORIGINAL STREAMLIT REQUIREMENTS THAT ARE NOW OVERRIDDEN

The following requirements from the old prompt are intentionally removed:

- Streamlit requirement
- Streamlit Cloud requirement
- `st.session_state`
- `st.markdown()` game rendering
- Streamlit columns
- GIF-only animation limitations
- `st.empty()` pseudo-animation
- Streamlit rerun management
- requirement that all rendering occur server-side
- requirement prohibiting a browser game framework
- `streamlit run app.py`
- `.streamlit/config.toml`

Replace those concerns using FastAPI + Phaser architecture.

All **gameplay requirements associated with them remain intact**.

For example, preventing duplicate damage remains required even though the implementation technique changes.

---

# 42. DO NOT CHANGE THESE THINGS

Do NOT change:

- Organic Battles name
- Organic Chemistry + Fantasy RPG theme
- three chapters
- chapter order
- boss names
- boss order
- major boss HP
- nine spell names
- spell concepts
- spell tier structure
- damage progression
- cooldown concept
- player HP concept
- boss damage rules
- 50/50 counterattack
- vocabulary-driven combat
- one-attempt questions
- avatar permanence
- rewards
- titles
- progression locking
- defeat/retry
- final boss
- SPECTRAL CHAMPION ending

The objective is to **upgrade the presentation and technology without changing the game design**.

---

# 43. BUILD ORDER

Work systematically.

## Phase 1 — Repository Analysis

Read the existing repository.

Create a checklist mapping every requirement from `organic_battles_codex_prompt.md` to the new implementation.

Do this before deleting Streamlit code.

## Phase 2 — Python Game Engine

Implement/refactor:

- models
- game state
- bosses
- spells
- questions
- combat
- progression
- rewards
- avatar

Run tests.

## Phase 3 — FastAPI

Implement game/session APIs.

Run API tests.

## Phase 4 — Phaser Foundation

Implement:

- BootScene
- asset loader
- game configuration
- API adapter
- responsive scaling
- shared animation helpers

## Phase 5 — Main Game Scenes

Implement:

- title
- avatar creator
- map
- boss intro
- battle
- reward
- defeat
- chapter completion
- final victory

## Phase 6 — Art

Create/integrate:

- avatar art
- 14 boss designs
- three chapter environments
- spell graphics
- particles
- UI elements
- reward graphics

## Phase 7 — Animation

Implement every required spell animation and boss feedback sequence.

## Phase 8 — Polish

Add:

- transitions
- particles
- responsive layout
- high-DPI support
- loading screen
- battle log
- accessibility
- audio if available
- visual consistency

## Phase 9 — Full Game Validation

Play through from:

```text
NEW GAME
```

through:

```text
SPECTRAL CHAMPION
```

Fix issues encountered.

---

# 44. ACCEPTANCE TEST

Do not consider the rebuild complete until a player can:

1. Open the game URL.
2. See a polished animated title screen.
3. Create a high-quality graphical avatar.
4. Preview avatar changes.
5. Permanently finalize the avatar.
6. Enter Chapter 1.
7. Navigate an RPG-style chapter map.
8. Enter the Hybridization Goblin battle.
9. Choose a spell.
10. Receive a chemistry vocabulary question.
11. Answer it.
12. See a successful spell animation after a correct answer.
13. See a fizzle animation after an incorrect answer.
14. See damage applied correctly.
15. See boss counterattack animation.
16. Experience actual 50% hit/miss mechanics.
17. Lose HP when hit.
18. Lose a battle.
19. Retry that boss.
20. Preserve completed progression.
21. Defeat every Chapter 1 boss.
22. Unlock the Resonance Dragon.
23. Receive Chapter 1 rewards.
24. Unlock Chapter 2.
25. Complete Chapter 2.
26. Unlock Chapter 3.
27. Complete Chapter 3.
28. Defeat the Stereochemistry Overlord.
29. Reach the final cinematic victory scene.
30. Receive the SPECTRAL CHAMPION title.
31. Refresh/reload without obvious state corruption.
32. Play entirely through a browser without installing anything.

---

# 45. VISUAL ACCEPTANCE STANDARD

The application is NOT visually complete if:

- bosses are mostly emoji
- spells are mostly text
- battle animation is just messages changing
- avatar is only an emoji
- chapter map is just buttons
- battle screen looks like a web form
- default browser controls dominate the interface
- graphics are visibly low-resolution
- major spells have no meaningful animation
- bosses have no visual identity
- victory consists only of text

The game should visually communicate:

> **This is an actual educational fantasy RPG that happens to teach Organic Chemistry.**

It should NOT communicate:

> **This is a chemistry quiz wrapped in a dashboard.**

---

# 46. FINAL CODE REVIEW

Before finishing, inspect the repository as though it is being submitted to a student game-development competition.

Verify:

- complete gameplay
- all 14 bosses
- all 9 spells
- all 3 chapters
- accurate damage
- accurate HP
- real cooldowns
- correct 50/50 boss counterattacks
- avatar permanence
- question correctness
- original chemistry wording
- progression locking
- rewards
- defeat/retry
- high-resolution assets
- responsive Phaser rendering
- smooth animations
- asset fallback behavior
- FastAPI security/state validation
- tests
- deployment
- documentation
- no unfinished mandatory functionality

Fix problems rather than documenting them as future work.

---

# 47. FINAL DELIVERABLE

**Do not merely explain how you would build the game.**

Modify/create the repository and produce the complete working implementation.

Generate:

- Python source
- FastAPI application
- Phaser client
- HTML
- CSS
- JavaScript
- JSON data
- graphical assets
- asset manifests
- tests
- README
- requirements
- Dockerfile
- deployment configuration if useful

At completion, provide:

1. concise architecture summary
2. final repository tree
3. commands used to run/test
4. test results
5. deployment instructions
6. brief inventory of visual assets created
7. confirmation that every original functional requirement was preserved
8. any genuine limitations that could not be resolved

Do not stop at architecture.

Do not stop at a prototype.

Do not stop after creating the first chapter.

**Build the complete Organic Battles game from beginning to final SPECTRAL CHAMPION victory.**
