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

## 3. Boss Artwork Catalog (`data/tracks/advanced/bosses/` & `data/tracks/foundational/bosses/`)

All boss illustrations are stored as high-resolution transparent RGBA PNGs across the curriculum asset directories:
- **Advanced Mechanistic Mastery**: `data/tracks/advanced/bosses/` (135 progressive chapter bosses)
- **Foundational Curriculum**: `data/tracks/foundational/bosses/` & `data/tracks/default/bosses/` (76 core bosses)

### 3.1 Advanced Mechanistic Track Boss Catalog (`data/tracks/advanced/bosses/`)

The Advanced Mechanistic Mastery curriculum features **135 custom bosses** across 27 chapters stored in `data/tracks/advanced/bosses/`:

#### 3.1.1 Chapter 1: A Review of General Chemistry: Electrons, Bonds, and Molecular Properties
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Valence Vanguard** | `valence-vanguard.png` | 2.80 MB | A shimmering guardian forged from electron shells and fundamental orbital blocks. Mastery of valence electron counting, octet r... |
| **Electronegativity Elemental** | `electronegativity-elemental.png` | 2.68 MB | A polarized spirit that redistributes charge across chemical bonds. Predicting bond dipoles, electronegativity trends (Pauling ... |
| **Hybridization Hydra** | `hybridization-hydra.png` | 2.69 MB | A multi-headed beast whose geometries morph between linear, trigonal planar, and tetrahedral. Differentiating sp3, sp2, and sp ... |
| **Dipole Dragon** | `dipole-dragon.png` | 2.85 MB | A winged leviathan soaring on vectors of net molecular polarity. Vector addition of individual bond dipoles to determine net mo... |
| **Molecular Orbital Monarch** | `molecular-orbital-monarch.png` | 3.06 MB | The sovereign of constructive and destructive wave interference in the quantum realm. Constructing and interpreting molecular o... |

#### 3.1.2 Chapter 2: Molecular Representations
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Skeletal Sentry** | `skeletal-sentry.png` | 2.31 MB | A skeletal sentinel armored in zig-zag carbon backbones. Rapidly decoding bond-line (skeletal) structures, implicit hydrogen co... |
| **Lone Pair Phantom** | `lone-pair-phantom.png` | 2.88 MB | An elusive phantom that phases through unseen nonbonding electron pairs. Identifying and placing missing lone pairs on oxygen, ... |
| **Resonance Reaver** | `resonance-reaver.png` | 2.86 MB | A spectral pirate wielding dual curved arrows to redistribute pi-electron delocalization. Drawing valid resonance structures us... |
| **Formal Charge Fiend** | `formal-charge-fiend.png` | 2.68 MB | A calculation goblin punishing miscalculated atomic formal charges. Calculating formal charges accurately across neutral, catio... |
| **Delocalization Overlord** | `delocalization-overlord.png` | 3.07 MB | The ultimate master of conjugated pi systems and resonance major contributor evaluation. Evaluating major vs. minor resonance c... |

#### 3.1.3 Chapter 3: Acids and Bases
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Proton Pixie** | `proton-pixie.png` | 2.07 MB | A swift fairy delivering and abstracting single hydrogen ions. Identifying Brønsted-Lowry acids, bases, conjugate pairs, and si... |
| **Conjugate Chimera** | `conjugate-chimera.png` | 2.56 MB | A dual-natured monster balancing an acid head and a conjugate base tail. Predicting conjugate acid-base pairs and relating acid... |
| **Inductive Imp** | `inductive-imp.png` | 2.24 MB | A pesky demon that pulls electron density through electronegative halogen tethers. Assessing inductive effects and distance dep... |
| **ARIO Archmage** | `ario-archmage.png` | 2.88 MB | A grand sorcerer invoking the four sacred laws of conjugate base stabilization: A-R-I-O. Applying the ARIO mnemonic hierarchy t... |
| **Equilibrium Sovereign** | `equilibrium-sovereign.png` | 2.64 MB | The master of acid-base equilibria who dictates which side of the reaction dominates. Quantitatively calculating equilibrium co... |

#### 3.1.4 Chapter 4: Alkanes and Cycloalkanes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **IUPAC Infantry** | `iupac-infantry.png` | 2.27 MB | Foot soldiers marching strictly according to systematic IUPAC nomenclature rules. Mastering IUPAC naming rules for branched alk... |
| **Newman Nightmare** | `newman-nightmare.png` | 2.72 MB | A haunting entity projecting front-and-back carbon sights down the C-C axis. Visualizing and drawing Newman projections, identi... |
| **Torsional Titan** | `torsional-titan.png` | 2.96 MB | A colossal golem driven by eclipsing electron repulsion and gauche steric clash. Quantifying conformational energy costs of H/H... |
| **Chair-Flip Champion** | `chair-flip-champion.png` | 2.18 MB | A nimble martial artist who flips cyclohexanes between alternating chair conformations. Mastering chair cyclohexane ring flips,... |
| **1,3-Diaxial Dreadnought** | `13-diaxial-dreadnought.png` | 2.23 MB | A fortified juggernaut loaded with bulky t-butyl equatorial anchors. Calculating conformational equilibrium (A-values) and iden... |

#### 3.1.5 Chapter 5: Stereoisomerism
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Chirality Cerberus** | `chirality-cerberus.png` | 2.44 MB | A three-headed hound guarding stereogenic tetrahedral carbon centers. Locating chiral (stereogenic) centers and identifying int... |
| **Cahn-Ingold-Prelog Captain** | `cahn-ingold-prelog-captain.png` | 2.48 MB | A disciplined naval captain who assigns CIP priority numbers with atomic rigor. Assigning (R) and (S) configurations to chiral ... |
| **Enantiomer Enchanter** | `enantiomer-enchanter.png` | 2.92 MB | A mirror-realm sorcerer who commands non-superimposable mirror image reflections. Distinguishing enantiomers, understanding rac... |
| **Diastereomer Duelist** | `diastereomer-duelist.png` | 2.67 MB | A swordmaster wielding non-mirror stereoisomer blades with distinct physical properties. Differentiating diastereomers from ena... |
| **Meso Monarch** | `meso-monarch.png` | 2.70 MB | A tranquil emperor whose internal symmetry renders multi-chiral architectures achiral. Recognizing meso compounds, their intern... |

#### 3.1.6 Chapter 6: Chemical Reactivity and Mechanisms
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Enthalpy Elemental** | `enthalpy-elemental.png` | 2.68 MB | A thermal elemental controlling bond dissociation energies (BDE) and heat of reaction. Calculating heats of reaction from bond ... |
| **Entropy Spectre** | `entropy-spectre.png` | 2.81 MB | A chaotic ghost increasing molecular disorder and degree of freedom. Evaluating entropy changes (Delta S) based on molecule cou... |
| **Carbocation Colossus** | `carbocation-colossus.png` | 2.60 MB | A towering titan prone to spontaneous 1,2-hydride and 1,2-methyl shifts. Predicting carbocation stability ladders (3° > 2° > 1°... |
| **Transition State Trickster** | `transition-state-trickster.png` | 2.59 MB | An elusive phantom perched atop the highest energy peak of reaction coordinate diagrams. Interpreting reaction coordinate diagr... |
| **Gibbs Free Energy Sovereign** | `gibbs-free-energy-sovereign.png` | 2.92 MB | The supreme arbiter of chemical spontaneity, thermodynamics, and kinetics. Mastering thermodynamic spontaneity (Delta G < 0), e... |

#### 3.1.7 Chapter 7: Alkyl Halides: Nucleophilic Substitution and Elimination Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Halide Hound** | `halide-hound.png` | 2.37 MB | A tracking beast that sniffs out leaving group abilities across alkyl halides. Ranking leaving group ability (I- > Br- > Cl- >>... |
| **SN2 Striker** | `sn2-striker.png` | 2.20 MB | A relentless assassin executing backside bimolecular nucleophilic attacks in a single concerted blow. Mastering concerted SN2 m... |
| **SN1 Shapeshifter** | `sn1-shapeshifter.png` | 2.51 MB | A two-step phantom who departs leaving groups first to form planar carbocation intermediates. Mastering unimolecular SN1 mechan... |
| **Zaitsev-Hofmann Zealot** | `zaitsev-hofmann-zealot.png` | 2.67 MB | A dual-bladed zealot wielding small strong bases (EtO-) and bulky sterically hindered bases (t-BuOK). Controlling E2 regioselec... |
| **Walden Inversion Warlord** | `walden-inversion-warlord.png` | 3.02 MB | The grand warlord commanding the complete 16-quadrant SN1/SN2/E1/E2 competition matrix. Navigating the complete SN1/SN2/E1/E2 d... |

#### 3.1.8 Chapter 8: Addition Reactions of Alkenes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Pi-Bond Paladin** | `pi-bond-paladin.png` | 2.11 MB | A knight clad in electron-rich pi-orbital armor, seeking electrophilic reagents. Understanding alkene structure, electron densi... |
| **Markovnikov Minotaur** | `markovnikov-minotaur.png` | 2.80 MB | A raging minotaur charging towards the more substituted carbon to place protons on the richer carbon. Applying Markovnikov's ru... |
| **Bromonium Berserker** | `bromonium-berserker.png` | 2.61 MB | A dual-clawed berserker locking alkenes in a rigid three-membered halonium bridge. Mastering halogenation (Br2/Cl2) and halohyd... |
| **Hydroboration Harrier** | `hydroboration-harrier.png` | 2.59 MB | A tactical archer delivering BH3-THF in a concerted 4-membered syn-transition state. Mastering hydroboration-oxidation (BH3:THF... |
| **Ozonolysis Overlord** | `ozonolysis-overlord.png` | 2.75 MB | A destructive titan that cleaves carbon-carbon double bonds with ozone blades. Predicting ozonolysis cleavage products (O3, DMS... |

#### 3.1.9 Chapter 9: Alkynes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Triple-Bond Troll** | `triple-bond-troll.png` | 2.67 MB | A sturdy troll wielding rigid sp-hybridized linear triple-bond clubs. Understanding alkyne structure, sp hybridization, 180° bo... |
| **Acetylide Assassin** | `acetylide-assassin.png` | 2.27 MB | A stealth assassin carrying terminal alkynyl anions generated by strong NaNH2 base. Mastering terminal alkyne deprotonation wit... |
| **Keto-Enol Karkinos** | `keto-enol-karkinos.png` | 2.91 MB | A crab-like monster that rapidly tautomerizes unstable enols into stable carbonyls. Understanding Markovnikov hydration (HgSO4/... |
| **Lindlar Lancer** | `lindlar-lancer.png` | 2.26 MB | A poisoned-catalyst lancer who selectively pauses catalytic hydrogenation at the alkene stage. Employing poisoned Lindlar's cat... |
| **Dissolving Metal Dragon** | `dissolving-metal-dragon.png` | 2.54 MB | A fierce sodium dragon swimming in liquid ammonia at -78°C. Mastering dissolving metal reduction (Na in liquid NH3) via radical... |

#### 3.1.10 Chapter 10: Radical Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Homolytic Harpy** | `homolytic-harpy.png` | 3.22 MB | A flying harpy with razor single-barbed fishhook talons that cleave bonds homolytically. Understanding homolytic bond cleavage,... |
| **Chlorination Cyclops** | `chlorination-cyclops.png` | 2.89 MB | A wild cyclops firing unselective, highly reactive chlorine radicals. Understanding the unselective nature of radical chlorinat... |
| **Allylic Radical Archer** | `allylic-radical-archer.png` | 2.43 MB | A sniper who stabilizes radical centers via delocalization across adjacent pi-systems. Mastering allylic and benzylic radical s... |
| **Bromination Behemoth** | `bromination-behemoth.png` | 1.96 MB | A patient, highly selective behemoth that attacks only the weakest C-H bond (3° carbons). Mastering the extreme regioselectivit... |
| **Autooxidation Sovereign** | `autooxidation-sovereign.png` | 3.21 MB | The dread master of radical cascade degradation and polymer cross-linking. Mastering radical autooxidation mechanisms, free rad... |

#### 3.1.11 Chapter 11: Synthesis
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **FGI Footman** | `fgi-footman.png` | 2.65 MB | A versatile soldier skilled in functional group interconversions (FGIs). Executing one-step functional group conversions (alken... |
| **Carbon-Chain Centaur** | `carbon-chain-centaur.png` | 2.42 MB | A charging centaur who lengthens carbon chains using terminal acetylide and Grignard reagents. Identifying carbon-carbon bond f... |
| **Synthon Shapeshifter** | `synthon-shapeshifter.png` | 2.82 MB | A mysterious entity that breaks down target molecules into idealized charged synthon fragments. Understanding retrosynthetic di... |
| **Disconnection Duelist** | `disconnection-duelist.png` | 2.39 MB | A master swordsman who severs strategic bonds to reveal simpler starting materials. Formulating backwards (retrosynthetic) mult... |
| **Retrosynthesis Sovereign** | `retrosynthesis-sovereign.png` | 3.06 MB | The grand master of organic architecture capable of designing multi-step total syntheses. Assembling coherent, high-yielding 3-... |

#### 3.1.12 Chapter 12: Alcohols and Phenols
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Hydroxyl Hydra** | `hydroxyl-hydra.png` | 2.61 MB | A multi-headed aquatic hydra thriving in networks of hydrogen bonding. Mastering alcohol nomenclature, physical properties, hyd... |
| **Grignard Guardian** | `grignard-guardian.png` | 2.15 MB | A metal-shielded golem armed with nucleophilic organomagnesium (RMgX) blades. Mastering Grignard synthesis of 1°, 2°, and 3° al... |
| **Chromic Acid Crusher** | `chromic-acid-crusher.png` | 2.75 MB | A ruthless crusher wielding harsh Jones reagent (H2CrO4 / CrO3, H2SO4). Predicting oxidation products of 1°, 2°, and 3° alcohol... |
| **Phenol Phantom** | `phenol-phantom.png` | 2.77 MB | A resonance-stabilized phantom whose aromatic hydroxyl displays enhanced acidity (pKa ~ 10). Understanding phenol acidity, reso... |
| **Swern-PCC Sovereign** | `swern-pcc-sovereign.png` | 2.57 MB | A precise sovereign wielding mild, selective oxidation reagents (PCC, DMP, Swern). Mastering selective mild oxidations (PCC, De... |

#### 3.1.13 Chapter 13: Ethers and Epoxides; Thiols and Sulfides
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alkoxy Ape** | `alkoxy-ape.png` | 2.79 MB | A nimble primate swinging across unreactive ether solvent bridges. Recognizing ether structure, physical properties, low chemic... |
| **Williamson Warden** | `williamson-warden.png` | 2.53 MB | A castle warden who pairs alkoxide nucleophiles with primary alkyl halides. Mastering the Williamson Ether Synthesis, choosing ... |
| **Epoxide Enchanter** | `epoxide-enchanter.png` | 2.38 MB | A master of ring strain who concentrates 105 kJ/mol of energy into three-membered oxirane rings. Understanding epoxide ring str... |
| **Oxirane Opener** | `oxirane-opener.png` | 2.05 MB | A dual-stance warrior who switches ring-opening attacks between acidic and basic conditions. Mastering the regiochemistry and s... |
| **Thiol-Crown Tyrant** | `thiol-crown-tyrant.png` | 2.91 MB | An ancient tyrant commanding sulfur analogs (thiols, sulfides) and crown ether cation cages. Mastering thiol/sulfide chemistry ... |

#### 3.1.14 Chapter 14: Infrared Spectroscopy and Mass Spectrometry
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Wavenumber Wraith** | `wavenumber-wraith.png` | 2.73 MB | A spectral wraith hovering across the infrared spectrum from 4000 to 400 cm-1. Understanding IR spectroscopy theory, Hooke's la... |
| **Carbonyl Peak Corsair** | `carbonyl-peak-corsair.png` | 2.62 MB | A pirate targeting intense, razor-sharp C=O stretching absorptions at ~1715 cm-1. Identifying diagnostic IR peaks (carbonyl ~17... |
| **McLafferty Mage** | `mclafferty-mage.png` | 2.52 MB | A mystic who executes six-membered cyclic gamma-hydrogen radical rearrangements in the mass spec chamber. Mastering mass spectr... |
| **Isotope Inquisitor** | `isotope-inquisitor.png` | 2.73 MB | An inquisitor who inspects (M+1) and (M+2) isotope peak ratios with microscopic precision. Using isotopic peak distributions (M... |
| **Molecular Ion Monarch** | `molecular-ion-monarch.png` | 2.85 MB | The sovereign of the mass spec chamber who reveals exact molecular weight and degrees of unsaturation. Determining exact molecu... |

#### 3.1.15 Chapter 15: Nuclear Magnetic Resonance Spectroscopy
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Chemical Shift Sprite** | `chemical-shift-sprite.png` | 2.52 MB | A cheerful sprite placing proton signals along the 0 to 12 ppm delta frequency scale. Understanding chemical shift (ppm), refer... |
| **Splitting Sentry** | `splitting-sentry.png` | 2.67 MB | A vigilant guard counting neighboring protons using the rigid (n+1) multiplicity rule. Applying the (n+1) splitting rule, ident... |
| **DEPT Demon** | `dept-demon.png` | 2.73 MB | A multi-pulse spectral demon who separates 13C signals into CH3, CH2, CH, and quaternary carbons. Interpreting broadband-decoup... |
| **Anisotropic Archon** | `anisotropic-archon.png` | 2.96 MB | A dimensional archon who bends induced magnetic fields through aromatic rings and pi bonds. Explaining magnetic anisotropy in a... |
| **Coupling Constant Conqueror** | `coupling-constant-conqueror.png` | 2.90 MB | The grand master of coupling constants (J values), complex splitting trees, and full structure elucidation. Integrating 1H NMR,... |

#### 3.1.16 Chapter 16: Conjugated Pi Systems and Pericyclic Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Diene Demon** | `diene-demon.png` | 2.55 MB | A cunning demon wielding alternating single and double bonds in s-cis and s-trans conformations. Classifying isolated, conjugat... |
| **1,4-Addition Anomaly** | `14-addition-anomaly.png` | 2.39 MB | A dual-faced anomaly that attacks conjugated dienes under temperature-dependent regimes. Mastering electrophilic addition to co... |
| **Woodward-Hoffmann Wyrm** | `woodward-hoffmann-wyrm.png` | 2.84 MB | A mystical dragon soaring on frontier molecular orbitals (HOMO and LUMO). Applying frontier molecular orbital (FMO) theory to e... |
| **Endo-Exo Executor** | `endo-exo-executor.png` | 2.68 MB | A precise executor enforcing secondary orbital overlap during Diels-Alder cycloadditions. Predicting the endo rule, stereospeci... |
| **Diels-Alder Overlord** | `diels-alder-overlord.png` | 2.79 MB | The supreme commander of [4+2] cycloadditions, electrocyclic ring closures, and sigmatropic shifts. Mastering Diels-Alder [4+2]... |

#### 3.1.17 Chapter 17: Aromatic Compounds
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Benzene Basilisk** | `benzene-basilisk.png` | 2.29 MB | A legendary serpent coiled within a perfectly symmetrical, planar 6-carbon ring. Understanding the special stability of benzene... |
| **Hückel Herald** | `hckel-herald.png` | 2.55 MB | A herald proclaiming the sacred 4n+2 pi-electron law of aromaticity. Applying Hückel's Rule (4n+2 pi electrons, cyclic, planar,... |
| **Annulene Abomination** | `annulene-abomination.png` | 2.15 MB | A flexible nonplanar giant whose puckered geometry escapes antiaromatic instability. Distinguishing aromatic, antiaromatic, and... |
| **Birch Berserker** | `birch-berserker.png` | 2.88 MB | A berserker wielding sodium and liquid ammonia to selectively reduce benzene into 1,4-cyclohexadienes. Mastering the Birch Redu... |
| **Aromaticity Overlord** | `aromaticity-overlord.png` | 2.99 MB | The master of aromatic heterocycles (pyridine, pyrrole, furan) and benzylic position transformations. Analyzing aromatic hetero... |

#### 3.1.18 Chapter 18: Aromatic Substitution Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Arenium Archer** | `arenium-archer.png` | 2.63 MB | A sniper who pierces aromatic rings to generate resonance-stabilized sigma complexes (arenium ions). Mastering the general mech... |
| **Friedel-Crafts Fiend** | `friedel-crafts-fiend.png` | 2.15 MB | A chaotic fiend launching alkyl and acyl carbocations onto benzene rings. Mastering Friedel-Crafts Alkylation (and carbocation ... |
| **Ortho-Para Oracle** | `ortho-para-oracle.png` | 2.56 MB | An oracle reading resonance and inductive effects of benzene substituents. Classifying activating (ortho/para), deactivating (m... |
| **Meisenheimer Marauder** | `meisenheimer-marauder.png` | 2.65 MB | A pirate who infiltrates electron-deficient aryl halides bearing strong ortho/para nitro groups. Mastering the SNAr mechanism, ... |
| **Benzyne Behemoth** | `benzyne-behemoth.png` | 2.98 MB | A towering behemoth that generates highly strained triple-bond benzyne intermediates via elimination. Mastering the Elimination... |

#### 3.1.19 Chapter 19: Aldehydes and Ketones
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Carbonyl Chimera** | `carbonyl-chimera.png` | 2.53 MB | A hybrid beast featuring a strongly polarized C=O carbon ripe for nucleophilic attack. Understanding carbonyl polarity, hybridi... |
| **Acetal Aegis** | `acetal-aegis.png` | 2.70 MB | A protective aegis composed of dual alkoxy groups on a single carbon protecting aldehydes/ketones. Mastering reversible acetal ... |
| **Imine-Enamine Imp** | `imine-enamine-imp.png` | 2.35 MB | A mischievous imp who pairs carbonyls with primary and secondary amines at pH 4.5. Mastering imine (from 1° amines) and enamine... |
| **Baeyer-Villiger Banshee** | `baeyer-villiger-banshee.png` | 2.63 MB | A wailing banshee inserting peroxy acid oxygens adjacent to carbonyl groups to forge esters. Mastering the Baeyer-Villiger oxid... |
| **Wittig Warlock** | `wittig-warlock.png` | 2.72 MB | A master conjurer who pairs phosphorus ylides with carbonyls to forge carbon-carbon double bonds. Mastering the Wittig reaction... |

#### 3.1.20 Chapter 20: Carboxylic Acids and Their Derivatives
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Carboxylate Captain** | `carboxylate-captain.png` | 2.68 MB | A captain commanding resonance-stabilized carboxylate anions and carboxylic acid dimers. Understanding carboxylic acid structur... |
| **Acid Chloride Assassin** | `acid-chloride-assassin.png` | 2.50 MB | The most reactive assassin in the acyl derivative hierarchy, equipped with a prime chloride leaving group. Mastering the prepar... |
| **Tetrahedral Titan** | `tetrahedral-titan.png` | 2.75 MB | A colossal titan who guides nucleophiles through the addition-elimination mechanism of acyl derivatives. Mastering the general ... |
| **Anhydride Archon** | `anhydride-archon.png` | 2.02 MB | A dual-acyl archon capable of transferring acyl groups cleanly into esters and amides. Mastering the preparation and synthetic ... |
| **Acyl Transfer Sovereign** | `acyl-transfer-sovereign.png` | 2.90 MB | The supreme sovereign commanding the complete acyl reactivity ladder (chlorides > anhydrides > esters > amides). Mastering the ... |

#### 3.1.21 Chapter 21: Alpha Carbon Chemistry: Enols and Enolates
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Tautomer Troll** | `tautomer-troll.png` | 3.11 MB | A nimble troll switching rapidly between keto and enol constitutional isomers. Understanding keto-enol tautomerism, thermodynam... |
| **LDA Lancer** | `lda-lancer.png` | 2.71 MB | A sterically bulky lancer wielding Lithium Diisopropylamide (LDA) at -78°C. Controlling kinetic vs. thermodynamic enolate forma... |
| **Aldol Alchemist** | `aldol-alchemist.png` | 2.75 MB | An alchemist who couples enolates with aldehydes to produce beta-hydroxy aldehydes and alpha,beta-unsaturated enones. Mastering... |
| **Claisen Centurion** | `claisen-centurion.png` | 2.53 MB | A Roman centurion commanding ester enolates to attack parent esters in nucleophilic acyl substitution. Mastering the Claisen co... |
| **Robinson Annulation Regent** | `robinson-annulation-regent.png` | 2.93 MB | The master of conjugate additions and ring-forming cascades. Mastering conjugate (Michael) 1,4-additions, Stork enamine synthes... |

#### 3.1.22 Chapter 22: Amines
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Amino Assassin** | `amino-assassin.png` | 2.34 MB | A nitrogen-bearing assassin acting as both a strong nucleophile and a Brønsted-Lowry base. Understanding amine classification (... |
| **Inversion Imp** | `inversion-imp.png` | 2.53 MB | A high-frequency imp who flips trivalent nitrogen lone pairs like an umbrella at room temperature. Explaining pyramidal nitroge... |
| **Gabriel Gargoyle** | `gabriel-gargoyle.png` | 2.79 MB | A stone gargoyle shielding nitrogen inside potassium phthalimide to forge pure primary amines. Mastering the Gabriel synthesis ... |
| **Hofmann Hunter** | `hofmann-hunter.png` | 2.42 MB | A hunter who exhausts amines with excess methyl iodide followed by thermal elimination with Ag2O. Mastering exhaustive methylat... |
| **Diazonium Dragon** | `diazonium-dragon.png` | 2.67 MB | A mythical dragon breathing nitrous acid (HNO2) to transform arylamines into reactive arenediazonium salts. Mastering diazotiza... |

#### 3.1.23 Chapter 23: Introduction to Organometallic Compounds
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Gilman Guardian** | `gilman-guardian.png` | 2.71 MB | A copper-shielded guardian wielding lithium dialkylcuprate reagents (R2CuLi). Mastering Gilman reagent (R2CuLi) preparation, Co... |
| **Carbenoid Cyclops** | `carbenoid-cyclops.png` | 2.58 MB | A cyclops firing zinc-copper carbenoids (ICH2ZnI) to convert alkenes into cyclopropanes. Mastering the Simmons-Smith reaction (... |
| **Stille Specter** | `stille-specter.png` | 2.76 MB | A palladium-bound specter coupling organotin reagents (R-SnR3) with aryl and vinyl halides. Understanding the catalytic cycle o... |
| **Suzuki Sorcerer** | `suzuki-sorcerer.png` | 2.74 MB | A sorcerer coupling aryl/vinyl boronic acids (R-B(OH)2) with organic halides under basic aqueous conditions. Mastering the Suzu... |
| **Cross-Coupling Conqueror** | `cross-coupling-conqueror.png` | 2.90 MB | The ultimate master of transition-metal catalysis commanding Heck, Negishi, and Grubbs Alkene Metathesis. Mastering the Heck re... |

#### 3.1.24 Chapter 24: Carbohydrates
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Aldose Apparition** | `aldose-apparition.png` | 2.71 MB | A polyhydroxy aldehyde apparition displaying straight-chain D- and L-configurations in Fischer projections. Mastering carbohydr... |
| **Pyranose Phantom** | `pyranose-phantom.png` | 2.75 MB | A cyclic phantom that folds open-chain aldoses into six-membered pyranose and five-membered furanose rings. Converting open-cha... |
| **Anomeric Archer** | `anomeric-archer.png` | 2.79 MB | An archer stationed at the C1 anomeric carbon who watches alpha and beta anomers equilibrate. Understanding the anomeric carbon... |
| **Kiliani-Fischer Knight** | `kiliani-fischer-knight.png` | 2.67 MB | A knight who extends aldose carbon chains by adding HCN followed by reduction and hydrolysis. Mastering the Kiliani-Fischer syn... |
| **Polysaccharide Pharaoh** | `polysaccharide-pharaoh.png` | 3.05 MB | The supreme ruler of complex glycosidic linkages commanding starch, glycogen, cellulose, and reducing sugars. Analyzing disacch... |

#### 3.1.25 Chapter 25: Amino Acids, Peptides, and Proteins
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Zwitterion Zealot** | `zwitterion-zealot.png` | 2.60 MB | A dipolar zealot carrying both a protonated ammonium (+NH3) and a carboxylate (-COO-) group. Mastering alpha-amino acid structu... |
| **Strecker Striker** | `strecker-striker.png` | 2.47 MB | A striker who condenses aldehydes with NH4Cl and NaCN followed by acidic hydrolysis. Mastering the Strecker synthesis, Hell-Vol... |
| **Edman Executioner** | `edman-executioner.png` | 2.43 MB | An analytical executioner who selectively cleaves N-terminal amino acid residues using phenyl isothiocyanate (PITC). Mastering ... |
| **Merrifield Mage** | `merrifield-mage.png` | 2.58 MB | A solid-phase synthesis mage who anchors peptide chains to insoluble polystyrene resin beads. Mastering solid-phase peptide syn... |
| **Polypeptide Sovereign** | `polypeptide-sovereign.png` | 3.04 MB | The master of protein architecture commanding primary, secondary (alpha-helices, beta-sheets), tertiary, and quaternary folds. ... |

#### 3.1.26 Chapter 26: Lipids
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Fatty Acid Fiend** | `fatty-acid-fiend.png` | 2.56 MB | A long-chain hydrocarbon fiend whose melting points drop dramatically with cis-double bond kinks. Mastering fatty acid structur... |
| **Micelle Minion** | `micelle-minion.png` | 2.65 MB | An amphipathic minion equipped with a polar hydrophilic head and a hydrophobic hydrocarbon tail. Understanding soap action, mic... |
| **Steroid Shifter** | `steroid-shifter.png` | 2.54 MB | A rigid tetracyclic shifter built from the iconic cyclopentanoperhydrophenanthrene (ABCD) ring nucleus. Recognizing the steroid... |
| **Terpene Tracker** | `terpene-tracker.png` | 2.10 MB | A tracker who reconstructs natural scent and flavor molecules from 5-carbon isoprene building blocks. Applying the Isoprene Rul... |
| **Phospholipid Patriarch** | `phospholipid-patriarch.png` | 3.00 MB | The patriarch of cellular membranes commanding phosphoglycerides and sphingolipids. Understanding phospholipid structure, lipid... |

#### 3.1.27 Chapter 27: Synthetic Polymers
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Monomer Marauder** | `monomer-marauder.png` | 2.54 MB | A rogue marauder who links vinyl monomers into long-chain macromolecules via radical and ionic pathways. Mastering chain-growth... |
| **Ziegler-Natta Zealot** | `ziegler-natta-zealot.png` | 2.70 MB | A coordination catalyst zealot commanding titanium-aluminum complexes (TiCl4 / Al(C2H5)3). Mastering stereoregular polymerizati... |
| **Copolymer Colossus** | `copolymer-colossus.png` | 2.72 MB | A versatile titan who blends multiple monomer feeds into tailored material properties. Differentiating copolymer topologies (ra... |
| **Crosslink Commander** | `crosslink-commander.png` | 2.61 MB | A commander who ties polymer strands together with covalent crosslinks and vulcanizing sulfur bridges. Understanding polymer ph... |
| **Macromolecule Monarch** | `macromolecule-monarch.png` | 3.29 MB | The sovereign of step-growth condensation polymers, synthetic fibers, and polymer sustainability. Mastering step-growth (conden... |

### 3.2 Foundational Track Boss Catalog (`data/tracks/foundational/bosses/` & `data/tracks/default/bosses/`)

The Foundational curriculum bosses are stored in `data/tracks/foundational/bosses/` (with core assets in `data/tracks/default/bosses/`):

#### 3.2.1 Chapter 1: Foundations of Structure & Bonding
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Orbital Ogre** | `orbital-ogre.png` | 2.95 MB | A hulking, ground-state brute wielding heavy dumbbell-shaped clubs representing $s$ and $p$ orbitals. Electron capacity ($2$ pe... |
| **Bondbreaker Brute** | `bondbreaker-brute.png` | 2.96 MB | An armored siege-warrior who wields twin cleavers, separating sigma and pi bonds with raw force. Bond dissociation energy, cova... |
| **Hybridization Goblin** | `hybridization-goblin.png` | 2.66 MB | An energetic trickster juggling tetrahedral, trigonal planar, and linear geometric runes. $sp^3$, $sp^2$, and $sp$ hybridizatio... |
| **Polarity Phantom** | `polarity-phantom.png` | 2.63 MB | A floating, translucent apparition wrapped in shifting positive and negative dipole shrouds. Molecular dipole moments, vector a... |
| **Molecular Property Titan** | `molecular-property-titan.png` | 2.94 MB | A towering elemental forged from ice, boiling steam, and crystal lattices. Hydrogen bonding, dipole-dipole interactions, and Lo... |

#### 3.2.2 Chapter 2: Molecular Representations
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Lewis Rune Knight** | `lewis-rune-knight.png` | 2.59 MB | A proud knight bearing an octet shield lined with formal valence dots. |
| **Skeletal Sketcher** | `skeletal-sketcher.png` | 2.56 MB | A swift rogue who slashes in zig-zag line angles, omitting implicit hydrogens. |
| **Conformation Mimic** | `conformation-mimic.png` | 2.60 MB | A shapeshifting mimic that twists single bonds into eclipsed and staggered stances. |
| **Functional Group Golem** | `functional-group-golem.png` | 2.95 MB | A stone colossus studded with reactive alchemical cores (alcohols, amines, halides). |
| **Molecular Mapmaster** | `molecular-mapmaster.png` | 2.60 MB | An arcane cartographer who builds complex constitutional isomers and molecular graphs. |

#### 3.2.3 Chapter 3: Acids & Bases in Organic Chemistry
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Proton Prowler** | `proton-prowler.png` | 2.45 MB | A swift feline beast that stalks and snatches Brønsted–Lowry protons ($H^+$). |
| **pKa Warlock** | `pka-warlock.png` | 2.53 MB | A calculating sorcerer wielding logarithmic acidity scales and ranking base strengths. |
| **Conjugate Basilisk** | `conjugate-basilisk.png` | 3.25 MB | A dual-headed serpent whose venomous bite demonstrates conjugate acid-base pairs. |
| **Equilibrium Lich** | `equilibrium-lich.png` | 2.97 MB | An ancient lich who tilts reaction balances toward the side with the weaker acid. |
| **Resonance Wraith** | `resonance-wraith.png` | 2.70 MB | A ghostly phantom that disperses negative charges across delocalized conjugate bases. |

#### 3.2.4 Chapter 4: Alkanes & Cycloalkanes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alkane Marauder** | `alkane-marauder.png` | 2.69 MB | A hardy wanderer clad in inert, nonpolar paraffin armor. |
| **Newman Sentinel** | `newman-sentinel.png` | 2.45 MB | A guardian whose circular shield displays staggered and eclipsed sightline projections. |
| **Conformer Imp** | `conformer-imp.png` | 2.45 MB | A mischievous demon twisting cyclohexanes between chair, boat, and twist-boat forms. |
| **Cycloalkane Crusher** | `cycloalkane-crusher.png` | 2.87 MB | A heavy brawler flipping equatorial and axial substituents under 1,3-diaxial strain. |
| **Ring-Strain Behemoth** | `ring-strain-behemoth.png` | 3.19 MB | A massive beast pressurized by the acute angle strain of 3- and 4-membered rings. |

#### 3.2.5 Chapter 5: Stereoisomerism & Chirality
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Chiral Chimera** | `chiral-chimera.png` | 3.11 MB | A mythical creature with two non-superimposable asymmetric faces. |
| **Enantiomer Elf** | `enantiomer-elf.png` | 2.60 MB | A mirror-twin archer whose left-handed and right-handed arrows rotate plane-polarized light in opposite directions. |
| **Diastereomer Duelist** | `diastereomer-duelist.png` | 2.45 MB | A tactical fencer with multiple stereocenters that change configuration independently. |
| **Conformation Seer** | `conformation-seer.png` | 3.04 MB | An oracle who peers into 3D space to assign $(R)$ and $(S)$ Cahn–Ingold–Prelog priorities. |
| **Stereochemistry Overlord** | `stereochemistry-overlord.png` | 2.82 MB | The master of optical activity, resolving racemic mixtures and unmasking meso traps. |

#### 3.2.6 Chapter 6: Chemical Reactivity & Reaction Mechanisms
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Curved-Arrow Trickster** | `curved-arrow-trickster.png` | 2.46 MB | A nimble illusionist guiding electron pairs from sources to sinks. |
| **Nucleophile Raider** | `nucleophile-raider.png` | 2.55 MB | An aggressive warrior rich with lone pairs and negative charges, seeking electrophiles. |
| **Electrophile Warden** | `electrophile-warden.png` | 2.80 MB | A defensive sentinel with empty orbitals ready to receive electron density. |
| **Transition-State Wraith** | `transition-state-wraith.png` | 2.72 MB | An ephemeral spirit haunting the highest energetic peak ($\Delta G^\ddagger$) of the reaction. |
| **Mechanism Titan** | `mechanism-titan.png` | 2.80 MB | A monumental boss executing multi-step mechanisms through rate-determining steps. |

#### 3.2.7 Chapter 7: Alkyl Halides (Substitution & Elimination)
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **SN2 Assassin** | `sn2-assassin.png` | 2.37 MB | A deadly ninja striking from the exact rear ($180^\circ$), delivering a clean Walden inversion. |
| **Carbocation Shapeshifter** | `carbocation-shapeshifter.png` | 2.81 MB | A planar intermediate that slides hydrides and methyl groups to achieve $3^\circ$ stability. |
| **SN1 Knight** | `sn1-knight.png` | 2.84 MB | A patient warrior who waits for the leaving group to depart before attacking from both faces. |
| **E2 Executioner** | `e2-executioner.png` | 2.89 MB | A heavy executioner who cleaves protons and halides only in anti-periplanar alignment. |
| **E1 Sorcerer** | `e1-sorcerer.png` | 2.85 MB | An arcane sorcerer weaving Zaitsev's rule to produce the most substituted, stable alkenes. |

#### 3.2.8 Chapter 8: Addition Reactions of Alkenes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alkene Charger** | `alkene-charger.png` | 2.61 MB | A beast charging forward on the exposed electron density of its carbon–carbon double bond. |
| **Markovnikov Marauder** | `markovnikov-marauder.png` | 2.70 MB | A tactician who directs electrophilic additions strictly to the more substituted carbon. |
| **Halohydrin Hydra** | `halohydrin-hydra.png` | 3.00 MB | A multi-headed beast generating bridged halonium ions trapped by water. |
| **Hydroboration Ranger** | `hydroboration-ranger.png` | 2.64 MB | A precise ranger delivering anti-Markovnikov, syn-addition strikes with borane. |
| **Addition Reaction Titan** | `addition-reaction-titan.png` | 3.14 MB | Master of catalytic hydrogenation, ozonolysis, and epoxidation pathways. |

#### 3.2.9 Chapter 9: Alkynes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Acetylide Archer** | `acetylide-archer.png` | 2.37 MB | An agile archer firing deprotonated terminal alkyne arrows into alkyl halides. |
| **Triple-Bond Basilisk** | `triple-bond-basilisk.png` | 3.11 MB | An ancient serpent encased in dense, cylindrical $sp$-hybridized electron clouds. |
| **Hydration Harpy** | `hydration-harpy.png` | 2.92 MB | A winged harpy that tautomerizes unstable enols into stable methyl ketones. |
| **Reduction Reaver** | `reduction-reaver.png` | 2.74 MB | A warrior choosing between Lindlar's shield (cis-alkenes) and dissolving metal (trans-alkenes). |
| **Alkyne Overlord** | `alkyne-overlord.png` | 2.73 MB | The sovereign ruler of synthesis, chain elongation, and oxidative cleavage. |

#### 3.2.10 Chapter 10: Radical Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Initiation Imp** | `initiation-imp.png` | 2.54 MB | A fiery imp using heat and light to homolytically cleave peroxides into radical pairs. |
| **Propagation Phantom** | `propagation-phantom.png` | 2.60 MB | A self-sustaining specter that regenerates radical intermediates with every attack. |
| **Radical Reaper** | `radical-reaper.png` | 2.96 MB | A grim reaper whose scythe selectively harvests weak allylic and $3^\circ$ benzylic C–H bonds. |
| **Halogenation Hunter** | `halogenation-hunter.png` | 2.39 MB | A selective hunter balancing the fiery non-selectivity of chlorine with the surgical precision of bromine. |
| **Chain-Reaction Colossus** | `chain-reaction-colossus.png` | 2.96 MB | A colossal monster driven by rapid polymer propagation and radical termination. |

#### 3.2.11 Chapter 11: Multi-Step Organic Synthesis
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Retrosynthesis Rogue** | `retrosynthesis-rogue.png` | 2.51 MB | A mastermind who cuts complex targets into accessible precursor synthons. |
| **Reagent Alchemist** | `reagent-alchemist.png` | 2.57 MB | A potion-master selecting selective oxidizing and reducing reagents. |
| **Transformation Tactician** | `transformation-tactician.png` | 2.86 MB | A strategist maneuvering protecting groups and functional group interconversions. |
| **Synthetic Pathweaver** | `synthetic-pathweaver.png` | 2.57 MB | A planner routing stereoselective steps with high yields and minimal side products. |
| **Synthesis Grandmaster** | `synthesis-grandmaster.png` | 3.01 MB | The legendary architect capable of assembling natural products from simple feedstocks. |

#### 3.2.12 Chapter 12: Alcohols & Phenols
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alcohol Alchemist** | `alcohol-alchemist.png` | 2.65 MB | A master of conversion, turning alcohols into halides via tosylates and thionyl chloride. |
| **Phenol Phantom** | `phenol-phantom.png` | 2.59 MB | An aromatic spirit whose conjugate phenoxide is stabilized across the benzene ring. |
| **Oxidation Ogre** | `oxidation-ogre.png` | 2.83 MB | A brute wielding Jones reagents and PCC to oxidize primary and secondary alcohols. |
| **Dehydration Djinn** | `dehydration-djinn.png` | 3.01 MB | An elemental spirit consuming water molecules under acid catalysis to yield alkenes. |
| **Hydroxyl Golem** | `hydroxyl-golem.png` | 3.14 MB | A towering monolith demonstrating hydrogen bonding, solubility, and Grignard vulnerability. |

#### 3.2.13 Chapter 13: Ethers, Epoxides, Thiols & Sulfides
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Ether Enchanter** | `ether-enchanter.png` | 2.78 MB | A defensive caster shielded by unreactive Williamson ether frameworks. |
| **Epoxide Ambusher** | `epoxide-ambusher.png` | 2.55 MB | A coiled beast primed with $60^\circ$ ring strain, waiting to burst open. |
| **Ring-Opening Rogue** | `ring-opening-rogue.png` | 2.72 MB | A rogue directing acid attacks to the more substituted carbon and base attacks to the less hindered carbon. |
| **Thiol Trickster** | `thiol-trickster.png` | 2.60 MB | A sulfur-wielding skirmisher forming reversible disulfide bridges. |
| **Sulfide Sentinel** | `sulfide-sentinel.png` | 2.80 MB | An armored guardian controlling thioethers, sulfoxides, and sulfonium leaving groups. |

#### 3.2.14 Chapter 14: Infrared (IR) Spectroscopy & Mass Spectrometry
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Vibration Wraith** | `vibration-wraith.png` | 2.95 MB | A phantom vibrating in symmetric stretches, asymmetric bends, and wagging modes. |
| **Fingerprint Fiend** | `fingerprint-fiend.png` | 2.84 MB | An examiner identifying diagnostic patterns in the dense region below $1500\text{ cm}^{-1}$. |
| **IR Specter** | `ir-specter.png` | 2.67 MB | A spectral master reading carbonyl spikes ($1715\text{ cm}^{-1}$) and broad hydroxyl valleys ($3300\text{ cm}^{-1}$). |
| **Fragmentation Phantom** | `fragmentation-phantom.png` | 2.46 MB | An entity cleaving molecular ions into allylic cations, acylium ions, and alpha-cleavage shards. |
| **Mass-Spec Behemoth** | `mass-spec-behemoth.png` | 3.15 MB | A giant weighing $m/z$ ratios, recognizing isotopic signatures ($M+2$ for Cl and Br), and identifying base peaks. |

#### 3.2.15 Chapter 15: Nuclear Magnetic Resonance (NMR) Spectroscopy
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Chemical-Shift Seer** | `chemical-shift-seer.png` | 2.88 MB | An oracle charting ppm positions based on electronegative shielding and deshielding. |
| **Integration Illusionist** | `integration-illusionist.png` | 2.76 MB | A scholar calculating the exact ratio of hydrogen atoms from step-curve peak areas. |
| **Splitting Sorcerer** | `splitting-sorcerer.png` | 3.01 MB | A mathematician casting the $N+1$ multiplicity rule across singlets, doublets, and quartets. |
| **Coupling Conjurer** | `coupling-conjurer.png` | 2.49 MB | An archmage measuring $J$-coupling constants across adjacent spin systems. |
| **NMR Oracle** | `nmr-oracle.png` | 2.76 MB | The supreme elucidator who constructs complete 3D structures from combined $^1\text{H}$ and $^{13}\text{C}$ spectra. |

#### 3.2.16 Chapter 16: Conjugated Pi Systems & Pericyclic Reactions
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Conjugation Conjurer** | `conjugation-conjurer.png` | 2.75 MB | A summoner linking alternating single and double bonds to absorb visible light. |
| **Diene Duelist** | `diene-duelist.png` | 2.75 MB | A fighter adopting the rigid s-cis conformation required for cyclic closure. |
| **Diels–Alder Dragon** | `diels-alder-dragon.png` | 2.75 MB | A legendary beast executing $[4+2]$ cycloadditions with endo-stereoselectivity. |
| **Orbital-Symmetry Sphinx** | `orbital-symmetry-sphinx.png` | 2.75 MB | A guardian posing riddles of HOMO-LUMO overlaps and Woodward–Hoffmann rules. |
| **Pericyclic Overlord** | `pericyclic-overlord.png` | 2.75 MB | Sovereign of electrocyclic ring openings, sigmatropic shifts, and concerted transition states. |

#### 3.2.17 Chapter 17: Aromatic Compounds
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Benzene Beast** | `benzene-beast.png` | 2.75 MB | A mythical beast fortified with $36\text{ kcal/mol}$ of aromatic resonance stabilization energy. |
| **Aromaticity Archon** | `aromaticity-archon.png` | 2.75 MB | A judge enforcing planarity, complete conjugation, and cyclic orbital overlap. |
| **Hückel Hexer** | `h-ckel-hexer.png` | 2.75 MB | A warlock casting the $4n+2$ $\pi$-electron rule to banish anti-aromatic intruders. |
| **Resonance Dragon** | `resonance-dragon.png` | 2.75 MB | A six-headed dragon cycling uncharged Kekulé canonical contributors. |
| **Aromatic Overlord** | `aromatic-overlord.png` | 2.75 MB | Master of heterocyclic rings (pyridine, pyrrole, furan, thiophene) and polycyclic aromatics. |

#### 3.2.18 Chapter 18: Electrophilic Aromatic Substitution (EAS)
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Electrophilic Aromatic Knight** | `electrophilic-aromatic-knight.png` | 2.75 MB | A noble knight delivering halogenation, nitration, and sulfonation strikes. |
| **Sigma-Complex Specter** | `sigma-complex-specter.png` | 2.75 MB | An arenium ion intermediate stabilizing positive charges across ortho and para carbons. |
| **Director Duelist** | `director-duelist.png` | 2.75 MB | A strategist balancing activating ortho/para directors against deactivating meta directors. |
| **Friedel–Crafts Forgefiend** | `friedel-crafts-forgefiend.png` | 2.75 MB | A forge-master wielding $\text{AlCl}_3$ catalysts for alkylation and acylations without rearrangement. |
| **Substitution Overlord** | `substitution-overlord.png` | 2.75 MB | Master of nucleophilic aromatic substitution ($\text{S}_\text{N}\text{Ar}$) and benzyne intermediates. |

#### 3.2.19 Chapter 19: Aldehydes & Ketones (Nucleophilic Addition)
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Carbonyl Crusher** | `carbonyl-crusher.png` | 2.75 MB | A titan focusing force through a strong polar $C^\delta+=O^\delta-$ dipole. |
| **Aldehyde Apparition** | `aldehyde-apparition.png` | 2.75 MB | A reactive spirit more vulnerable to nucleophilic attack than heavier ketones. |
| **Ketone Knight** | `ketone-knight.png` | 2.75 MB | A shielded knight protected by the steric and electronic donor effects of two alkyl groups. |
| **Nucleophilic Addition Necromancer** | `nucleophilic-addition-necromancer.png` | 2.75 MB | Summons hydrides, Grignard reagents, and cyanide to form cyanohydrins and alcohols. |
| **Carbonyl Dragon** | `carbonyl-dragon.png` | 2.75 MB | Breathes reversible acetals, hemiacetals, imines, and enamines. |

#### 3.2.20 Chapter 20: Carboxylic Acids & Their Derivatives
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Carboxylate Crusader** | `carboxylate-crusader.png` | 2.75 MB | A resilient crusader protected by resonance-stabilized carboxylate negative charge. |
| **Acyl Chloride Assassin** | `acyl-chloride-assassin.png` | 2.75 MB | The hyper-reactive apex of the acyl ladder, expelling chloride leaving groups instantly. |
| **Ester Enchanter** | `ester-enchanter.png` | 2.75 MB | A sweet-scented enchanter casting Fischer esterifications and saponification cleanses. |
| **Amide Juggernaut** | `amide-juggernaut.png` | 2.75 MB | A heavily fortified juggernaut stabilized by strong nitrogen lone-pair resonance. |
| **Acyl-Substitution Overlord** | `acyl-substitution-overlord.png` | 2.75 MB | The master orchestrating addition-elimination mechanisms through tetrahedral intermediates. |

#### 3.2.21 Chapter 21: Alpha Carbon Chemistry (Enols & Enolates)
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Alpha-Carbon Assassin** | `alpha-carbon-assassin.png` | 2.75 MB | A rogue abstracting acidic $\alpha$-hydrogens with strong bases like LDA. |
| **Enol Enchanter** | `enol-enchanter.png` | 2.75 MB | An enchanter rapidly shifting between keto and enol tautomers. |
| **Enolate Elemental** | `enolate-elemental.png` | 2.75 MB | An elemental channeling ambident nucleophilicity between carbon and oxygen. |
| **Aldol Warlock** | `aldol-warlock.png` | 2.75 MB | A warlock joining two carbonyl molecules into $\beta$-hydroxy aldehydes and $\alpha,\beta$-unsaturated enones. |
| **Condensation Colossus** | `condensation-colossus.png` | 2.75 MB | Master of Claisen condensations, Michael additions, and Robinson annulations. |

#### 3.2.22 Chapter 22: Amines & Nitrogen Compounds
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Amine Assassin** | `amine-assassin.png` | 2.75 MB | An agile fighter wielding primary, secondary, and tertiary basic lone pairs. |
| **Basicity Banshee** | `basicity-banshee.png` | 2.75 MB | A shrieking banshee whose power scales with inductive electron donation and solvation stability. |
| **Ammonium Guardian** | `ammonium-guardian.png` | 2.75 MB | A shielded guardian holding positive formal charges in quaternary ammonium salts. |
| **Nitrogen Necromancer** | `nitrogen-necromancer.png` | 2.75 MB | Casts reductive aminations and forms diazonium salts for Sandmeyer reactions. |
| **Amine Overlord** | `amine-overlord.png` | 2.75 MB | Master of Hofmann eliminations (giving less substituted alkenes) and Curtius rearrangements. |

#### 3.2.23 Chapter 23: Organometallic Chemistry
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Grignard Golem** | `grignard-golem.png` | 2.75 MB | A heavy golem forged of alkylmagnesium halides in anhydrous ether armor. |
| **Organolithium Lancer** | `organolithium-lancer.png` | 2.75 MB | An aggressive lancer wielding intense carbon–lithium ionic polarity. |
| **Metal–Carbon Mercenary** | `metal-carbon-mercenary.png` | 2.75 MB | A mercenary utilizing Gilman cuprate reagents for soft 1,4-conjugate additions. |
| **Organometallic Alchemist** | `organometallic-alchemist.png` | 2.75 MB | Master of Suzuki, Heck, and cross-coupling reactions with palladium catalysts. |
| **Carbon–Metal Titan** | `carbon-metal-titan.png` | 2.75 MB | Master of alkene metathesis and carbenoid Simmons–Smith cyclopropanations. |

#### 3.2.24 Chapter 24: Carbohydrates & Sugars
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Monosaccharide Mimic** | `monosaccharide-mimic.png` | 2.75 MB | A mimic shifting between D- and L-aldoses and ketoses in Fischer projections. |
| **Anomer Assassin** | `anomer-assassin.png` | 2.75 MB | Strikes at the mutarotating C1 anomeric carbon between $\alpha$ and $\beta$ configurations. |
| **Glycosidic Guardian** | `glycosidic-guardian.png` | 2.75 MB | A guardian holding polysaccharides together with stable acetal ether links. |
| **Ring–Chain Shapeshifter** | `ring-chain-shapeshifter.png` | 2.75 MB | Reversibly opens and closes between open-chain aldehydes and cyclic pyranose chairs. |
| **Carbohydrate Colossus** | `carbohydrate-colossus.png` | 2.75 MB | Master of starch, cellulose, reducing sugars, and Tollens/Benedict oxidation tests. |

#### 3.2.25 Chapter 25: Amino Acids, Peptides & Proteins
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Zwitterion Zealot** | `zwitterion-zealot.png` | 2.75 MB | A warrior maintaining dual charges ($-\text{NH}_3^+$ and $-\text{COO}^-$) at the isoelectric point (pI). |
| **Amino Acid Knight** | `amino-acid-knight.png` | 2.75 MB | A versatile knight wielding diverse side-chain chemistry (acidic, basic, polar, nonpolar). |
| **Peptide Binder** | `peptide-binder.png` | 2.75 MB | Forges rigid, planar amide bonds through ribosomal dehydration coupling. |
| **Protein-Folding Phantom** | `protein-folding-phantom.png` | 2.75 MB | Weaves $\alpha$-helices, $\beta$-sheets, and tertiary folding driven by hydrophobic collapse. |
| **Polypeptide Titan** | `polypeptide-titan.png` | 2.75 MB | A quaternary multi-subunit enzyme complex orchestrating all biochemical reactions. |

#### 3.2.26 Chapter 26: Lipids & Cell Membranes
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Fatty-Acid Fiend** | `fatty-acid-fiend.png` | 2.75 MB | A serpentine fiend with long hydrocarbon tails featuring saturated and cis-unsaturated kinks. |
| **Triglyceride Troll** | `triglyceride-troll.png` | 2.75 MB | A hoarder of energy storing glycerol triesters in adipose reserves. |
| **Phospholipid Phantom** | `phospholipid-phantom.png` | 2.75 MB | An amphipathic phantom with polar phosphate heads and twin hydrophobic tails. |
| **Membrane Marauder** | `membrane-marauder.png` | 2.75 MB | Infiltrates fluid mosaic bilayers and navigates cholesterol fluidity gates. |
| **Lipid Leviathan** | `lipid-leviathan.png` | 2.75 MB | Master of prostaglandins, steroid hormones, terpenes, and micellar self-assembly. |

#### 3.2.27 Chapter 27: Synthetic Polymers & Materials
| Boss | Asset | Size | Lore / Topic |
|---|---|---|---|
| **Monomer Mimic** | `monomer-mimic.png` | 2.75 MB | A small, reactive building block capable of repeated addition across pi bonds. |
| **Initiator Imp** | `initiator-imp.png` | 2.75 MB | Generates free radicals, cations, or anions to spark chain-growth cascades. |
| **Chain-Growth Golem** | `chain-growth-golem.png` | 2.75 MB | A rapidly expanding golem that adds thousands of ethylene units in milliseconds. |
| **Crosslink Colossus** | `crosslink-colossus.png` | 2.75 MB | Forges covalent bridges between polymer chains to turn pliable plastics into rigid thermosets. |
| **Polymer Overlord** | `polymer-overlord.png` | 2.75 MB | Sovereign of nylon condensations, polyesters, conducting polymers, and recycling recycling depolymerization. |

### 3.3 Universal Fallback Asset
| Asset | Path | Size | Description |
|---|---|---|---|
| **Boss Placeholder** | [`static/assets/bosses/boss-placeholder.svg`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/assets/bosses/boss-placeholder.svg) | 349 B | Clean, lightweight SVG vector badge displaying an arcane alchemical glyph. Automatically rendered if an unmapped asset is requested. |

---
## 4. Curricula & Track Asset Resolution Architecture

The game's 20 tracks across 2 curricula organize their content and boss assets with a hierarchical resolution cascade:

### 4.1 Track Content Hierarchy (`data/tracks/`)

1. **Foundational Curriculum (8 Tracks)**:
   - `default`: Core 27-chapter curriculum with boss assets in `data/tracks/default/bosses/` (and shared static assets in `static/assets/bosses/`).
   - `found-nomenclature`: Chemical nomenclature, IUPAC naming conventions, and structural representations.
   - `found-stereochem`: Chiral centers, enantiomers, diastereomers, and R/S configuration trials.
   - `found-acidbase`: pKa comparisons, conjugate pairs, and acid-base equilibria.
   - `found-structure`: Lewis structures, resonance contributors, hybridization, and bonding properties.
   - `found-alkanes`: Conformational analysis, Newman projections, and ring strain.
   - `found-reactivity`: Nucleophiles, electrophiles, reaction coordinate diagrams, and transition states.
   - `found-alkylhalides`: SN1, SN2, E1, and E2 mechanisms and stereochemical outcomes.

2. **Advanced Mechanistic Mastery Curriculum (12 Tracks)**:
   - `adv-vocab`: Advanced vocabulary, terminology, and spectroscopic definitions (`VocabularyConceptsData`).
   - `adv-mechanisms`: Arrow-pushing cascades, polar reaction mechanisms, and intermediates (`MechanismsData`).
   - `adv-synthesis`: Retrosynthetic disconnections, protecting groups, and multi-step synthesis.
   - `adv-reagents`: Organometallic reagents, oxidizing/reducing agents, and catalyst selectivity.
   - `adv-acidbase`: Non-aqueous equilibria, thermodynamic vs kinetic acidity, and base catalysts.
   - `adv-stereochem`: Dynamic stereocontrol, Cram's chelate model, and chiral auxiliaries.
   - `adv-spectroscopy`: Combined 1D/2D NMR, IR diagnostic bands, and mass spectrometry fragmentation.
   - `adv-carbonyl`: Nucleophilic additions, enols, enolates, aldol/Claisen condensations, and conjugate additions.
   - `adv-aromatic`: EAS, NAS, benzyne intermediates, and Hückel/antiaromatic stability.
   - `adv-pericyclic`: Diels-Alder, electrocyclic, sigmatropic shifts, and orbital symmetry (FMO analysis).
   - `adv-outcomes`: Predicting major vs minor products, regioselectivity, and stereoselectivity.
   - `adv-radicals`: Radical chain mechanisms, halogenation selectivity, and single-electron transfers.

Detailed lore and chemical concepts for each creature are documented in [`FoundationalBestiary.md`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/FoundationalBestiary.md) and [`AdvancedBestiary.md`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/AdvancedBestiary.md).

### 4.2 Asset Resolution Cascade
When the loader (`app/domain/content/loader.py`) prepares boss illustrations for a duel, it traverses:
1. **Track-Specific Boss Folder**: `data/tracks/{track_id}/bosses/` (or configured `boss_folder` from `OB_tracks`).
2. **Default Track Boss Folder**: `data/tracks/default/bosses/`.
3. **Global Static Boss Assets**: `static/assets/bosses/` and `bosses/`.
4. **Universal Fallback**: `static/assets/bosses/boss-placeholder.svg`.

---

## 5. Processing, Optimization & Quality Standards

1. **Contiguous Alpha Channels**: All companion and boss PNGs have been cleaned to remove extraneous border artifacts and cropped tightly to the character bounding box with smooth transparency.
2. **Asynchronous & Lazy Loading**: HTML5 `<img loading="lazy" decoding="async">` attributes ensure zero main-thread blockage during high-speed turn interactions.
3. **Asset Resolution Safety**: Both backend (`app/domain/content/loader.py`) and frontend (`static/js/avatars.js`) feature resilient fallback handlers that catch missing asset errors and substitute `boss-placeholder.svg` without interrupting gameplay.
