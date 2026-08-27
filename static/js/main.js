const $ = (selector) => document.querySelector(selector);
import { Avatar, CHARACTERS, createAvatarStage, setAvatarState, DEFAULT_AVATAR_CONFIG, PLAYER_AVATAR_OPTIONS, normalizeAvatarConfig } from './avatars.js?v=3';

let session = null;
let game = null;
let avatarStage = null;
let playerAvatar = null;
let bossAvatar = null;
let avatarConfig = normalizeAvatarConfig();
let pendingEmail = '';
let pendingUsername = '';
let selectedAvatar = null;

const api = async (path, body = {}) => {
  const payload = { ...body };
  const sessionId = payload.session_id;
  delete payload.session_id;

  const url = sessionId ? `${path}?session_id=${encodeURIComponent(sessionId)}` : path;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'Action unavailable');
  }

  return response.json();
};

const authApi = async (path, body = {}, method = 'POST') => {
  const response = await fetch(path, { method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: method === 'GET' ? undefined : JSON.stringify(body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) { const error = new Error(data.detail || 'Authentication action unavailable'); error.status = response.status; throw error; }
  return data;
};

function authMessage(message, success = false) {
  const status = $('#auth-status');
  if (status) { status.textContent = message; status.className = success ? 'success' : 'error'; }
}

function showUsernameTakenModal() {
  let modal = $('#username-taken-modal');
  if (!modal) {
    modal = document.createElement('div'); modal.id = 'username-taken-modal'; modal.className = 'auth-modal';
    modal.innerHTML = '<div class="modal-card"><div class="eyebrow">ORGO // IDENTITY ALERT</div><h2>Username unavailable</h2><p>Username taken, choose a different one</p><button class="primary" id="username-taken-close">CHOOSE ANOTHER</button></div>';
    $('#app').append(modal); $('#username-taken-close').onclick = () => modal.remove();
  }
}

function showAvatarOnboarding(existingAvatar = null) {
  $('#boot')?.classList.add('hidden'); $('#auth-screen')?.classList.add('hidden'); $('#avatar-creator')?.classList.remove('hidden');
  const returning = Boolean(existingAvatar?.character && CHARACTERS[existingAvatar.character]?.type === 'player');
  selectedAvatar = returning ? existingAvatar.character : null;
  $('#avatar-screen-title').textContent = returning ? 'YOUR AVATAR' : 'PICK YOUR AVATAR';
  $('#avatar-screen-copy').textContent = returning ? 'You have already selected this avatar. Would you like to change it?' : 'Choose one field companion. Your selection will represent you on every battlefield.';
  $('#keep-avatar')?.classList.toggle('hidden', !returning);
  renderAvatarSelection(returning);
}

function renderAvatarSelection(returning = false) {
  const gallery = $('#avatar-gallery');
  const status = $('#avatar-selection-status');
  const button = $('#accept-avatar');
  if (!gallery || !status || !button) return;
  const options = Object.entries(CHARACTERS).filter(([, avatar]) => avatar.type === 'player');
  if (!options.length) { status.textContent = 'No avatars are available right now.'; status.className = 'avatar-selection-status error'; button.disabled = true; return; }
  gallery.innerHTML = options.map(([id, avatar]) => `<button type="button" class="avatar-choice" data-avatar-id="${id}" aria-label="Choose ${avatar.name}"><span class="avatar-choice-art"><img src="${avatar.asset}" alt="${avatar.name}" loading="lazy"></span><span class="avatar-choice-name">${avatar.name}</span></button>`).join('');
  gallery.querySelectorAll('.avatar-choice').forEach((choice) => {
    const image = choice.querySelector('img');
    image.addEventListener('error', () => { choice.classList.add('asset-error'); choice.disabled = true; image.remove(); status.textContent = 'One or more avatar assets could not be loaded. Try refreshing the page.'; status.className = 'avatar-selection-status error'; });
    choice.addEventListener('click', () => {
      selectedAvatar = choice.dataset.avatarId;
      gallery.querySelectorAll('.avatar-choice').forEach((item) => item.classList.toggle('selected', item === choice));
      button.disabled = false;
      status.textContent = `${CHARACTERS[selectedAvatar].name} selected. Ready to enter the battlefield.`;
      status.className = 'avatar-selection-status success';
    });
  });
  gallery.querySelectorAll('.avatar-choice').forEach((choice) => choice.classList.toggle('selected', choice.dataset.avatarId === selectedAvatar));
  button.disabled = !selectedAvatar;
  button.textContent = returning ? 'CHANGE AVATAR' : 'CONTINUE TO BATTLEFIELD';
  status.textContent = returning && selectedAvatar ? `You have already selected ${CHARACTERS[selectedAvatar].name}. Would you like to change it?` : 'Select an avatar to continue.';
  status.className = returning ? 'avatar-selection-status success' : 'avatar-selection-status';
}

async function beginVerifiedGame() {
  session = await api('/api/game/new', {});
  showAvatarOnboarding(session.finalized ? session.avatar : null);
}

function bindAuthEvents() {
  $('#show-signup')?.addEventListener('click', () => { $('#login-form')?.classList.add('hidden'); $('#signup-form')?.classList.remove('hidden'); $('#auth-title').textContent = 'CREATE YOUR ACCOUNT'; authMessage(''); });
  $('#show-login')?.addEventListener('click', () => { $('#signup-form')?.classList.add('hidden'); $('#login-form')?.classList.remove('hidden'); $('#auth-title').textContent = 'WELCOME, ALCHEMIST'; authMessage(''); });
  $('#login-form')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); authMessage('Checking your credentials…'); try { await authApi('/api/auth/login', data); await beginVerifiedGame(); } catch (error) { authMessage(error.message); } });
  $('#signup-form')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); pendingEmail = data.email; pendingUsername = data.username; authMessage('Sending your confirmation code…'); try { await authApi('/api/auth/signup', data); $('#signup-form').classList.add('hidden'); $('#verify-form').classList.remove('hidden'); $('#auth-title').textContent = 'CHECK YOUR EMAIL'; $('#auth-copy').textContent = `A 6-digit code was sent to ${pendingEmail}.`; authMessage('Code sent. It expires in 15 minutes.', true); } catch (error) { if (error.status === 409 && error.message === 'Username taken, choose a different one') showUsernameTakenModal(); else authMessage(error.message); } });
  $('#verify-form')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); authMessage('Verifying your email…'); try { await authApi('/api/auth/verify', data); authMessage('Email verified.', true); await beginVerifiedGame(); } catch (error) { authMessage(error.message); } });
  $('#resend-code')?.addEventListener('click', async () => { authMessage('Sending a fresh code…'); try { await authApi(`/api/auth/resend?email=${encodeURIComponent(pendingEmail)}`, {}, 'POST'); authMessage('A new code was sent. The previous code is no longer valid.', true); } catch (error) { authMessage(error.message); } });
  $('#logout')?.addEventListener('click', async () => { await authApi('/api/auth/logout', {}, 'POST'); window.location.reload(); });
}

