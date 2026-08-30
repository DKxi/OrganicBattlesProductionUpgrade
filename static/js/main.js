const $ = (selector) => document.querySelector(selector);
import { Avatar, CHARACTERS, createAvatarStage, setAvatarState, DEFAULT_AVATAR_CONFIG, PLAYER_AVATAR_OPTIONS, normalizeAvatarConfig } from './avatars.js?v=3';
import { soundEngine } from './audio.js?v=1';


let session = null;
let game = null;
let avatarStage = null;
let playerAvatar = null;
let bossAvatar = null;
let avatarConfig = normalizeAvatarConfig();
let pendingEmail = '';
let pendingUsername = '';
let selectedAvatar = null;

let adminToken = localStorage.getItem('orgo_admin_token') || null;
let adminUsersData = [];
let adminSessionsData = [];
let adminStatusData = null;
let currentAdminTab = 'users';

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

const adminApi = async (path, body = {}, method = 'POST') => {
  const headers = { 'Content-Type': 'application/json' };
  if (adminToken) {
    headers['Authorization'] = `Bearer ${adminToken}`;
  }
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers,
    body: (method === 'GET' || method === 'DELETE') && Object.keys(body).length === 0 ? undefined : JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || 'Admin action unavailable');
    error.status = response.status;
    throw error;
  }
  return data;
};

function authMessage(message, success = false) {
  const status = $('#auth-status');
  if (status) { status.textContent = message; status.className = success ? 'success' : 'error'; }
}

function showUsernameTakenModal() {
  showBattleModal({
    eyebrow: 'ORGO // IDENTITY ALERT',
    title: 'USERNAME UNAVAILABLE',
    copy: 'Username taken, choose a different one.',
    action: 'CHOOSE ANOTHER',
  });
}

function showAvatarOnboarding(existingAvatar = null) {
  $('#boot')?.classList.add('hidden'); $('#auth-screen')?.classList.add('hidden'); $('#avatar-creator')?.classList.remove('hidden');
  const returning = Boolean(existingAvatar?.character && CHARACTERS[existingAvatar.character]?.type === 'player');
  const initialAvatar = returning ? existingAvatar.character : null;
  selectedAvatar = initialAvatar;
  $('#avatar-screen-title').textContent = returning ? 'YOUR AVATAR' : 'PICK YOUR AVATAR';
  $('#avatar-screen-copy').textContent = returning ? 'You have already selected this avatar. Would you like to change it?' : 'Choose one field companion. Your selection will represent you on every battlefield.';
  renderAvatarSelection(returning, initialAvatar);
}

