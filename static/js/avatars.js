const AVATAR_STATES = new Set(['idle', 'enter', 'cast', 'attack', 'hit', 'critical-hit', 'miss', 'victory', 'defeated', 'level-up']);

export const DEFAULT_AVATAR_CONFIG = {
  baseCharacter: 'organic-apprentice',
  skinTone: 'medium',
  hair: { style: 'messy-short', color: 'dark-green' },
  glasses: 'round-green',
  coat: 'classic-white',
  shirt: 'forest-green',
  pants: 'dark-green',
  shoes: 'green-sneakers',
  satchel: 'chemist-brown',
  flask: 'green-reaction',
  accessory: 'benzene-pin',
  accentColor: 'emerald',
};

export const PLAYER_AVATAR_OPTIONS = {
  skinTones: ['light', 'light-medium', 'medium', 'medium-deep', 'deep'],
  hairStyles: ['messy-short', 'side-swept', 'spiky', 'curly', 'medium-layered'],
  hairColors: ['black', 'dark-green', 'brown', 'dark-purple', 'blue-black'],
  glasses: ['none', 'round-black', 'round-green', 'rectangular-black', 'thin-silver'],
  coats: ['classic-white', 'green-trim', 'blue-trim', 'advanced-chemist', 'reaction-coat'],
  shirts: ['forest-green', 'navy', 'black', 'purple', 'white'],
  pants: ['dark-green', 'charcoal', 'navy', 'black'],
  shoes: ['green-sneakers', 'black-sneakers', 'chemist-boots', 'reaction-boots'],
  satchels: ['chemist-brown', 'dark-lab-bag', 'reaction-pouch', 'advanced-alchemist-pack'],
  flasks: ['green-reaction', 'blue-catalyst', 'purple-reagent', 'orange-energy'],
  accessories: ['benzene-pin', 'periodic-table-badge', 'molecule-brooch', 'reaction-arrow-pin', 'chemist-gloves', 'wrist-device'],
  accents: ['emerald', 'azure', 'violet', 'amber', 'crimson'],
};

export function normalizeAvatarConfig(config = {}) {
  const merged = {
    ...DEFAULT_AVATAR_CONFIG,
    ...config,
    hair: { ...DEFAULT_AVATAR_CONFIG.hair, ...(config.hair || {}) },
  };
  const valid = (key, value, fallback) => PLAYER_AVATAR_OPTIONS[key]?.includes(value) ? value : fallback;
  merged.skinTone = valid('skinTones', merged.skinTone, DEFAULT_AVATAR_CONFIG.skinTone);
  merged.hair.style = valid('hairStyles', merged.hair.style, DEFAULT_AVATAR_CONFIG.hair.style);
  merged.hair.color = valid('hairColors', merged.hair.color, DEFAULT_AVATAR_CONFIG.hair.color);
  merged.glasses = valid('glasses', merged.glasses, DEFAULT_AVATAR_CONFIG.glasses);
  merged.coat = valid('coats', merged.coat, DEFAULT_AVATAR_CONFIG.coat);
  merged.shirt = valid('shirts', merged.shirt, DEFAULT_AVATAR_CONFIG.shirt);
  merged.pants = valid('pants', merged.pants, DEFAULT_AVATAR_CONFIG.pants);
  merged.shoes = valid('shoes', merged.shoes, DEFAULT_AVATAR_CONFIG.shoes);
  merged.satchel = valid('satchels', merged.satchel, DEFAULT_AVATAR_CONFIG.satchel);
  merged.flask = valid('flasks', merged.flask, DEFAULT_AVATAR_CONFIG.flask);
  merged.accessory = valid('accessories', merged.accessory, DEFAULT_AVATAR_CONFIG.accessory);
  merged.accentColor = valid('accents', merged.accentColor, DEFAULT_AVATAR_CONFIG.accentColor);
  merged.baseCharacter = 'organic-apprentice';
  return merged;
}