const spells = [
  ['fire-spark', 'Fire Spark', 'BASIC', '20 DMG'],
  ['acid-shot', 'Acid Shot', 'BASIC', '20 DMG'],
  ['carbon-punch', 'Carbon Punch', 'BASIC', '20 DMG'],
  ['resonance-burst', 'Resonance Burst', 'MED', '30 DMG'],
  ['nucleophile-strike', 'Nucleophile Strike', 'MED', '30 DMG'],
  ['chiral-slash', 'Chiral Slash', 'MED', '30 DMG'],
  ['mechanism-storm', 'Mechanism Storm', 'STRONG', '45 DMG'],
  ['stereochemical-rift', 'Stereochemical Rift', 'STRONG', '45 DMG'],
  ['spectral-obliteration', 'Spectral Obliteration', 'STRONG', '45 DMG'],
];

function updateAvatarPreview() {
  const preview = $('.avatar-preview');
  if (!preview) return;

  let figure = preview.querySelector('.avatar-preview-art');
  if (!figure) {
    figure = Avatar({ character: 'organic-apprentice', state: 'idle', size: 'preview', config: avatarConfig });
    figure.classList.add('avatar-preview-art');
    preview.prepend(figure);
  } else {
    const replacement = Avatar({ character: 'organic-apprentice', state: 'idle', size: 'preview', config: avatarConfig });
    replacement.classList.add('avatar-preview-art');
    figure.replaceWith(replacement);
    figure = replacement;
  }

  let label = $('#avatar-preview-label');
  if (!label) {
    label = document.createElement('span');
    label.id = 'avatar-preview-label';
    preview.append(label);
  }

  label.textContent = `${avatarConfig.hair.style.toUpperCase()} // ${avatarConfig.coat.toUpperCase()} // ${avatarConfig.flask.toUpperCase()}`;
}

