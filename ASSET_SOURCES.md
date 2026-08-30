# Organic Battles — Asset Sources & Catalog

**Organic Battles** features a custom visual aesthetic combining arcane fantasy RPG themes with organic chemistry iconography. All runtime visual assets (player avatars, boss illustrations, and battle arenas) are stored locally in `static/assets/` and served as high-resolution transparent RGBA PNGs and vector SVGs with zero third-party hotlinking dependencies.

---

## 1. Battle Arena & Environments

| Asset | Path | File Size | Dimensions / Format | Usage & Description |
|---|---|---|---|---|
| **Battle Arena** | [`static/assets/battle-arena.png`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/assets/battle-arena.png) | 2.22 MB | High-Res RGBA PNG | The central alchemical laboratory arena featuring bubbling flask apparatus, arcane glassware, crystalline reagents, and glowing molecular circle glyphs. Rendered dynamically behind the combat stage with CSS radial lighting. |

---

## 2. Playable Alchemist Avatars (`static/assets/avatars/`)

The avatar engine in [`static/js/avatars.js`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/js/avatars.js) renders high-detail character sprites layered with CSS customization filters, gear accessories, and combat state animations (`idle`, `cast`, `hit`, `defeated`, `victory`).

| Companion Avatar | File | Size | Character Role & Arcane Theme |
|---|---|---|---|
| **Organic Apprentice** | `organic-apprentice.png` | 463 KB | Energetic novice chemist wielding reaction flasks and reagent satchels. |
| **Reaction Mage** | `reaction-mage.png` | 661 KB | Arcane sorcerer channeling purple reaction flame and mechanism energy. |
| **Player Carbon Trailblazer** | `player-carbon-trailblazer.png` | 2.08 MB | Adventuring alchemist carrying field flasks, reagents, and carbon apparatus. |
| **Player Catalysis Adept** | `player-catalysis-adept.png` | 2.42 MB | Arcane scholar wielding dual elemental energy orbs and catalytic robes. |
| **Player Compound Artificer** | `player-compound-artificer.png` | 2.47 MB | Master artificer holding floating crystalline molecules and arcane alembics. |
| **Player Molecular Analyst** | `player-molecular-analyst.png` | 2.41 MB | Analytical chemist holding an arcane tome and floating orbital spheres. |
| **Player Research Alchemist** | `player-research-alchemist.png` | 2.38 MB | Senior scholar wielding an alchemical lantern staff and field specimen case. |

### Avatar Customization Matrix
The companion avatar system supports real-time customization tokens defined in [`static/js/avatars.js`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/js/avatars.js):
- **Skin Tones**: `light`, `light-medium`, `medium`, `medium-deep`, `deep`
- **Hair Styles & Colors**: `messy-short`, `side-swept`, `spiky`, `curly`, `medium-layered` (in `black`, `dark-green`, `brown`, `dark-purple`, `blue-black`)
- **Apparel & Coats**: `classic-white`, `green-trim`, `blue-trim`, `advanced-chemist`, `reaction-coat`
- **Elemental Flasks**: `green-reaction`, `blue-catalyst`, `purple-reagent`, `orange-energy`
- **Accessories**: `benzene-pin` (⌬), `periodic-table-badge` (C), `molecule-brooch` (⌘), `reaction-arrow-pin` (↗), `chemist-gloves` (✦), `wrist-device` (◈)
- **Aura Accents**: `emerald`, `azure`, `violet`, `amber`, `crimson`

---

## 3. Boss Artwork Catalog (`static/assets/bosses/`)

The repository includes **76 custom boss illustrations** and **1 vector fallback placeholder** representing organic chemistry concepts across functional groups, stereochemistry, reaction mechanisms, spectroscopy, and synthesis:

### 3.1 Chapter 1: Foundations, Electrons, Bonds & Properties
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Orbital Ogre** | `orbital-ogre.png` | 3.10 MB | Heavy brute wielding spiked clubs imbued with atomic electron orbitals. |
| **Bondbreaker Brute** | `bondbreaker-brute.png` | 3.10 MB | Armored titan cleaving sigma and pi covalent bonds with brute force. |
| **Hybridization Goblin** | `hybridization-goblin.png` | 2.79 MB | Cunning goblin spinning $sp^3$, $sp^2$, and $sp$ hybrid orbital staffs. |
| **Polarity Phantom** | `polarity-phantom.png` | 2.76 MB | Spectral apparition shifting dipole moments and electronegativity charges. |
| **Molecular Property Titan** | `molecular-property-titan.png` | 3.09 MB | Colossus commanding intermolecular forces, boiling points, and solubility. |