export const CHARACTERS = {
  'organic-apprentice': { name: 'Organic Apprentice', type: 'player', asset: '/static/assets/avatars/organic-apprentice.png' },
  'reaction-mage': { name: 'Reaction Mage', type: 'player', asset: '/static/assets/avatars/reaction-mage.png' },
  'player-carbon-trailblazer': { name: 'Player Carbon Trailblazer', type: 'player', asset: '/static/assets/avatars/player-carbon-trailblazer.png' },
  'player-catalysis-adept': { name: 'Player Catalysis Adept', type: 'player', asset: '/static/assets/avatars/player-catalysis-adept.png' },
  'player-compound-artificer': { name: 'Player Compound Artificer', type: 'player', asset: '/static/assets/avatars/player-compound-artificer.png' },
  'player-molecular-analyst': { name: 'Player Molecular Analyst', type: 'player', asset: '/static/assets/avatars/player-molecular-analyst.png' },
  'player-research-alchemist': { name: 'Player Research Alchemist', type: 'player', asset: '/static/assets/avatars/player-research-alchemist.png' },
  'carbonyl-dragon': { name: 'Carbonyl Dragon', type: 'boss', asset: '/static/assets/avatars/carbonyl-dragon.png' },
};

export function Avatar({ character = 'organic-apprentice', state = 'idle', size = 'large', direction = 'right', className = '', label = '', config = null, asset = null, displayName = null } = {}) {
  const safeCharacter = CHARACTERS[character] ? character : 'organic-apprentice';
  const safeState = AVATAR_STATES.has(state) ? state : 'idle';
  const safeConfig = normalizeAvatarConfig(config || {});
  const node = document.createElement('div');
  node.className = `avatar ${safeCharacter} avatar-${size} state-${safeState} skin-${safeConfig.skinTone} hair-style-${safeConfig.hair.style} hair-color-${safeConfig.hair.color} glasses-${safeConfig.glasses} coat-${safeConfig.coat} shirt-${safeConfig.shirt} pants-${safeConfig.pants} shoes-${safeConfig.shoes} satchel-${safeConfig.satchel} flask-${safeConfig.flask} accessory-${safeConfig.accessory} accent-${safeConfig.accentColor} ${direction === 'left' ? 'face-left' : ''} ${className}`.trim();
  node.dataset.character = safeCharacter;
  node.dataset.state = safeState;
  node.dataset.avatarConfig = JSON.stringify(safeConfig);
  node.setAttribute('aria-label', label || CHARACTERS[safeCharacter].name);
  const imageAsset = asset || CHARACTERS[safeCharacter].asset;
  const imageName = displayName || CHARACTERS[safeCharacter].name;
  node.dataset.asset = imageAsset;
  node.innerHTML = `<div class="avatar-art-frame"><img class="avatar-art" src="${imageAsset}" alt="${imageName}" decoding="async" draggable="false"><span class="avatar-fallback" aria-hidden="true">${imageName}</span></div><div class="avatar-effects" aria-hidden="true"><span class="effect-aura"></span><span class="effect-spark spark-one"></span><span class="effect-spark spark-two"></span><span class="effect-accessory">${safeConfig.accessory === 'benzene-pin' ? '⌬' : safeConfig.accessory === 'periodic-table-badge' ? 'C' : safeConfig.accessory === 'molecule-brooch' ? '⌘' : safeConfig.accessory === 'reaction-arrow-pin' ? '↗' : safeConfig.accessory === 'chemist-gloves' ? '✦' : '◈'}</span></div>`;
  const image = node.querySelector('.avatar-art');
  image.addEventListener('error', () => {
    if (asset && !image.dataset.retry) {
      image.dataset.retry = 'true';
      image.src = `${asset}${asset.includes('?') ? '&' : '?'}retry=1`;
      return;
    }
    if (image.dataset.fallback) return;
    image.dataset.fallback = 'true';
    if (asset) {
      image.style.visibility = 'hidden';
      node.classList.add('avatar-asset-fallback');
      return;
    }
    image.src = CHARACTERS['organic-apprentice'].asset;
    node.classList.add('avatar-asset-fallback');
  });
  return node;
}

export function setAvatarState(node, state) {
  if (!node) return;
  const next = AVATAR_STATES.has(state) ? state : 'idle';
  node.className = node.className.replace(/state-[\w-]+/, `state-${next}`);
  node.dataset.state = next;
}

export function createAvatarStage() {
  const stage = document.createElement('div');
  stage.className = 'avatar-stage';
  stage.setAttribute('aria-label', 'Battle avatars');
  return stage;
}