const optionLabels = {
  skinTones: 'Skin tone', hairStyles: 'Hair style', hairColors: 'Hair color', glasses: 'Glasses',
  coats: 'Lab coat', shirts: 'Shirt / vest', pants: 'Pants', shoes: 'Shoes', satchels: 'Satchel',
  flasks: 'Flask', accessories: 'Accessory', accents: 'Accent color',
};

const optionKeys = {
  skinTones: 'skinTone', hairStyles: 'hair.style', hairColors: 'hair.color', glasses: 'glasses',
  coats: 'coat', shirts: 'shirt', pants: 'pants', shoes: 'shoes', satchels: 'satchel',
  flasks: 'flask', accessories: 'accessory', accents: 'accentColor',
};

function readConfigValue(key) {
  return key.split('.').reduce((value, part) => value?.[part], avatarConfig);
}

function setConfigValue(key, value) {
  const parts = key.split('.');
  if (parts.length === 1) avatarConfig = normalizeAvatarConfig({ ...avatarConfig, [key]: value });
  else avatarConfig = normalizeAvatarConfig({ ...avatarConfig, [parts[0]]: { ...avatarConfig[parts[0]], [parts[1]]: value } });
}

function ensureAvatarCreatorUi() {
  const form = $('.avatar-form');
  if (!form || form.dataset.v3Ready) return;
  form.dataset.v3Ready = 'true';
  form.innerHTML = Object.entries(PLAYER_AVATAR_OPTIONS).map(([category, values]) => `<label>${optionLabels[category].toUpperCase()} <select data-avatar-option="${category}">${values.map((value) => `<option value="${value}">${value.replaceAll('-', ' ')}</option>`).join('')}</select></label>`).join('');
  form.querySelectorAll('[data-avatar-option]').forEach((select) => {
    const category = select.dataset.avatarOption;
    select.value = readConfigValue(optionKeys[category]);
    select.addEventListener('change', () => { setConfigValue(optionKeys[category], select.value); updateAvatarPreview(); });
  });

  const actions = document.createElement('div');
  actions.className = 'avatar-creator-actions';
  actions.innerHTML = '<button type="button" id="randomize-avatar" class="secondary">RANDOMIZE</button><button type="button" id="reset-avatar" class="secondary">RESET</button>';
  form.parentElement.insertBefore(actions, form.nextSibling);
  $('#randomize-avatar').onclick = () => {
    const random = (values) => values[Math.floor(Math.random() * values.length)];
    avatarConfig = normalizeAvatarConfig({
      ...avatarConfig, skinTone: random(PLAYER_AVATAR_OPTIONS.skinTones), glasses: random(PLAYER_AVATAR_OPTIONS.glasses),
      coat: random(PLAYER_AVATAR_OPTIONS.coats), shirt: random(PLAYER_AVATAR_OPTIONS.shirts), pants: random(PLAYER_AVATAR_OPTIONS.pants),
      shoes: random(PLAYER_AVATAR_OPTIONS.shoes), satchel: random(PLAYER_AVATAR_OPTIONS.satchels), flask: random(PLAYER_AVATAR_OPTIONS.flasks),
      accessory: random(PLAYER_AVATAR_OPTIONS.accessories), accentColor: random(PLAYER_AVATAR_OPTIONS.accents),
      hair: { style: random(PLAYER_AVATAR_OPTIONS.hairStyles), color: random(PLAYER_AVATAR_OPTIONS.hairColors) },
    });
    form.querySelectorAll('[data-avatar-option]').forEach((select) => { select.value = readConfigValue(optionKeys[select.dataset.avatarOption]); });
    updateAvatarPreview();
  };
  $('#reset-avatar').onclick = () => {
    avatarConfig = normalizeAvatarConfig(DEFAULT_AVATAR_CONFIG);
    form.querySelectorAll('[data-avatar-option]').forEach((select) => { select.value = readConfigValue(optionKeys[select.dataset.avatarOption]); });
    updateAvatarPreview();
  };
}