### 3.2 Chapter 2: Molecular Structure & Representations
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Lewis Rune Knight** | `lewis-rune-knight.png` | 2.71 MB | Knight brandishing shields etched with valence electron octet runes. |
| **Skeletal Sketcher** | `skeletal-sketcher.png` | 2.68 MB | Rogue wielding curved bone blades in zig-zag carbon line angles. |
| **Conformation Mimic** | `conformation-mimic.png` | 2.73 MB | Shapeshifting mimic twisting along carbon–carbon single bond rotations. |
| **Functional Group Golem** | `functional-group-golem.png` | 3.09 MB | Stone behemoth embedded with reactive functional group cores. |
| **Molecular Mapmaster** | `molecular-mapmaster.png` | 2.73 MB | Arcane navigator charting constitutional isomers and molecular graphs. |

### 3.3 Chapter 3: Acids & Bases in Organic Chemistry
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Proton Prowler** | `proton-prowler.png` | 2.57 MB | Swift feline beast stalking Brønsted–Lowry hydronium transfers. |
| **pKa Warlock** | `pka-warlock.png` | 2.66 MB | Arcane sorcerer wielding logarithmic acidity scales and acid-base equilibria. |
| **Conjugate Basilisk** | `conjugate-basilisk.png` | 3.40 MB | Armored serpent spitting conjugate acid and base reagents. |
| **Resonance Wraith** | `resonance-wraith.png` | 2.83 MB | Ethereal specter stabilizing formal charges across delocalized $\pi$-systems. |
| **Equilibrium Lich** | `equilibrium-lich.png` | 3.12 MB | Undead warlock manipulating Le Chatelier equilibrium constants. |

### 3.4 Chapter 4: Alkanes & Cycloalkanes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alkane Marauder** | `alkane-marauder.png` | 2.82 MB | Saturated hydrocarbon raider navigating petroleum and alkane chains. |
| **Newman Sentinel** | `newman-sentinel.png` | 2.57 MB | Armored guardian rotating staggered and eclipsed Newman projections. |
| **Conformer Imp** | `conformer-imp.png` | 2.57 MB | Trickster demon twisting chair, boat, and twist-boat cyclohexane forms. |
| **Cycloalkane Crusher** | `cycloalkane-crusher.png` | 3.01 MB | Heavy golem flexing Bayer angle strain and torsional resistance. |
| **Ring Strain Behemoth** | `ring-strain-behemoth.png` | 3.35 MB | Colossal titan releasing extreme ring strain from 3- and 4-membered rings. |

### 3.5 Chapter 5: Stereochemistry & Chirality
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Chiral Chimera** | `chiral-chimera.png` | 3.26 MB | Two-headed beast split across asymmetric stereocenters. |
| **Enantiomer Elf** | `enantiomer-elf.png` | 2.73 MB | Mirrored archer whose left and right non-superimposable forms strike as one. |
| **Diastereomer Duelist** | `diastereomer-duelist.png` | 2.57 MB | Fencer mastering non-mirror stereoisomer geometries and meso compounds. |
| **Conformation Seer** | `conformation-seer.png` | 3.19 MB | Oracle discerning $(R)/(S)$ Cahn–Ingold–Prelog priority configurations. |
| **Stereochemistry Overlord** | `stereochemistry-overlord.png` | 2.95 MB | Supreme master of polarimetry and optical activity rotation. |

### 3.6 Chapter 6: Chemical Reactivity & Reaction Mechanisms
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Curved Arrow Trickster** | `curved-arrow-trickster.png` | 2.58 MB | Arcane rogue bending electron pair movement arrows across reaction coordinates. |
| **Nucleophile Raider** | `nucleophile-raider.png` | 2.67 MB | Electron-rich warrior attacking electrophilic centers. |
| **Electrophile Warden** | `electrophile-warden.png` | 2.94 MB | Electron-deficient guardian seeking lone pairs. |
| **Transition State Wraith** | `transition-state-wraith.png` | 2.85 MB | Spectral phantom haunting the energy peak ($\Delta G^\ddagger$) of activation barriers. |
| **Mechanism Titan** | `mechanism-titan.png` | 2.93 MB | Multi-step colossus of reaction coordinate diagrams and rate-determining steps. |