function renderAvatarSelection(returning = false, initialAvatar = null) {
  const gallery = $('#avatar-gallery');
  const status = $('#avatar-selection-status');
  const button = $('#accept-avatar');
  const keepButton = $('#keep-avatar');
  if (!gallery || !status || !button) return;

  const options = Object.entries(CHARACTERS).filter(([, avatar]) => avatar.type === 'player');
  if (!options.length) {
    status.textContent = 'No avatars are available right now.';
    status.className = 'avatar-selection-status error';
    button.disabled = true;
    return;
  }

  const updateButtonsAndStatus = () => {
    gallery.querySelectorAll('.avatar-choice').forEach((item) => item.classList.toggle('selected', item.dataset.avatarId === selectedAvatar));
    button.disabled = !selectedAvatar;

    if (returning && initialAvatar) {
      if (selectedAvatar === initialAvatar) {
        keepButton?.classList.add('hidden');
        button.textContent = 'CONTINUE TO BATTLEFIELD';
        status.textContent = `${CHARACTERS[selectedAvatar].name} selected. Ready to enter the battlefield.`;
      } else {
        keepButton?.classList.remove('hidden');
        if (keepButton) keepButton.textContent = 'KEEP CURRENT AVATAR';
        button.textContent = 'CHANGE AVATAR & ENTER';
        status.textContent = `Switching companion to ${CHARACTERS[selectedAvatar].name}. Click to confirm.`;
      }
    } else {
      keepButton?.classList.add('hidden');
      button.textContent = 'CONTINUE TO BATTLEFIELD';
      status.textContent = selectedAvatar
        ? `${CHARACTERS[selectedAvatar].name} selected. Ready to enter the battlefield.`
        : 'Select an avatar to continue.';
    }
    status.className = 'avatar-selection-status success';
  };

  gallery.innerHTML = options.map(([id, avatar]) => `<button type="button" class="avatar-choice" data-avatar-id="${id}" aria-label="Choose ${avatar.name}"><span class="avatar-choice-art"><img src="${avatar.asset}" alt="${avatar.name}" loading="lazy"></span><span class="avatar-choice-name">${avatar.name}</span></button>`).join('');

  gallery.querySelectorAll('.avatar-choice').forEach((choice) => {
    const image = choice.querySelector('img');
    image.addEventListener('error', () => { choice.classList.add('asset-error'); choice.disabled = true; image.remove(); status.textContent = 'One or more avatar assets could not be loaded. Try refreshing the page.'; status.className = 'avatar-selection-status error'; });
    choice.addEventListener('click', () => {
      selectedAvatar = choice.dataset.avatarId;
      updateButtonsAndStatus();
    });
  });

  updateButtonsAndStatus();
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

function showBattleModal({ eyebrow = 'ORGO // BATTLE REPORT', title, copy, action = 'CONTINUE', onDone }) {
  let modal = $('#battle-outcome-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'battle-outcome-modal';
    modal.className = 'hidden';
    modal.innerHTML = `<div class="modal-card outcome-card"><div class="eyebrow" id="outcome-eyebrow">ORGO // BATTLE REPORT</div><h2 id="outcome-title"></h2><p id="outcome-copy" class="modal-question"></p><button id="outcome-action" class="primary"></button></div>`;
    $('#app').append(modal);
  }
  const eyebrowEl = modal.querySelector('.eyebrow');
  if (eyebrowEl) eyebrowEl.textContent = eyebrow;
  $('#outcome-title').textContent = title;
  $('#outcome-copy').textContent = copy;
  const button = $('#outcome-action');
  button.textContent = action;
  button.onclick = () => {
    modal.classList.add('hidden');
    if (onDone) onDone();
  };
  modal.onclick = (event) => {
    if (event.target === modal) {
      modal.classList.add('hidden');
      if (onDone) onDone();
    }
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

let cooldownTimer = null;

function renderSpells(s) {
  const spellsContainer = $('#spells');
  if (!spellsContainer) return;
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
    cooldownTimer = null;
  }

  const orderedSpells = [...spells].sort(([leftId], [rightId]) => {
    const leftAvailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && s.spell_damage[leftId]);
    const rightAvailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && s.spell_damage[rightId]);
    return Number(rightAvailable) - Number(leftAvailable);
  });

  const remaining = { ...(s.cooldowns || {}) };

  const isDefeated = (s.player.hp <= 0);
  const isVictory = (s.boss.hp <= 0);

  const updateSpellButtons = () => {
    orderedSpells.forEach(([id, name, type, damage]) => {
      const btn = spellsContainer.querySelector(`[data-spell="${id}"]`);
      if (!btn) return;
      const cd = Math.max(0, Math.round((remaining[id] || 0) * 10) / 10);
      const unavailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && !s.spell_damage[id]);
      const activeDamage = s.spell_damage?.[id] ? `${s.spell_damage[id]} DMG` : damage;
      const meta = btn.querySelector('.spell-meta');
      if (meta) {
        meta.textContent = `${type} · ${unavailable ? 'NOT AVAILABLE' : cd > 0 ? cd.toFixed(1) + 's' : activeDamage}`;
      }
      btn.disabled = unavailable || cd > 0 || isDefeated || isVictory;
    });
  };

  spellsContainer.innerHTML = `<div class="control-panel"><div class="control-title">ARSENAL // SELECT A SPELL</div><div class="spell-grid">${orderedSpells.map(([id, name, type, damage]) => {
    const cd = Math.max(0, Math.round((remaining[id] || 0) * 10) / 10);
    const unavailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && !s.spell_damage[id]);
    const activeDamage = s.spell_damage?.[id] ? `${s.spell_damage[id]} DMG` : damage;
    return `<button class="spell" data-spell="${id}" ${cd > 0 || unavailable || isDefeated || isVictory ? 'disabled' : ''}><div class="spell-name">${name}</div><div class="spell-meta">${type} · ${unavailable ? 'NOT AVAILABLE' : cd > 0 ? cd.toFixed(1) + 's' : activeDamage}</div></button>`;
  }).join('')}</div></div>`;

  const hasCooldowns = Object.values(remaining).some((v) => v > 0);
  if (hasCooldowns && !isDefeated && !isVictory) {
    cooldownTimer = setInterval(() => {
      let anyLeft = false;
      for (const k in remaining) {
        if (remaining[k] > 0) {
          remaining[k] = Math.max(0, remaining[k] - 0.2);
          if (remaining[k] > 0) anyLeft = true;
        }
      }
      updateSpellButtons();
      if (!anyLeft) {
        clearInterval(cooldownTimer);
        cooldownTimer = null;
      }
    }, 200);
  }

  document.querySelectorAll('[data-spell]').forEach((button) => {
    button.onclick = async () => {
      if (isDefeated || isVictory) return;
      try {
        render(await api('/api/battle/select-spell', { session_id: session.session_id, spell_id: button.dataset.spell }));
      } catch (error) {
        showBattleModal({
          eyebrow: 'ORGO // ACTION BLOCKED',
          title: 'ACTION BLOCKED',
          copy: error.message,
          action: 'CONTINUE',
        });
      }
    };
  });
}