function ensureExplanationUi() {
  const brand = $('.brand');
  if (!brand) return;

  let button = $('#view-explanation');
  if (!button) {
    button = document.createElement('button');
    button.id = 'view-explanation';
    button.className = 'header-help';
    button.textContent = 'VIEW EXPLANATION';
    brand.parentElement.insertBefore(button, brand.nextSibling);
  }

  let modal = $('#explanation-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'explanation-modal';
    modal.className = 'hidden';
    modal.innerHTML = `
      <div class="modal-card">
        <button id="close-explanation" class="modal-close" aria-label="Close explanation">×</button>
        <div class="eyebrow">ORGO // CONCEPT REVIEW</div>
        <h2 id="explanation-title">WHY THIS ANSWER?</h2>
        <p id="explanation-question" class="modal-question"></p>
        <div class="modal-answer">
          <span class="hint">CORRECT ANSWER</span>
          <strong id="explanation-answer"></strong>
        </div>
        <p id="explanation-copy"></p>
        <button id="modal-done" class="primary">BACK TO BATTLE</button>
      </div>
    `;
    $('#app').append(modal);
    $('#close-explanation').onclick = closeExplanation;
    $('#modal-done').onclick = closeExplanation;
    modal.onclick = (event) => {
      if (event.target === modal) closeExplanation();
    };
  }

  button.onclick = () => {
    if (window.lastExplanation) showExplanation(window.lastExplanation);
  };
}

function closeExplanation() {
  $('#explanation-modal')?.classList.add('hidden');
}

function showExplanation(result) {
  window.lastExplanation = result;
  ensureExplanationUi();
  $('#explanation-question').textContent = result.question_prompt || 'Review the chemistry concept from the last trial.';
  $('#explanation-answer').textContent = result.correct_answer;
  $('#explanation-copy').textContent = result.explanation;
  $('#explanation-modal').classList.remove('hidden');
}

function showBattleModal({ title, copy, action = 'CONTINUE', onDone }) {
  let modal = $('#battle-outcome-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'battle-outcome-modal';
    modal.className = 'hidden';
    modal.innerHTML = `<div class="modal-card outcome-card"><div class="eyebrow">ORGO // BATTLE REPORT</div><h2 id="outcome-title"></h2><p id="outcome-copy" class="modal-question"></p><button id="outcome-action" class="primary"></button></div>`;
    $('#app').append(modal);
  }
  $('#outcome-title').textContent = title;
  $('#outcome-copy').textContent = copy;
  const button = $('#outcome-action');
  button.textContent = action;
  button.onclick = () => {
    modal.classList.add('hidden');
    if (onDone) onDone();
  };
  modal.classList.remove('hidden');
}

function render(s) {
  session = s;
  const chapterLabel = $('#chapter-label');
  if (chapterLabel) chapterLabel.textContent = `CHAPTER ${s.chapter} / ${s.chapter_name}`;

  const avatarPanel = $('#avatar-panel');
  if (avatarPanel) {
    avatarPanel.innerHTML = '';
    const card = document.createElement('div');
    card.className = 'avatar-card';
    const panelArt = Avatar({ character: s.avatar?.character || 'organic-apprentice', state: 'idle', size: 'panel', config: s.avatar?.config || s.avatar });
    panelArt.classList.add('avatar-panel-art');
    const info = document.createElement('div');
    info.innerHTML = `<div class="avatar-name"></div><div class="avatar-sub">${s.player.hp} / ${s.player.max_hp} HP</div>`;
    info.querySelector('.avatar-name').textContent = s.username || 'ALCHEMIST';
    card.append(panelArt, info);
    avatarPanel.append(card);
  }

  const log = $('#log');
  if (log) {
    log.innerHTML = s.log.map((message) => `<div class="log-line">${message}</div>`).join('');
    requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
  }

  renderSpells(s);
  renderQuestion(s);
  drawScene(s);
  renderAvatars(s);
}

function renderAvatars(s) {
  if (!avatarStage) return;
  if (!playerAvatar) {
    playerAvatar = Avatar({ character: s.avatar?.character || 'organic-apprentice', state: 'idle', size: 'player', direction: 'right', config: s.avatar?.config || s.avatar });
    bossAvatar = Avatar({ character: 'carbonyl-dragon', asset: s.boss.image ? `/static/assets/bosses/${s.boss.image}?v=2` : '/static/assets/bosses/boss-placeholder.svg?v=2', displayName: s.boss.name, state: 'idle', size: 'boss', direction: 'left' });
    avatarStage.append(playerAvatar, bossAvatar);
  } else {
    const expectedBossAsset = s.boss.image ? `/static/assets/bosses/${s.boss.image}?v=2` : '/static/assets/bosses/boss-placeholder.svg?v=2';
    if (bossAvatar.dataset.asset !== expectedBossAsset) {
      const replacement = Avatar({ character: 'carbonyl-dragon', asset: expectedBossAsset, displayName: s.boss.name, state: 'idle', size: 'boss', direction: 'left' });
      bossAvatar.replaceWith(replacement); bossAvatar = replacement;
    }
  }
  playerAvatar.querySelector('.avatar-label')?.remove();
  bossAvatar.querySelector('.avatar-label')?.remove();
  const playerLabel = document.createElement('div');
  playerLabel.className = 'avatar-label player-label';
  playerLabel.textContent = `${s.username || 'ALCHEMIST'} // ${s.player.hp} HP`;
  const bossLabel = document.createElement('div');
  bossLabel.className = 'avatar-label boss-label';
  bossLabel.textContent = `${s.boss.name} // ${s.boss.hp} HP`;
  playerAvatar.append(playerLabel);
  bossAvatar.append(bossLabel);
}