### 3.7 Chapter 7: Alkyl Halides & Nucleophilic Substitution (SN1/SN2)
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **SN2 Assassin** | `sn2-assassin.png` | 2.49 MB | Swift ninja executing one-step backside attacks with Walden inversion. |
| **Carbocation Shapeshifter** | `carbocation-shapeshifter.png` | 2.95 MB | Planar intermediate rearranging hydride and methyl shifts for stability. |
| **SN1 Knight** | `sn1-knight.png` | 2.98 MB | Two-step warrior leaving behind leaving groups before nucleophilic trapping. |
| **E2 Executioner** | `e2-executioner.png` | 3.03 MB | Heavy berserker executing anti-periplanar $\beta$-eliminations. |
| **E1 Sorcerer** | `e1-sorcerer.png` | 2.99 MB | Sorcerer casting Zaitsev alkene eliminations via carbocation intermediates. |

### 3.8 Chapter 8: Alkenes — Structure & Addition Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alkene Charger** | `alkene-charger.png` | 2.74 MB | Armored beast charging with reactive carbon–carbon double bonds ($\pi$-bonds). |
| **Markovnikov Marauder** | `markovnikov-marauder.png` | 2.83 MB | Warrior directing electrophilic additions to the more substituted carbon. |
| **Halohydrin Hydra** | `halohydrin-hydra.png` | 3.14 MB | Multi-headed hydra spitting halogen and water addition reagents. |
| **Hydroboration Ranger** | `hydroboration-ranger.png` | 2.76 MB | Archer executing anti-Markovnikov syn-additions with borane complexes. |
| **Addition Reaction Titan** | `addition-reaction-titan.png` | 3.29 MB | Master titan of catalytic hydrogenation and oxidative alkene cleavages. |

### 3.9 Chapter 9: Alkynes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Acetylide Archer** | `acetylide-archer.png` | 2.48 MB | De-protonated terminal alkyne archer seeking alkyl halide targets. |
| **Hydration Harpy** | `hydration-harpy.png` | 3.06 MB | Winged beast tautomerizing enols into carbonyls via oxymercuration. |
| **Halogenation Hunter** | `halogenation-hunter.png` | 2.50 MB | Hunter adding dual equivalents of halogens across triple bonds. |
| **Reduction Reaver** | `reduction-reaver.png` | 2.88 MB | Warrior wielding Lindlar catalysts (cis) and sodium in ammonia (trans). |
| **Triple Bond Basilisk** | `triple-bond-basilisk.png` | 3.26 MB | Ancient basilisk fortified with sp-hybridized cylindrical electron density. |

### 3.10 Chapter 10: Radical Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Initiation Imp** | `initiation-imp.png` | 2.66 MB | Imp cleaving peroxides with UV light into unpaired radical electrons. |
| **Propagation Phantom** | `propagation-phantom.png` | 2.72 MB | Self-sustaining chain reaction phantom abstracting hydrogen atoms. |
| **Radical Reaper** | `radical-reaper.png` | 3.10 MB | Scythe-wielding reaper targeting allylic and benzylic $3^\circ$ positions. |
| **Bromination Beast** | `reagent-alchemist.png` | 2.69 MB | Highly selective halogenation beast targeting weakest C–H bonds. |
| **Chain Reaction Colossus** | `chain-reaction-colossus.png` | 3.11 MB | Colossal entity driving radical polymerization and termination cascades. |