function renderQuestion(s) {
  const container = $('#question');
  if (!container) return;

  if (s.player.hp <= 0) {
    container.innerHTML = `<div class="control-panel"><div class="control-title">BATTLE STATUS // DEFEAT</div><div class="question">Your aura has faded. Regroup and retry the battle.</div><button id="retry-battle-btn" class="primary" style="margin-top:10px">RETRY BATTLE</button></div>`;
    $('#retry-battle-btn').onclick = () => api('/api/battle/retry', { session_id: session.session_id }).then(render);
    return;
  }

  if (s.boss.hp <= 0) {
    container.innerHTML = `<div class="control-panel"><div class="control-title">BATTLE STATUS // VICTORY</div><div class="question">${s.boss.name} has been defeated!</div><button id="next-turn-btn" class="primary" style="margin-top:10px">PROCEED TO NEXT ARENA</button></div>`;
    $('#next-turn-btn').onclick = () => api('/api/battle/next-turn', { session_id: session.session_id }).then((nextState) => {
      if (nextState.victory) showBattleModal({ title: 'SPECTRAL CHAMPION', copy: 'All chapters complete.', action: 'CLOSE' });
      else render(nextState);
    });
    return;
  }

  const q = s.question;
  container.innerHTML = `<div class="control-panel">${q ? `<div class="control-title">VOCABULARY TRIAL // ONE ATTEMPT</div><div class="question">${q.prompt}</div><div class="answers">${q.choices.map((answer, index) => `<button class="answer" data-answer="${answer}"><span class="hint">${'ABCD'[index]}</span><br>${answer}</button>`).join('')}</div>` : `<div class="control-title">BATTLE STATUS</div><div class="question">${s.boss.name} awaits your next spell.</div><div class="hint">Choose a spell above to reveal a chemistry trial.</div>`}</div>`;

  document.querySelectorAll('[data-answer]').forEach((button) => {
    button.onclick = async () => {
      try {
        const result = await api('/api/battle/answer', { session_id: session.session_id, answer: button.dataset.answer });
        render(result);
        showOutcome(result);
      } catch (error) {
        showBattleModal({
          eyebrow: 'ORGO // ACTION BLOCKED',
          title: 'ACTION BLOCKED',
          copy: error.message,
          action: 'CONTINUE',
        });
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

  if (r.defeat) {
    soundEngine.playDefeat();
    if (!r.correct) {
      window.lastExplanation = r;
      ensureExplanationUi();
      const headerButton = $('#view-explanation');
      if (headerButton) {
        headerButton.textContent = 'EXPLANATION';
        headerButton.classList.add('available');
      }
    }
    showBattleModal({
      title: 'DEFEAT',
      copy: `Your aura has faded. Regroup and try the battle again.${!r.correct ? ` (Correct answer: ${r.correct_answer})` : ''}`,
      action: 'RETRY BATTLE',
      onDone: () => api('/api/battle/retry', { session_id: session.session_id }).then(render),
    });
    return;
  }

  if (r.defeated) {
    soundEngine.playVictory();
    showBattleModal({
      title: 'VICTORY',
      copy: `${r.boss.name} defeated.`,
      action: 'CONTINUE',
      onDone: () => api('/api/battle/next-turn', { session_id: session.session_id }).then((nextState) => {
        if (nextState.victory) showBattleModal({ title: 'SPECTRAL CHAMPION', copy: 'All chapters complete.', action: 'CLOSE' });
        else render(nextState);
      }),
    });
    return;
  }

  if (!r.correct) {
    soundEngine.playSpellFizzle();
    setTimeout(() => soundEngine.playPlayerHit(), 300);
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

  soundEngine.playBossHit();
  if (r.boss_hit) {
    setTimeout(() => soundEngine.playPlayerHit(), 350);
  } else {
    setTimeout(() => soundEngine.playBossMiss(), 350);
  }

  showBattleModal({ title: 'DIRECT HIT', copy: msg, action: 'BACK TO BATTLE' });
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
    transparent: true,
    scale: {
      mode: Phaser.Scale.RESIZE,
      autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: {
      create() {},
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

// --- Admin Configuration Portal Logic ---

function showAdminToast(message) {
  const toast = $('#admin-feedback-toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(window._adminToastTimeout);
  window._adminToastTimeout = setTimeout(() => {
    toast.classList.add('hidden');
  }, 3500);
}

function openAdminScreen() {
  $('#admin-screen')?.classList.remove('hidden');
  if (adminToken) {
    loadAdminDashboard().catch(() => {
      adminToken = null;
      localStorage.removeItem('orgo_admin_token');
      showAdminLogin();
    });
  } else {
    showAdminLogin();
  }
}

function closeAdminScreen() {
  $('#admin-screen')?.classList.add('hidden');
}

function showAdminLogin() {
  $('#admin-login-view')?.classList.remove('hidden');
  $('#admin-dashboard-view')?.classList.add('hidden');
  const status = $('#admin-login-status');
  if (status) {
    status.textContent = '';
    status.className = '';
  }
}

async function loadAdminDashboard() {
  $('#admin-login-view')?.classList.add('hidden');
  $('#admin-dashboard-view')?.classList.remove('hidden');

  const [status, usersResp, sessionsResp] = await Promise.all([
    adminApi('/api/admin/status', {}, 'GET'),
    adminApi('/api/admin/users', {}, 'GET'),
    adminApi('/api/admin/sessions', {}, 'GET'),
  ]);

  adminStatusData = status;
  adminUsersData = usersResp.users || [];
  adminSessionsData = sessionsResp.sessions || [];

  renderAdminStatus();
  renderAdminUsers($('#admin-user-search')?.value || '');
  renderAdminSessions($('#admin-session-search')?.value || '');
}

function switchAdminTab(tabName) {
  currentAdminTab = tabName;
  const isUsers = tabName === 'users';
  $('#admin-tab-users')?.classList.toggle('active', isUsers);
  $('#admin-tab-sessions')?.classList.toggle('active', !isUsers);

  $('#admin-users-tab-content')?.classList.toggle('hidden', !isUsers);
  $('#admin-sessions-tab-content')?.classList.toggle('hidden', isUsers);
}

function renderAdminStatus() {
  const banner = $('#admin-env-status');
  if (!banner || !adminStatusData) return;

  const envVal = adminStatusData.env_content_source;
  if (envVal) {
    banner.className = 'admin-status-banner override-active';
    banner.innerHTML = `
      <span>⚡ <strong>GLOBAL .ENV OVERRIDE ACTIVE</strong>: <code>GAME_CONTENT_SOURCE="${envVal}"</code> (All users will play in <strong>${envVal.toUpperCase()}</strong> mode until .env is cleared).</span>
      <span class="status-badge active">PRIORITY 1 ACTIVE</span>
    `;
  } else {
    banner.className = 'admin-status-banner';
    banner.innerHTML = `
      <span>✔ <strong>DYNAMIC HIERARCHY ACTIVE</strong>: Individual user database settings apply. Default mode: <code>APP</code>.</span>
      <span class="status-badge normal">DATABASE CONTROL ACTIVE</span>
    `;
  }

  const stats = $('#admin-stats-summary');
  if (stats) {
    stats.textContent = `Total Users: ${adminUsersData.length} | Sessions: ${adminStatusData.total_sessions || 0}`;
  }
}

function renderAdminUsers(filterText = '') {
  const tbody = $('#admin-user-tbody');
  if (!tbody) return;

  const query = filterText.toLowerCase().trim();
  const filtered = adminUsersData.filter((u) => !query || u.username.toLowerCase().includes(query) || u.email.toLowerCase().includes(query) || u.id.toLowerCase().includes(query));

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--muted); padding: 30px;">No users found matching '${filterText}'.</td></tr>`;
    return;
  }

  const envOverride = adminStatusData?.env_content_source;

  tbody.innerHTML = filtered.map((u) => {
    const isOverride = Boolean(envOverride && envOverride !== (u.content_source || 'app'));
    const effectiveClass = u.effective_mode === 'json' ? 'mode-json' : 'mode-app';
    const effectiveLabel = isOverride ? `${u.effective_mode.toUpperCase()} (via .env)` : u.effective_mode.toUpperCase();
    const effectiveBadge = isOverride ? 'pill-effective overridden' : `pill-effective ${effectiveClass}`;

    const dbMode = u.content_source || '';

    return `
      <tr data-user-id="${u.id}">
        <td>
          <div class="user-cell-name">${u.username}</div>
          <div class="user-cell-id">${u.id.slice(0, 8)}…</div>
        </td>
        <td><span style="color: var(--muted);">${u.email}</span></td>
        <td>
          <span class="${u.verified ? 'badge-verified' : 'badge-unverified'}">
            ${u.verified ? 'VERIFIED' : 'UNVERIFIED'}
          </span>
        </td>
        <td>
          <span style="font-family: 'DM Mono', monospace; font-size: 0.72rem; color: var(--cyan);">
            Ch ${u.chapter} // Boss ${u.boss_index + 1}
          </span>
        </td>
        <td>
          <div class="mode-toggle-group">
            <button type="button" class="mode-toggle-btn ${dbMode === 'app' ? 'selected' : ''}" data-set-mode="app" title="Force App Mode for this user">APP</button>
            <button type="button" class="mode-toggle-btn ${dbMode === 'json' ? 'selected-json' : ''}" data-set-mode="json" title="Force JSON Mode for this user">JSON</button>
            <button type="button" class="mode-toggle-btn ${!dbMode ? 'selected-default' : ''}" data-set-mode="" title="Clear DB setting (use default)">DEFAULT</button>
          </div>
        </td>
        <td>
          <span class="${effectiveBadge}">${effectiveLabel}</span>
        </td>
        <td>
          <div style="display: flex; gap: 6px; align-items: center;">
            <button type="button" class="admin-save-btn" data-save-user="${u.id}">APPLY</button>
            <button type="button" class="admin-cred-btn" data-edit-cred="${u.id}" title="Edit Username or Password">🔑 CREDENTIALS</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  // Bind toggle & save buttons
  tbody.querySelectorAll('tr').forEach((row) => {
    const userId = row.dataset.userId;
    const user = adminUsersData.find((u) => u.id === userId);
    if (!user) return;

    const credBtn = row.querySelector('[data-edit-cred]');
    if (credBtn) {
      credBtn.onclick = () => openAdminCredentialsModal(user);
    }

    let selectedMode = user.content_source;

    const modeBtns = row.querySelectorAll('[data-set-mode]');
    const saveBtn = row.querySelector('[data-save-user]');


    modeBtns.forEach((btn) => {
      btn.onclick = () => {
        selectedMode = btn.dataset.setMode || null;
        modeBtns.forEach((b) => {
          b.className = 'mode-toggle-btn';
        });
        if (selectedMode === 'app') btn.className = 'mode-toggle-btn selected';
        else if (selectedMode === 'json') btn.className = 'mode-toggle-btn selected-json';
        else btn.className = 'mode-toggle-btn selected-default';
      };
    });

    saveBtn.onclick = async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = 'SAVING…';
      try {
        const resp = await adminApi(`/api/admin/users/${userId}/config`, { content_source: selectedMode }, 'POST');
        user.content_source = resp.content_source;
        user.effective_mode = resp.effective_mode;
        showAdminToast(`✓ User '${user.username}' set to ${resp.content_source ? resp.content_source.toUpperCase() : 'DEFAULT (APP)'}`);
        renderAdminUsers($('#admin-user-search')?.value || '');
      } catch (err) {
        showBattleModal({
          eyebrow: 'ADMIN // ERROR',
          title: 'CONFIG UPDATE FAILED',
          copy: err.message,
          action: 'DISMISS',
        });
        saveBtn.disabled = false;
        saveBtn.textContent = 'APPLY';
      }
    };
  });
}

function renderAdminSessions(filterText = '') {
  const tbody = $('#admin-sessions-tbody');
  if (!tbody) return;

  const query = filterText.toLowerCase().trim();
  const filtered = adminSessionsData.filter((s) => !query || s.username.toLowerCase().includes(query) || s.email.toLowerCase().includes(query) || s.boss_name.toLowerCase().includes(query) || String(s.chapter).includes(query));

  const stats = $('#admin-session-stats-summary');
  if (stats) {
    stats.textContent = `Total Active Sessions: ${adminSessionsData.length}`;
  }

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--muted); padding: 30px;">No game sessions found matching '${filterText}'.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((s) => {
    const effectiveClass = s.effective_mode === 'json' ? 'mode-json' : 'mode-app';
    const effectiveBadge = `pill-effective ${effectiveClass}`;
    const chapters = s.available_chapters || [{ id: 1, name: 'Chapter 1' }];

    const chapterOptions = chapters.map((ch) => `<option value="${ch.id}" ${ch.id === s.chapter ? 'selected' : ''}>Ch ${ch.id}: ${ch.name.slice(0, 18)}…</option>`).join('');

    return `
      <tr data-session-id="${s.session_id}">
        <td>
          <div class="user-cell-name">${s.username}</div>
          <div class="user-cell-id">${s.session_id.slice(0, 8)}…</div>
        </td>
        <td>
          <span class="${effectiveBadge}">${s.effective_mode.toUpperCase()}</span>
        </td>
        <td>
          <div style="font-weight: 600; color: var(--ink);">Ch ${s.chapter}: ${s.chapter_name}</div>
          <div style="font: 500 0.68rem 'DM Mono', monospace; color: var(--orange); margin-top: 3px;">
            Boss ${s.boss_index + 1}: ${s.boss_name}
          </div>
        </td>
        <td>
          <div class="session-hp-tag">
            <span class="hp-player">Player: ${s.player_hp}/${s.player_max_hp} HP</span>
            <span class="hp-boss">Boss: ${s.boss_hp}/${s.boss_max_hp} HP</span>
          </div>
        </td>
        <td>
          <span class="badge-verified">${s.completed_count} Defeated</span>
        </td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            <select class="admin-chapter-select" data-chapter-select>
              ${chapterOptions}
            </select>
            <button type="button" class="btn-reset" data-reset-session="${s.session_id}">⟲ RESET</button>
          </div>
        </td>
        <td>
          <button type="button" class="btn-danger" data-delete-session="${s.session_id}">🗑 DELETE</button>
        </td>
      </tr>
    `;
  }).join('');

  // Bind Reset & Delete actions
  tbody.querySelectorAll('tr').forEach((row) => {
    const sessionId = row.dataset.sessionId;
    const sessionObj = adminSessionsData.find((s) => s.session_id === sessionId);
    if (!sessionObj) return;

    const chapterSelect = row.querySelector('[data-chapter-select]');
    const resetBtn = row.querySelector('[data-reset-session]');
    const deleteBtn = row.querySelector('[data-delete-session]');

    resetBtn.onclick = async () => {
      const targetChapter = parseInt(chapterSelect.value, 10);
      resetBtn.disabled = true;
      resetBtn.textContent = 'RESETTING…';
      try {
        const resp = await adminApi(`/api/admin/sessions/${sessionId}/reset`, { chapter: targetChapter }, 'POST');
        showAdminToast(`✓ ${resp.message}`);
        await loadAdminDashboard();
      } catch (err) {
        showBattleModal({
          eyebrow: 'ADMIN // ERROR',
          title: 'SESSION RESET FAILED',
          copy: err.message,
          action: 'DISMISS',
        });
        resetBtn.disabled = false;
        resetBtn.textContent = '⟲ RESET';
      }
    };

    deleteBtn.onclick = () => {
      showBattleModal({
        eyebrow: 'ADMIN // CONFIRM DELETION',
        title: 'DELETE SESSION?',
        copy: `Are you sure you want to delete the active game session for user "${sessionObj.username}"? The user will receive a clean session upon their next login.`,
        action: 'CONFIRM DELETE',
        onDone: async () => {
          deleteBtn.disabled = true;
          deleteBtn.textContent = 'DELETING…';
          try {
            await adminApi(`/api/admin/sessions/${sessionId}`, {}, 'DELETE');
            showAdminToast(`✓ Session for "${sessionObj.username}" deleted successfully.`);
            await loadAdminDashboard();
          } catch (err) {
            showBattleModal({
              eyebrow: 'ADMIN // ERROR',
              title: 'SESSION DELETE FAILED',
              copy: err.message,
              action: 'DISMISS',
            });
            deleteBtn.disabled = false;
            deleteBtn.textContent = '🗑 DELETE';
          }
        },
      });
    };
  });
}

function openAdminCredentialsModal(user) {
  const modal = $('#admin-cred-modal');
  if (!modal) return;

  $('#admin-cred-user-id').value = user.id;
  $('#admin-cred-email').value = user.email;
  $('#admin-cred-username').value = user.username;
  $('#admin-cred-password').value = '';
  const status = $('#admin-cred-status');
  if (status) {
    status.textContent = '';
    status.className = 'admin-modal-status';
  }
  const saveBtn = $('#admin-cred-save-btn');
  if (saveBtn) {
    saveBtn.disabled = false;
    saveBtn.textContent = 'SAVE CREDENTIALS';
  }

  modal.classList.remove('hidden');
}

function closeAdminCredentialsModal() {
  $('#admin-cred-modal')?.classList.add('hidden');
}

function bindAdminEvents() {
  $('#open-admin-boot')?.addEventListener('click', openAdminScreen);
  $('#open-admin-auth')?.addEventListener('click', openAdminScreen);
  $('#open-admin-game')?.addEventListener('click', openAdminScreen);

  $('#close-admin-login')?.addEventListener('click', closeAdminScreen);
  $('#close-admin-dash')?.addEventListener('click', closeAdminScreen);

  $('#admin-cred-cancel-btn')?.addEventListener('click', closeAdminCredentialsModal);

  $('#admin-cred-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const userId = $('#admin-cred-user-id').value;
    const username = $('#admin-cred-username').value.trim();
    const password = $('#admin-cred-password').value.trim();
    const status = $('#admin-cred-status');
    const saveBtn = $('#admin-cred-save-btn');

    if (!username) {
      if (status) {
        status.textContent = 'Username cannot be empty.';
        status.className = 'admin-modal-status error';
      }
      return;
    }

    if (password && password.length < 8) {
      if (status) {
        status.textContent = 'Password must be at least 8 characters long.';
        status.className = 'admin-modal-status error';
      }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'SAVING…';
    if (status) {
      status.textContent = 'Updating user credentials…';
      status.className = 'admin-modal-status hint';
    }

    try {
      const payload = { username };
      if (password) {
        payload.password = password;
      }
      const resp = await adminApi(`/api/admin/users/${userId}/credentials`, payload, 'POST');
      const user = adminUsersData.find((u) => u.id === userId);
      if (user) {
        user.username = resp.username;
      }
      showAdminToast(`✓ ${resp.message}`);
      closeAdminCredentialsModal();
      renderAdminUsers($('#admin-user-search')?.value || '');
    } catch (err) {
      if (status) {
        status.textContent = err.message;
        status.className = 'admin-modal-status error';
      }
      saveBtn.disabled = false;
      saveBtn.textContent = 'SAVE CREDENTIALS';
    }
  });

  $('#admin-tab-users')?.addEventListener('click', () => switchAdminTab('users'));
  $('#admin-tab-sessions')?.addEventListener('click', () => switchAdminTab('sessions'));

  $('#admin-login-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const username = formData.get('admin_username');
    const password = formData.get('admin_password');
    const status = $('#admin-login-status');
    if (status) {
      status.textContent = 'Verifying admin credentials…';
      status.className = 'hint';
    }
    try {
      const data = await adminApi('/api/admin/login', { username, password }, 'POST');
      adminToken = data.token;
      localStorage.setItem('orgo_admin_token', adminToken);
      if (status) {
        status.textContent = 'Access granted.';
        status.className = 'success';
      }
      await loadAdminDashboard();
    } catch (error) {
      if (status) {
        status.textContent = error.message;
        status.className = 'error';
      }
    }
  });

  $('#admin-refresh-btn')?.addEventListener('click', () => {
    loadAdminDashboard().catch((err) => {
      showAdminToast(`Failed to refresh: ${err.message}`);
    });
  });

  $('#admin-logout-btn')?.addEventListener('click', async () => {
    try {
      await adminApi('/api/admin/logout', {}, 'POST');
    } catch (_) {}
    adminToken = null;
    localStorage.removeItem('orgo_admin_token');
    showAdminLogin();
  });

  $('#admin-user-search')?.addEventListener('input', (event) => {
    renderAdminUsers(event.target.value);
  });

  $('#admin-session-search')?.addEventListener('input', (event) => {
    renderAdminSessions(event.target.value);
  });
}


function openCreditsModal() {
  const modal = $('#credits-modal');
  const scrollContent = $('#credits-scroll-content');
  if (!modal) return;

  modal.classList.remove('hidden');

  // Reset animation to start smoothly from bottom
  if (scrollContent) {
    scrollContent.style.animation = 'none';
    void scrollContent.offsetHeight; // trigger reflow
    scrollContent.style.animation = 'movieCreditsScroll 65s linear infinite';
  }
}

function closeCreditsModal() {
  $('#credits-modal')?.classList.add('hidden');
}

function bindDomEvents() {
  const startButton = $('#start');
  if (startButton) {
    startButton.addEventListener('click', async () => {
      $('#boot')?.classList.add('hidden'); $('#auth-screen')?.classList.remove('hidden');
    });
  }

  $('#open-credits-boot')?.addEventListener('click', openCreditsModal);
  $('#close-credits-btn')?.addEventListener('click', closeCreditsModal);

  $('#credits-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'credits-modal') {
      closeCreditsModal();
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeCreditsModal();
    }
  });


  $('#keep-avatar')?.addEventListener('click', () => {
    $('#avatar-creator')?.classList.add('hidden'); $('#game-shell')?.classList.remove('hidden'); startPhaser(); render(session);
  });

  const acceptButton = $('#accept-avatar');
  if (acceptButton) {
    acceptButton.addEventListener('click', async () => {
      if (!selectedAvatar) return;
      if (session.finalized && selectedAvatar === session.avatar?.character) {
        $('#avatar-creator')?.classList.add('hidden');
        $('#game-shell')?.classList.remove('hidden');
        startPhaser();
        render(session);
        return;
      }
      acceptButton.disabled = true;
      acceptButton.textContent = 'ENTERING BATTLEFIELD…';
      try {
        const avatar = { character: selectedAvatar, body: 'arc', config: { ...DEFAULT_AVATAR_CONFIG, baseCharacter: selectedAvatar } };
        session = await api('/api/avatar/finalize', { session_id: session.session_id, ...avatar });
        playerAvatar = null;
        $('#avatar-creator')?.classList.add('hidden');
        $('#game-shell')?.classList.remove('hidden');
        startPhaser();
        render(session);
      } catch (error) {
        acceptButton.disabled = false;
        acceptButton.textContent = 'CONTINUE TO BATTLEFIELD';
        const status = $('#avatar-selection-status');
        if (status) {
          status.textContent = error.message;
          status.className = 'avatar-selection-status error';
        }
      }
    });
  }


  const muteButton = $('#mute');
  if (muteButton) {
    const updateMuteUi = () => {
      const isMuted = soundEngine.isMuted();
      muteButton.textContent = isMuted ? '🔇 AUDIO' : '🔊 AUDIO';
      muteButton.classList.toggle('muted', isMuted);
    };
    updateMuteUi();
    muteButton.addEventListener('click', () => {
      soundEngine.toggleMute();
      updateMuteUi();
    });
  }

  ensureExplanationUi();
  bindAuthEvents();
  bindAdminEvents();
}


if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bindDomEvents);
} else {
  bindDomEvents();
}