function animateBattleResult(result) {
  if (!playerAvatar || !bossAvatar) return;
  setAvatarState(playerAvatar, result.correct ? 'cast' : 'miss');
  if (result.boss_hit) setTimeout(() => setAvatarState(playerAvatar, 'hit'), 430);
  if (result.correct) setTimeout(() => setAvatarState(bossAvatar, result.defeated ? 'defeated' : 'hit'), 420);
  if (result.defeated) setTimeout(() => setAvatarState(playerAvatar, 'victory'), 760);
  setTimeout(() => {
    if (!result.defeated) setAvatarState(playerAvatar, 'idle');
    if (!result.defeated) setAvatarState(bossAvatar, 'idle');
  }, 1500);
}

function renderSpells(s) {
  const spellsContainer = $('#spells');
  if (!spellsContainer) return;

  const orderedSpells = [...spells].sort(([leftId], [rightId]) => {
    const leftAvailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && s.spell_damage[leftId]);
    const rightAvailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && s.spell_damage[rightId]);
    return Number(rightAvailable) - Number(leftAvailable);
  });
  spellsContainer.innerHTML = `<div class="control-panel"><div class="control-title">ARSENAL // SELECT A SPELL</div><div class="spell-grid">${orderedSpells.map(([id, name, type, damage]) => {
    const cooldown = s.cooldowns?.[id] || 0;
    const unavailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && !s.spell_damage[id]);
    const activeDamage = s.spell_damage?.[id] ? `${s.spell_damage[id]} DMG` : damage;
    return `<button class="spell" data-spell="${id}" ${cooldown || unavailable ? 'disabled' : ''}><div class="spell-name">${name}</div><div class="spell-meta">${type} · ${unavailable ? 'NOT AVAILABLE' : cooldown ? cooldown + 's' : activeDamage}</div></button>`;
  }).join('')}</div></div>`;

  document.querySelectorAll('[data-spell]').forEach((button) => {
    button.onclick = async () => {
      try {
        render(await api('/api/battle/select-spell', { session_id: session.session_id, spell_id: button.dataset.spell }));
      } catch (error) {
        alert(error.message);
      }
    };
  });
}

function renderQuestion(s) {
  const container = $('#question');
  if (!container) return;

  const q = s.question;
  container.innerHTML = `<div class="control-panel">${q ? `<div class="control-title">VOCABULARY TRIAL // ONE ATTEMPT</div><div class="question">${q.prompt}</div><div class="answers">${q.choices.map((answer, index) => `<button class="answer" data-answer="${answer}"><span class="hint">${'ABCD'[index]}</span><br>${answer}</button>`).join('')}</div>` : `<div class="control-title">BATTLE STATUS</div><div class="question">${s.boss.name} awaits your next spell.</div><div class="hint">Choose a spell above to reveal a chemistry trial.</div>`}</div>`;

  document.querySelectorAll('[data-answer]').forEach((button) => {
    button.onclick = async () => {
      try {
        const result = await api('/api/battle/answer', { session_id: session.session_id, answer: button.dataset.answer });
        render(result);
        showOutcome(result);
      } catch (error) {
        alert(error.message);
      }
    };
  });
}