### 3.11 Chapters 11–15: Synthesis, Spectroscopy & Functional Groups
| Boss | Asset | Size | Topic / Mechanism |
|---|---|---|---|
| **Synthesis Grandmaster** | `synthesis-grandmaster.png` | 3.16 MB | Multi-step organic synthesis architect. |
| **Retrosynthesis Rogue** | `retrosynthesis-rogue.png` | 2.64 MB | Disconnecting target molecules backwards into synthetic synthons. |
| **Transformation Tactician** | `transformation-tactician.png` | 3.00 MB | Functional group interconversion strategist. |
| **Synthetic Pathweaver** | `synthetic-pathweaver.png` | 2.69 MB | Routing stereoselective pathways and protecting groups. |
| **Alcohol Alchemist** | `alcohol-alchemist.png` | 2.78 MB | Hydroxyl group chemistry, Grignard additions, and tosylate activations. |
| **Oxidation Ogre** | `oxidation-ogre.png` | 2.97 MB | Wielding Jones reagents, PCC, and DMP to oxidize alcohols. |
| **Dehydration Djinn** | `dehydration-djinn.png` | 3.16 MB | Eliminating water molecules with acid catalysts to yield alkenes. |
| **Phenol Phantom** | `phenol-phantom.png` | 2.72 MB | Acidic aromatic hydroxyl phantom with resonance stabilization. |
| **Hydroxyl Golem** | `hydroxyl-golem.png` | 3.30 MB | Stone golem bonded with primary, secondary, and tertiary alcohols. |
| **Ether Enchanter** | `ether-enchanter.png` | 2.91 MB | Williamson ether synthesis caster and acid cleavage sorcerer. |
| **Epoxide Ambusher** | `epoxide-ambusher.png` | 2.67 MB | Strained 3-membered oxirane ring ambusher opening via acid/base attack. |
| **Ring Opening Rogue** | `ring-opening-rogue.png` | 2.85 MB | Regioselective attacker targeting substituted epoxide carbons. |
| **Thiol Trickster** | `thiol-trickster.png` | 2.73 MB | Sulfur-analog trickster forming disulfide bridges and mercaptans. |
| **Sulfide Sentinel** | `sulfide-sentinel.png` | 2.93 MB | Guardian of thioethers, sulfoxides, and sulfone oxidation states. |
| **IR Specter** | `ir-specter.png` | 2.80 MB | Infrared radiation specter measuring carbonyl ($1715\text{ cm}^{-1}$) and OH ($3300\text{ cm}^{-1}$) stretches. |
| **Vibration Wraith** | `vibration-wraith.png` | 3.09 MB | Symmetric and asymmetric bond bending/stretching wraith. |
| **Fingerprint Fiend** | `fingerprint-fiend.png` | 2.98 MB | Fiend identifying diagnostic peaks below $1500\text{ cm}^{-1}$. |
| **Fragmentation Phantom** | `fragmentation-phantom.png` | 2.58 MB | Mass spectrometry phantom cleaving molecular ions ($M^+$) into base peaks. |
| **Mass Spec Behemoth** | `mass-spec-behemoth.png` | 3.30 MB | Heavy behemoth analyzing mass-to-charge ($m/z$) ratios and isotope patterns. |
| **NMR Oracle** | `nmr-oracle.png` | 2.89 MB | Nuclear magnetic resonance seer charting proton and carbon chemical shifts. |
| **Chemical Shift Seer** | `chemical-shift-seer.png` | 3.02 MB | Seer measuring ppm deshielding effects near electronegative atoms. |
| **Integration Illusionist** | `integration-illusionist.png` | 2.89 MB | Measuring peak areas corresponding to relative proton counts. |
| **Splitting Sorcerer** | `splitting-sorcerer.png` | 3.15 MB | Calculating $N+1$ multiplicity (singlets, doublets, triplets, quartets). |
| **Coupling Conjurer** | `coupling-conjurer.png` | 2.62 MB | Measuring $J$-coupling constants across adjacent spin systems. |

### 3.12 Universal Fallback Asset
| Asset | Path | Size | Description |
|---|---|---|---|
| **Boss Placeholder** | [`static/assets/bosses/boss-placeholder.svg`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/assets/bosses/boss-placeholder.svg) | 349 B | Clean, lightweight SVG vector badge displaying an arcane alchemical glyph. Automatically rendered if an unmapped asset is requested. |

---

## 4. Processing, Optimization & Quality Standards

1. **Contiguous Alpha Channels**: All companion and boss PNGs have been cleaned to remove extraneous border artifacts and cropped tightly to the character bounding box with smooth transparency.
2. **Asynchronous & Lazy Loading**: HTML5 `<img loading="lazy" decoding="async">` attributes ensure zero main-thread blockage during high-speed turn interactions.
3. **Asset Resolution Safety**: Both backend (`app/domain/content/loader.py`) and frontend (`static/js/avatars.js`) feature resilient fallback handlers that catch missing asset errors and substitute `boss-placeholder.svg` without interrupting gameplay.
