// tracks-config.js — Organic Battles Track & Curriculum Registry
// Defines the two Curricula (Advanced Mechanistic Mastery & Foundational Open)
// and all 19 tracks with their configurable data_folder paths.

const CURRICULA = [
  {
    id: 'all',
    name: 'All Curricula',
    code: 'ALL'
  },
  {
    id: 'advanced',
    name: 'Advanced Mechanistic Mastery',
    code: 'A',
    total_questions: 16200,
    chapters: 27,
    bosses: 135
  },
  {
    id: 'foundational',
    name: 'Foundational Open',
    code: 'F',
    total_questions: 10850,
    chapters: 31,
    bosses: 155
  }
];

const TRACKS = [
  {
    id: 'default',
    curriculum: 'foundational',
    title: 'Default Track',
    detail: 'core curriculum · comprehensive chemistry',
    boss: 'Orbital Ogre',
    boss_folder: 'data/tracks/default/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'amber',
    data_folder: 'data/tracks/default'
  },
  // 12 Advanced Mechanistic Mastery Tracks
  {
    id: 'adv-vocab',
    curriculum: 'advanced',
    title: 'Vocabulary & Core Concepts',
    detail: 'definitions · patterns · principles',
    boss: 'The Lexicon',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'violet',
    data_folder: 'data/tracks/advanced/VocabularyConceptsData'
  },
  {
    id: 'adv-outcomes',
    curriculum: 'advanced',
    title: 'Reaction Outcomes',
    detail: '50 / 30 / 20 outcome weighting',
    boss: 'The Selector',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'coral',
    data_folder: 'data/tracks/advanced/ReactionOutComeTypesData'
  },
  {
    id: 'adv-arrows',
    curriculum: 'advanced',
    title: 'Curved Arrow & Intermediates',
    detail: 'electron flow · reactive species',
    boss: 'The Arrowmith',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'teal',
    data_folder: 'data/tracks/advanced/MechanismsIntermediatesData'
  },
  {
    id: 'adv-stereo',
    curriculum: 'advanced',
    title: 'Stereochemistry & Structure',
    detail: '3D thinking · configurations',
    boss: 'The Geometer',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'amber',
    data_folder: 'data/tracks/advanced/StereochemistryStructureData'
  },
  {
    id: 'adv-rankings',
    curriculum: 'advanced',
    title: 'Relative Property Rankings',
    detail: 'acidity · stability · reactivity',
    boss: 'The Comparator',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'pink',
    data_folder: 'data/tracks/advanced/RelativePropertyRankingsData'
  },
  {
    id: 'adv-spectra',
    curriculum: 'advanced',
    title: 'Spectroscopy',
    detail: 'IR · NMR · MS · DEPT',
    boss: 'The Signal',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'blue',
    data_folder: 'data/tracks/advanced/SpectroscopyElucidationData'
  },
  {
    id: 'adv-retro',
    curriculum: 'advanced',
    title: 'Multi-Step & Retrosynthesis',
    detail: 'disconnections · route design',
    boss: 'The Cartographer',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'lime',
    data_folder: 'data/tracks/advanced/MultiStepSynthesisData'
  },
  {
    id: 'adv-mo',
    curriculum: 'advanced',
    title: 'MO Theory & Pericyclics',
    detail: 'orbitals · electrocyclic logic',
    boss: 'The Orbitalist',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'indigo',
    data_folder: 'data/tracks/advanced/OrbitalPericyclicExpandedData'
  },
  {
    id: 'adv-thermo',
    curriculum: 'advanced',
    title: 'Thermodynamics & Kinetics Math',
    detail: 'energy · rates · equations',
    boss: 'The Kinetician',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'orange',
    data_folder: 'data/tracks/advanced/ThermodynamicsKineticsExpandedData'
  },
  {
    id: 'adv-medicinal',
    curriculum: 'advanced',
    title: 'Medicinal & Bioorganic Chemistry',
    detail: 'drug design · biomolecules',
    boss: 'The Pharmacist',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'rose',
    data_folder: 'data/tracks/advanced/MedicinalBioorganicExpandedData'
  },
  {
    id: 'adv-lab',
    curriculum: 'advanced',
    title: 'Lab Techniques & Green Chemistry',
    detail: 'workup · safety · sustainability',
    boss: 'The Steward',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'emerald',
    data_folder: 'data/tracks/advanced/LabTechniquesGreenExpandedData'
  },
  {
    id: 'adv-trees',
    curriculum: 'advanced',
    title: 'SkillBuilder Decision Trees',
    detail: 'choose the next best move',
    boss: 'The Brancher',
    boss_folder: 'data/tracks/advanced/bosses',
    questions: 1350,
    chapters: 27,
    accent: 'cyan',
    data_folder: 'data/tracks/advanced/SkillBuilderMasteryExpandedData'
  },
  // 7 Foundational Open Tracks
  {
    id: 'found-nomenclature',
    curriculum: 'foundational',
    title: 'Nomenclature & Concepts',
    detail: 'name it · see it · understand it',
    boss: 'The Namer',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'sky',
    data_folder: 'data/tracks/foundational/FoundationalNomenclatureData'
  },
  {
    id: 'found-outcomes',
    curriculum: 'foundational',
    title: 'Reaction Outcomes',
    detail: 'predict the product with confidence',
    boss: 'The Predictor',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'coral',
    data_folder: 'data/tracks/foundational/FoundationalReactionOutcomesData'
  },
  {
    id: 'found-mechanisms',
    curriculum: 'foundational',
    title: 'Reaction Mechanisms',
    detail: 'follow the electrons',
    boss: 'The Mechanist',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'teal',
    data_folder: 'data/tracks/foundational/FoundationalMechanismsData'
  },
  {
    id: 'found-stereo',
    curriculum: 'foundational',
    title: 'Stereochemistry Analysis',
    detail: 'wedges · dashes · spatial logic',
    boss: 'The Spatialist',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'amber',
    data_folder: 'data/tracks/foundational/FoundationalStereochemistryData'
  },
  {
    id: 'found-property',
    curriculum: 'foundational',
    title: 'Property & Acidity Rankings',
    detail: 'compare what matters',
    boss: 'The Ranker',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'pink',
    data_folder: 'data/tracks/foundational/FoundationalPropertyRankingsData'
  },
  {
    id: 'found-spectra',
    curriculum: 'foundational',
    title: 'Spectroscopy & Structure',
    detail: 'read the hidden structure',
    boss: 'The Listener',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'blue',
    data_folder: 'data/tracks/foundational/FoundationalSpectroscopyData'
  },
  {
    id: 'found-synthesis',
    curriculum: 'foundational',
    title: 'Multi-Step Synthesis',
    detail: 'build a route, one move at a time',
    boss: 'The Builder',
    boss_folder: 'data/tracks/foundational/bosses',
    questions: 1550,
    chapters: 31,
    accent: 'lime',
    data_folder: 'data/tracks/foundational/FoundationalMultiStepSynthesisData'
  }
];

// Helper to query tracks
function getTrackById(id) {
  return TRACKS.find((t) => t.id === id) || TRACKS[0];
}

function getCurriculumById(id) {
  return CURRICULA.find((c) => c.id === id);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CURRICULA, TRACKS, getTrackById, getCurriculumById };
}