function showOutcome(r) {
  animateBattleResult(r);
  const msg = r.defeated
    ? `VICTORY — ${r.boss.name} defeated.`
    : r.defeat
      ? 'DEFEAT — retry to regroup.'
      : r.correct
        ? `DIRECT HIT — ${r.damage} damage. ${r.boss_hit ? 'Counterattack!' : 'Boss missed!'}`
        : `SPELL FIZZLE — correct answer: ${r.correct_answer}`;

  if (!r.correct && !r.defeated) {
    window.lastExplanation = r;
    ensureExplanationUi();
    const headerButton = $('#view-explanation');
    if (headerButton) {
      headerButton.textContent = 'EXPLANATION';
      headerButton.classList.add('available');
    }
    showBattleModal({
      title: 'SPELL FIZZLE',
      copy: `The spell fizzled and backfired for ${r.self_damage} damage. Correct answer: ${r.correct_answer}`,
      action: 'VIEW EXPLANATION',
      onDone: () => showExplanation(r),
    });
    return;
  }

  if (r.defeat) {
    showBattleModal({ title: 'DEFEAT', copy: 'Your aura fades. Regroup and try the battle again.', action: 'RETRY', onDone: () => api('/api/battle/retry', { session_id: session.session_id }).then(render) });
  } else if (r.defeated) {
    showBattleModal({ title: 'VICTORY', copy: `${r.boss.name} defeated.`, action: 'CONTINUE', onDone: () => api('/api/battle/next-turn', { session_id: session.session_id }).then((nextState) => {
      if (nextState.victory) showBattleModal({ title: 'SPECTRAL CHAMPION', copy: 'All chapters complete.', action: 'CLOSE' });
      else render(nextState);
    }) });
  } else {
    showBattleModal({ title: r.correct ? 'DIRECT HIT' : 'BATTLE UPDATE', copy: msg, action: 'BACK TO BATTLE' });
  }
}

function startPhaser() {
  if (game) return;

  avatarStage = createAvatarStage();
  $('#phaser')?.append(avatarStage);

  game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: 'phaser',
    width: 900,
    height: 520,
    backgroundColor: '#0b1e2c',
    scale: {
      mode: Phaser.Scale.RESIZE,
      autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: {
      preload() {
        this.load.image('arena', '/static/assets/battle-arena.png');
      },
      create() {
        this.arena = this.add.image(this.scale.width / 2, this.scale.height / 2, 'arena').setOrigin(0.5);
        this.resizeArena();
        this.scale.on('resize', () => this.resizeArena());
      },
      resizeArena() {
        if (!this.arena) return;
        this.arena.setPosition(this.scale.width / 2, this.scale.height / 2);
        this.arena.setDisplaySize(this.scale.width, this.scale.height);
      },
    },
  });
}

function drawScene(s) {
  if (!game?.scene?.scenes?.[0]) return;

  const scene = game.scene.scenes[0];
  const width = scene.scale.width;
  const height = scene.scale.height;
  scene.children.list.filter((x) => x.getData?.('dynamic')).forEach((x) => x.destroy());

  const chapterColor = Phaser.Display.Color.HexStringToColor(s.chapter_color).color;
  scene.add.circle(width * 0.72, height * 0.48, Math.min(125, width * 0.18), chapterColor, 0.08).setStrokeStyle(2, chapterColor, 0.45).setData('dynamic', true);
}

function bindDomEvents() {
  const startButton = $('#start');
  if (startButton) {
    startButton.addEventListener('click', async () => {
      $('#boot')?.classList.add('hidden'); $('#auth-screen')?.classList.remove('hidden');
    });
  }

  $('#keep-avatar')?.addEventListener('click', () => {
    $('#avatar-creator')?.classList.add('hidden'); $('#game-shell')?.classList.remove('hidden'); startPhaser(); render(session);
  });

  const acceptButton = $('#accept-avatar');
  if (acceptButton) {
    acceptButton.addEventListener('click', async () => {
      if (!selectedAvatar) return;
      acceptButton.disabled = true; acceptButton.textContent = 'ENTERING BATTLEFIELD…';
      try {
        const avatar = { character: selectedAvatar, body: 'arc', config: { ...DEFAULT_AVATAR_CONFIG, baseCharacter: selectedAvatar } };
        session = await api('/api/avatar/finalize', { session_id: session.session_id, ...avatar });
        $('#avatar-creator')?.classList.add('hidden'); $('#game-shell')?.classList.remove('hidden'); startPhaser(); render(session);
      } catch (error) {
        acceptButton.disabled = false; acceptButton.textContent = 'CONTINUE TO BATTLEFIELD';
        const status = $('#avatar-selection-status'); if (status) { status.textContent = error.message; status.className = 'avatar-selection-status error'; }
      }
    });
  }

  ensureExplanationUi();
  bindAuthEvents();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bindDomEvents);
} else {
  bindDomEvents();
}
