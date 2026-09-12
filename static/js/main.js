const $ = (selector) => document.querySelector(selector);
import { Avatar, CHARACTERS, createAvatarStage, setAvatarState, DEFAULT_AVATAR_CONFIG, PLAYER_AVATAR_OPTIONS, normalizeAvatarConfig } from './avatars.js?v=3';
import { soundEngine } from './audio.js?v=1';

// DOM Construction & Sanitization Utilities
function sanitizeHtml(dirty) {
  if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
    return DOMPurify.sanitize(dirty);
  }
  const div = document.createElement('div');
  div.textContent = dirty;
  return div.innerHTML;
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function createEl(tag, props = {}, children = []) {
  const el = document.createElement(tag);
  for (const [key, val] of Object.entries(props)) {
    if (key === 'className') el.className = val;
    else if (key === 'dataset') Object.assign(el.dataset, val);
    else if (key === 'style' && typeof val === 'object') Object.assign(el.style, val);
    else if (key.startsWith('on') && typeof val === 'function') el.addEventListener(key.slice(2).toLowerCase(), val);
    else el.setAttribute(key, val);
  }
  const childArray = Array.isArray(children) ? children : [children];
  for (const child of childArray) {
    if (child == null) continue;
    if (typeof child === 'string' || typeof child === 'number') {
      el.appendChild(document.createTextNode(String(child)));
    } else if (child instanceof Node) {
      el.appendChild(child);
    }
  }
  return el;
}

let session = null;
let game = null;
let avatarStage = null;
let playerAvatar = null;
let bossAvatar = null;
let avatarConfig = normalizeAvatarConfig();
let pendingEmail = '';
let pendingUsername = '';
let selectedAvatar = null;

// Remove any residual admin token from localStorage
try { localStorage.removeItem('orgo_admin_token'); } catch (_) {}
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
  const headers = { 'Content-Type': 'application/json', 'X-Client-Type': 'browser' };
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers,
    body: (method === 'GET' || method === 'DELETE') && Object.keys(body).length === 0 ? undefined : JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorMsg = data.detail || (data.error && data.error.message) || data.message || `Admin action failed (HTTP ${response.status}: ${response.statusText || 'Error'})`;
    const error = new Error(errorMsg);
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
  $('#boot')?.classList.add('hidden');
  $('#auth-screen')?.classList.add('hidden');
  $('#track-screen')?.classList.add('hidden');
  $('#game-shell')?.classList.add('hidden');
  $('#avatar-creator')?.classList.remove('hidden');
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

  gallery.replaceChildren(...options.map(([id, avatar]) => {
    return createEl('button', {
      type: 'button',
      className: 'avatar-choice',
      dataset: { avatarId: id },
      'aria-label': `Choose ${avatar.name}`
    }, [
      createEl('span', { className: 'avatar-choice-art' }, [
        createEl('img', { src: avatar.asset, alt: avatar.name, loading: 'lazy' })
      ]),
      createEl('span', { className: 'avatar-choice-name' }, avatar.name)
    ]);
  }));

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
  clearExplanation();
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
  form.replaceChildren(...Object.entries(PLAYER_AVATAR_OPTIONS).map(([category, values]) => {
    const select = createEl('select', { dataset: { avatarOption: category } },
      values.map((value) => createEl('option', { value }, value.replaceAll('-', ' ')))
    );
    return createEl('label', {}, [`${optionLabels[category].toUpperCase()} `, select]);
  }));
  form.querySelectorAll('[data-avatar-option]').forEach((select) => {
    const category = select.dataset.avatarOption;
    select.value = readConfigValue(optionKeys[category]);
    select.addEventListener('change', () => { setConfigValue(optionKeys[category], select.value); updateAvatarPreview(); });
  });

  const actions = createEl('div', { className: 'avatar-creator-actions' }, [
    createEl('button', { type: 'button', id: 'randomize-avatar', className: 'secondary' }, 'RANDOMIZE'),
    createEl('button', { type: 'button', id: 'reset-avatar', className: 'secondary' }, 'RESET')
  ]);
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
  let button = $('#view-explanation');
  const gameHeader = $('#game-shell header') || $('header');
  if (!button && gameHeader) {
    button = document.createElement('button');
    button.id = 'view-explanation';
    button.className = 'header-help hidden';
    button.type = 'button';
    button.textContent = 'VIEW EXPLANATION';
    const configBtn = $('#open-admin-game');
    if (configBtn) gameHeader.insertBefore(button, configBtn);
    else gameHeader.appendChild(button);
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

  if (button) {
    button.onclick = () => {
      if (window.lastExplanation) showExplanation(window.lastExplanation);
    };
  }
}

function closeExplanation() {
  $('#explanation-modal')?.classList.add('hidden');
}

function clearExplanation() {
  window.lastExplanation = null;
  const headerButton = $('#view-explanation');
  if (headerButton) {
    headerButton.classList.add('hidden');
    headerButton.classList.remove('available');
  }
  closeExplanation();
}

function showExplanation(result) {
  if (!result) return;
  window.lastExplanation = result;
  ensureExplanationUi();
  const headerButton = $('#view-explanation');
  if (headerButton) {
    headerButton.textContent = 'VIEW EXPLANATION';
    headerButton.classList.remove('hidden');
    headerButton.classList.add('available');
  }
  const titleEl = $('#explanation-title');
  if (titleEl) {
    titleEl.textContent = result.correct ? 'WHY THIS ANSWER IS CORRECT' : 'WHY THIS ANSWER?';
  }
  $('#explanation-question').textContent = result.question_prompt || 'Review the chemistry concept from the last trial.';
  $('#explanation-answer').textContent = result.correct_answer || '';
  $('#explanation-copy').textContent = result.explanation || 'No detailed explanation provided for this question.';
  $('#explanation-modal').classList.remove('hidden');
}

function showBattleModal({ eyebrow = 'ORGO // BATTLE REPORT', title, copy, action = 'CONTINUE', secondaryAction = null, onDone, onSecondary }) {
  let modal = $('#battle-outcome-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'battle-outcome-modal';
    modal.className = 'modal-backdrop hidden';
    modal.innerHTML = `<div class="modal-card outcome-card">
      <div class="eyebrow" id="outcome-eyebrow">ORGO // BATTLE REPORT</div>
      <h2 id="outcome-title"></h2>
      <p id="outcome-copy" class="modal-question"></p>
      <div class="modal-actions" style="display:flex;gap:10px;justify-content:center;margin-top:16px;flex-wrap:wrap;">
        <button id="outcome-action" class="primary"></button>
        <button id="outcome-secondary" class="secondary hidden"></button>
      </div>
    </div>`;
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

  const secButton = $('#outcome-secondary');
  if (secButton) {
    if (secondaryAction) {
      secButton.textContent = secondaryAction;
      secButton.classList.remove('hidden');
      secButton.onclick = () => {
        modal.classList.add('hidden');
        if (onSecondary) onSecondary();
      };
    } else {
      secButton.classList.add('hidden');
      secButton.onclick = null;
    }
  }

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
    avatarPanel.replaceChildren();
    const card = document.createElement('div');
    card.className = 'avatar-card';
    const panelArt = Avatar({ character: s.avatar?.character || 'organic-apprentice', state: 'idle', size: 'panel', config: s.avatar?.config || s.avatar });
    panelArt.classList.add('avatar-panel-art');
    const info = document.createElement('div');
    const nameEl = createEl('div', { className: 'avatar-name' }, s.username || 'ALCHEMIST');
    const subEl = createEl('div', { className: 'avatar-sub' }, `${s.player.hp} / ${s.player.max_hp} HP`);
    info.append(nameEl, subEl);
    card.append(panelArt, info);
    avatarPanel.append(card);
  }

  const log = $('#log');
  if (log) {
    log.replaceChildren(...s.log.map((message) => createEl('div', { className: 'log-line' }, message)));
    requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
  }

  renderSpells(s);
  renderQuestion(s);
  drawScene(s);
  renderAvatars(s);

  if (window.lastExplanation) {
    // Invalidate stale explanations across different tracks or sessions
    if (
      (window.lastExplanation.track_id && s.track_id && window.lastExplanation.track_id !== s.track_id) ||
      (window.lastExplanation.session_id && s.session_id && window.lastExplanation.session_id !== s.session_id)
    ) {
      clearExplanation();
    } else {
      ensureExplanationUi();
      const headerButton = $('#view-explanation');
      if (headerButton) {
        headerButton.textContent = 'VIEW EXPLANATION';
        headerButton.classList.remove('hidden');
        headerButton.classList.add('available');
      }
    }
  }
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

  spellsContainer.replaceChildren(
    createEl('div', { className: 'control-panel' }, [
      createEl('div', { className: 'control-title' }, 'ARSENAL // SELECT A SPELL'),
      createEl('div', { className: 'spell-grid' }, orderedSpells.map(([id, name, type, damage]) => {
        const cd = Math.max(0, Math.round((remaining[id] || 0) * 10) / 10);
        const unavailable = Boolean(s.spell_damage && Object.keys(s.spell_damage).length && !s.spell_damage[id]);
        const activeDamage = s.spell_damage?.[id] ? `${s.spell_damage[id]} DMG` : damage;
        const isDisabled = cd > 0 || unavailable || isDefeated || isVictory;
        const btnProps = {
          className: 'spell',
          dataset: { spell: id },
        };
        if (isDisabled) btnProps.disabled = 'true';
        return createEl('button', btnProps, [
          createEl('div', { className: 'spell-name' }, name),
          createEl('div', { className: 'spell-meta' }, `${type} · ${unavailable ? 'NOT AVAILABLE' : cd > 0 ? cd.toFixed(1) + 's' : activeDamage}`)
        ]);
      }))
    ])
  );

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
    container.replaceChildren(
      createEl('div', { className: 'control-panel' }, [
        createEl('div', { className: 'control-title' }, 'BATTLE STATUS // DEFEAT'),
        createEl('div', { className: 'question' }, 'Your aura has faded. Regroup and retry the battle.'),
        createEl('button', { id: 'retry-battle-btn', className: 'primary', style: { marginTop: '10px' } }, 'RETRY BATTLE')
      ])
    );
    $('#retry-battle-btn').onclick = () => api('/api/battle/retry', { session_id: session.session_id }).then(render);
    return;
  }

  if (s.boss.hp <= 0) {
    container.replaceChildren(
      createEl('div', { className: 'control-panel' }, [
        createEl('div', { className: 'control-title' }, 'BATTLE STATUS // VICTORY'),
        createEl('div', { className: 'question' }, `${s.boss.name} has been defeated!`),
        createEl('button', { id: 'next-turn-btn', className: 'primary', style: { marginTop: '10px' } }, 'PROCEED TO NEXT ARENA')
      ])
    );
    $('#next-turn-btn').onclick = () => api('/api/battle/next-turn', { session_id: session.session_id }).then((nextState) => {
      if (nextState.victory) showBattleModal({ title: 'SPECTRAL CHAMPION', copy: 'All chapters complete.', action: 'CLOSE' });
      else render(nextState);
    });
    return;
  }

  const q = s.question;
  const trackName = (s.track_name || (() => {
    const trackId = s.track_id || (s.mode && s.mode.startsWith('track:') ? s.mode.slice(6) : (selectedTrackId || 'default'));
    const trackObj = (typeof TRACKS !== 'undefined' ? TRACKS : []).find((t) => t.id === trackId);
    return trackObj?.title || 'Chemistry Trial';
  })()).toUpperCase();

  if (q) {
    const answersContainer = createEl('div', { className: 'answers' }, q.choices.map((answer, index) => {
      const btn = createEl('button', { className: 'answer', dataset: { answer } });
      const hint = createEl('span', { className: 'hint' }, 'ABCD'[index] || '');
      btn.append(hint, document.createElement('br'), document.createTextNode(answer));
      return btn;
    }));

    container.replaceChildren(
      createEl('div', { className: 'control-panel' }, [
        createEl('div', { className: 'control-title' }, `${trackName} // ONE ATTEMPT`),
        createEl('div', { className: 'question' }, q.prompt),
        answersContainer
      ])
    );
  } else {
    container.replaceChildren(
      createEl('div', { className: 'control-panel' }, [
        createEl('div', { className: 'control-title' }, 'BATTLE STATUS'),
        createEl('div', { className: 'question' }, `${s.boss.name} awaits your next spell.`),
        createEl('div', { className: 'hint' }, 'Choose a spell above to reveal a chemistry trial.')
      ])
    );
  }

  document.querySelectorAll('#question button.answer').forEach((button) => {
    button.onclick = async () => {
      document.querySelectorAll('#question button.answer').forEach((b) => (b.disabled = true));
      try {
        const result = await api('/api/battle/answer', {
          session_id: session.session_id,
          answer: button.dataset.answer,
          turn_id: session.turn_id,
          expected_version: session.version,
        });
        render(result);
        showOutcome(result);
      } catch (error) {
        document.querySelectorAll('#question button.answer').forEach((b) => (b.disabled = false));
        showBattleModal({
          eyebrow: 'ORGO // ACTION BLOCKED',
          title: 'ACTION BLOCKED',
          copy: error.message,
          action: 'CONTINUE',
        });
        try {
          const refreshed = await api('/api/game/state', { session_id: session.session_id });
          render(refreshed);
        } catch (_) {}
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

  // Track-qualify and persist latest explanation for both correct and incorrect answers
  if (r.explanation) {
    window.lastExplanation = {
      ...r,
      session_id: session?.session_id,
      track_id: session?.track_id,
      chapter: session?.chapter,
      boss_id: session?.boss?.id,
    };
    ensureExplanationUi();
    const headerButton = $('#view-explanation');
    if (headerButton) {
      headerButton.textContent = 'VIEW EXPLANATION';
      headerButton.classList.remove('hidden');
      headerButton.classList.add('available');
    }
  }

  if (r.defeat) {
    soundEngine.playDefeat();
    showBattleModal({
      title: 'DEFEAT',
      copy: `Your aura has faded. Regroup and try the battle again.${!r.correct ? ` (Correct answer: ${r.correct_answer})` : ''}`,
      action: 'RETRY BATTLE',
      secondaryAction: r.explanation ? 'VIEW EXPLANATION' : null,
      onSecondary: () => showExplanation(window.lastExplanation || r),
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
      secondaryAction: r.explanation ? 'VIEW EXPLANATION' : null,
      onSecondary: () => showExplanation(window.lastExplanation || r),
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
    showBattleModal({
      title: 'SPELL FIZZLE',
      copy: `The spell fizzled and backfired for ${r.self_damage} damage. Correct answer: ${r.correct_answer}`,
      action: 'VIEW EXPLANATION',
      secondaryAction: 'CONTINUE BATTLE',
      onDone: () => showExplanation(window.lastExplanation || r),
      onSecondary: () => $('#battle-outcome-modal')?.classList.add('hidden'),
    });
    return;
  }

  soundEngine.playBossHit();
  if (r.boss_hit) {
    setTimeout(() => soundEngine.playPlayerHit(), 350);
  } else {
    setTimeout(() => soundEngine.playBossMiss(), 350);
  }

  showBattleModal({
    title: 'DIRECT HIT',
    copy: msg,
    action: 'BACK TO BATTLE',
    secondaryAction: r.explanation ? 'VIEW EXPLANATION' : null,
    onSecondary: () => showExplanation(window.lastExplanation || r),
  });
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
  loadAdminDashboard().catch(() => {
    showAdminLogin();
  });
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
  $('#admin-screen')?.scrollTo({ top: 0, behavior: 'instant' });

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
  if (currentAdminTab === 'storage') {
    loadStorageConfig();
  } else if (currentAdminTab === 'system') {
    loadLoggingConfig();
    loadRuntimeProfile();
  } else if (currentAdminTab === 'questions') {
    loadQuestionBank();
  } else if (currentAdminTab === 'releases') {
    loadReleasesTab();
  } else if (currentAdminTab === 'observability') {
    loadObservabilityMetrics();
  } else if (currentAdminTab === 'analytics') {
    loadLearningAnalytics();
  }
}

let adminObsInterval = null;
let qbCurrentTrack = 'default';
let qbCurrentPage = 1;
let qbTotalPages = 1;
let adminTracksList = [];

function switchAdminTab(tabName) {
  currentAdminTab = tabName;
  if (adminObsInterval) {
    clearInterval(adminObsInterval);
    adminObsInterval = null;
  }

  const allTabs = ['users', 'sessions', 'questions', 'releases', 'observability', 'analytics', 'storage', 'system'];
  allTabs.forEach((t) => {
    $(`#admin-tab-${t}`)?.classList.toggle('active', t === tabName);
    $(`#admin-${t}-tab-content`)?.classList.toggle('hidden', t !== tabName);
  });

  const activeContent = $(`#admin-${tabName}-tab-content`);
  if (activeContent) {
    activeContent.scrollTop = 0;
  }
  $('#admin-screen')?.scrollTo({ top: 0, behavior: 'instant' });

  if (tabName === 'questions') {
    loadQuestionBank();
  } else if (tabName === 'releases') {
    loadReleasesTab();
  } else if (tabName === 'observability') {
    loadObservabilityMetrics();
    setupObsAutoRefresh();
  } else if (tabName === 'analytics') {
    loadLearningAnalytics();
  } else if (tabName === 'storage') {
    loadStorageConfig();
  } else if (tabName === 'system') {
    loadLoggingConfig();
    loadRuntimeProfile();
  }
}

async function ensureTracksLoaded() {
  if (adminTracksList.length > 0) return adminTracksList;
  try {
    const res = await adminApi('/api/admin/tracks', {}, 'GET');
    if (res && res.tracks) {
      adminTracksList = res.tracks;
      populateTrackSelects();
    }
  } catch (err) {
    console.error('Failed to load tracks list:', err);
  }
  return adminTracksList;
}

function populateTrackSelects() {
  const qbSelect = $('#admin-qb-track-select');
  const relSelect = $('#admin-releases-track-select');
  const ingSelect = $('#admin-ingest-track-select');
  const anaSelect = $('#admin-analytics-track-select');

  const createOptions = () => adminTracksList.map(t => createEl('option', { value: t.id }, t.title || t.id.toUpperCase()));

  if (qbSelect && !qbSelect.options.length) {
    qbSelect.replaceChildren(...createOptions());
    qbSelect.value = qbCurrentTrack;
  }
  if (relSelect && !relSelect.options.length) {
    relSelect.replaceChildren(...createOptions());
  }
  if (ingSelect && ingSelect.options.length <= 1) {
    ingSelect.replaceChildren(createEl('option', { value: '' }, 'All Registered Tracks'), ...createOptions());
  }
  if (anaSelect && anaSelect.options.length <= 1) {
    anaSelect.replaceChildren(createEl('option', { value: '' }, 'All Tracks'), ...createOptions());
  }
}

async function loadQuestionBank() {
  await ensureTracksLoaded();
  const trackId = $('#admin-qb-track-select')?.value || qbCurrentTrack;
  qbCurrentTrack = trackId;
  const chapter = $('#admin-qb-chapter-select')?.value || '';
  const diff = $('#admin-qb-difficulty-select')?.value || '';
  const search = $('#admin-qb-search-input')?.value.trim() || '';

  const params = new URLSearchParams({
    page: String(qbCurrentPage),
    limit: '20',
  });
  if (chapter) params.append('chapter', chapter);
  if (diff) params.append('difficulty', diff);
  if (search) params.append('search', search);

  const tbody = $('#admin-qb-tbody');
  if (tbody) {
    tbody.replaceChildren(
      createEl('tr', {}, [
        createEl('td', { colspan: '7', style: { textAlign: 'center', color: 'var(--muted)', padding: '30px' } }, 'Loading questions…')
      ])
    );
  }

  try {
    const res = await adminApi(`/api/admin/tracks/${trackId}/questions?${params.toString()}`, {}, 'GET');
    if (!res) return;

    qbTotalPages = res.pages || 1;
    const stats = $('#admin-qb-stats-summary');
    if (stats) stats.textContent = `${res.total} questions (Page ${res.page} of ${qbTotalPages})`;

    const pageInfo = $('#admin-qb-page-info');
    if (pageInfo) pageInfo.textContent = `Page ${res.page} of ${qbTotalPages}`;

    const prevBtn = $('#admin-qb-prev-btn');
    if (prevBtn) prevBtn.disabled = res.page <= 1;
    const nextBtn = $('#admin-qb-next-btn');
    if (nextBtn) nextBtn.disabled = res.page >= qbTotalPages;

    renderQuestionBankRows(res.items || [], trackId);
  } catch (err) {
    if (tbody) {
      tbody.replaceChildren(
        createEl('tr', {}, [
          createEl('td', { colspan: '7', style: { textAlign: 'center', color: '#ff8e88', padding: '30px' } }, `Error loading questions: ${err.message}`)
        ])
      );
    }
  }
}

function renderQuestionBankRows(items, trackId) {
  const tbody = $('#admin-qb-tbody');
  if (!tbody) return;

  if (!items.length) {
    tbody.replaceChildren(
      createEl('tr', {}, [
        createEl('td', { colspan: '7', style: { textAlign: 'center', color: 'var(--muted)', padding: '30px' } }, 'No questions found.')
      ])
    );
    return;
  }

  tbody.replaceChildren(...items.map((q) => {
    const diffClass = q.difficulty === 'challenge' ? 'diff-challenge' : q.difficulty === 'intro' ? 'diff-intro' : 'diff-standard';
    const promptShort = q.prompt.length > 85 ? q.prompt.slice(0, 85) + '…' : q.prompt;
    const spellsText = (q.spells && q.spells.length) ? q.spells.join(', ') : '20, 30, 45';

    return createEl('tr', { dataset: { questionId: String(q.id) } }, [
      createEl('td', { style: { fontFamily: "'DM Mono', monospace", fontWeight: '700', color: 'var(--cyan)' } }, String(q.order_index)),
      createEl('td', {}, [
        createEl('div', { style: { fontWeight: '600', color: 'var(--ink)' } }, `Ch ${q.chapter}: ${q.chapter_title || ''}`),
        createEl('div', { style: { font: "500 0.68rem 'DM Mono', monospace", color: 'var(--orange)', marginTop: '2px' } }, `Boss: ${q.boss_name || q.boss_slug || ''}`)
      ]),
      createEl('td', {}, [
        createEl('div', { style: { fontSize: '0.8rem', color: 'var(--ink)', lineHeight: '1.35' } }, promptShort),
        createEl('div', { style: { font: "500 0.68rem 'DM Mono', monospace", color: 'var(--muted)', marginTop: '3px' } }, [
          'Ans: ',
          createEl('strong', {}, String(q.correct_option)),
          ` (${q.correct_answer || ''})`
        ])
      ]),
      createEl('td', {}, [
        createEl('span', { style: { fontFamily: "'DM Mono', monospace", fontSize: '0.72rem', color: 'var(--muted)' } }, q.topic || 'General')
      ]),
      createEl('td', {}, [
        createEl('span', { className: `badge-difficulty ${diffClass}` }, (q.difficulty || 'standard').toUpperCase())
      ]),
      createEl('td', {}, [
        createEl('span', { style: { fontFamily: "'DM Mono', monospace", fontSize: '0.72rem', color: 'var(--cyan)' } }, spellsText)
      ]),
      createEl('td', {}, [
        createEl('div', { style: { display: 'flex', gap: '6px', alignItems: 'center' } }, [
          createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { editQuestion: String(q.id) } }, '✏ EDIT'),
          createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { reorderUp: String(q.id), chapter: String(q.chapter), boss: q.boss_slug || '' }, title: 'Move Up' }, '▲'),
          createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { reorderDown: String(q.id), chapter: String(q.chapter), boss: q.boss_slug || '' }, title: 'Move Down' }, '▼')
        ])
      ])
    ]);
  }));

  tbody.querySelectorAll('[data-edit-question]').forEach((btn) => {
    btn.onclick = () => openQuestionEditor(btn.dataset.editQuestion, trackId);
  });

  tbody.querySelectorAll('[data-reorder-up]').forEach((btn) => {
    btn.onclick = () => handleQuestionReorder(trackId, parseInt(btn.dataset.chapter, 10), btn.dataset.boss, parseInt(btn.dataset.reorderUp, 10), 'up');
  });

  tbody.querySelectorAll('[data-reorder-down]').forEach((btn) => {
    btn.onclick = () => handleQuestionReorder(trackId, parseInt(btn.dataset.chapter, 10), btn.dataset.boss, parseInt(btn.dataset.reorderDown, 10), 'down');
  });
}

async function handleQuestionReorder(trackId, chapter, bossSlug, qId, direction) {
  try {
    const params = new URLSearchParams({ chapter: String(chapter), limit: '100' });
    if (bossSlug) params.append('boss_slug', bossSlug);
    const res = await adminApi(`/api/admin/tracks/${trackId}/questions?${params.toString()}`, {}, 'GET');
    if (!res || !res.items || res.items.length < 2) {
      showAdminToast('Not enough questions to reorder.');
      return;
    }

    const ids = res.items.map(q => q.id);
    const currentIdx = ids.indexOf(qId);
    if (currentIdx === -1) return;

    let targetIdx = direction === 'up' ? currentIdx - 1 : currentIdx + 1;
    if (targetIdx < 0 || targetIdx >= ids.length) {
      showAdminToast(`Already at the ${direction === 'up' ? 'top' : 'bottom'} of this group.`);
      return;
    }

    const targetId = ids[targetIdx];
    const position = direction === 'up' ? 'before' : 'after';

    const url = bossSlug
      ? `/api/admin/tracks/${trackId}/chapters/${chapter}/bosses/${bossSlug}/reorder`
      : `/api/admin/tracks/${trackId}/chapters/${chapter}/reorder`;

    await adminApi(url, {
      move_question_id: qId,
      target_question_id: targetId,
      position: position,
    }, 'POST');

    showAdminToast(`✓ Question moved ${direction}`);
    loadQuestionBank();
  } catch (err) {
    showAdminToast(`Reorder failed: ${err.message}`);
  }
}

async function openQuestionEditor(questionId, trackId) {
  const modal = $('#admin-question-editor-modal');
  if (!modal) return;

  const status = $('#admin-qe-status');
  if (status) { status.textContent = 'Loading question details…'; status.className = 'admin-modal-status hint'; }
  modal.classList.remove('hidden');

  try {
    const q = await adminApi(`/api/admin/questions/${questionId}`, {}, 'GET');
    if (!q) return;

    $('#admin-qe-question-id').value = q.id;
    $('#admin-qe-track-id').value = q.track_id || trackId || 'default';
    $('#admin-qe-topic').value = q.topic || '';
    $('#admin-qe-difficulty').value = q.difficulty || 'standard';
    $('#admin-qe-prompt').value = q.prompt || '';
    $('#admin-qe-explanation').value = q.explanation || '';
    $('#admin-qe-spells').value = (q.spells || [20, 30, 45]).join(', ');
    $('#admin-qe-health').value = (q.health || [100]).join(', ');

    const opts = q.options || [];
    const getOptText = (label) => {
      const found = opts.find(o => (o.label || '').toUpperCase() === label);
      return found ? found.text : '';
    };

    $('#admin-qe-opt-a').value = getOptText('A');
    $('#admin-qe-opt-b').value = getOptText('B');
    $('#admin-qe-opt-c').value = getOptText('C');
    $('#admin-qe-opt-d').value = getOptText('D');

    const correct = (q.correct_option || 'A').toUpperCase();
    const radio = document.querySelector(`input[name="qe_correct_option"][value="${correct}"]`);
    if (radio) radio.checked = true;

    if (status) { status.textContent = ''; status.className = 'admin-modal-status'; }
  } catch (err) {
    if (status) { status.textContent = `Failed to load: ${err.message}`; status.className = 'admin-modal-status error'; }
  }
}

function closeQuestionEditor() {
  $('#admin-question-editor-modal')?.classList.add('hidden');
}

async function loadReleasesTab() {
  await ensureTracksLoaded();
  const trackId = $('#admin-releases-track-select')?.value || qbCurrentTrack;
  const tbody = $('#admin-releases-tbody');

  if (tbody) {
    tbody.replaceChildren(
      createEl('tr', {}, [
        createEl('td', { colspan: '5', style: { textAlign: 'center', color: 'var(--muted)', padding: '20px' } }, 'Loading releases…')
      ])
    );
  }

  try {
    const res = await adminApi(`/api/admin/tracks/${trackId}/releases`, {}, 'GET');
    if (!res || !res.releases) return;

    if (!res.releases.length) {
      tbody.replaceChildren(
        createEl('tr', {}, [
          createEl('td', { colspan: '5', style: { textAlign: 'center', color: 'var(--muted)', padding: '20px' } }, `No releases found for track "${trackId}".`)
        ])
      );
      return;
    }

    tbody.replaceChildren(...res.releases.map((r) => {
      const isPub = r.status === 'published';
      const badgeClass = isPub ? 'badge-published' : r.status === 'draft' ? 'badge-draft' : 'badge-archived';
      const checksumShort = r.checksum ? r.checksum.slice(0, 10) + '…' : '--';
      const pubDate = r.published_at ? new Date(r.published_at * 1000).toLocaleString() : '--';

      return createEl('tr', {}, [
        createEl('td', { style: { fontFamily: "'DM Mono', monospace", fontWeight: '700', color: 'var(--cyan)' } }, `v${r.version}`),
        createEl('td', {}, [
          createEl('span', { className: `badge-status ${badgeClass}` }, r.status)
        ]),
        createEl('td', {}, [
          createEl('span', { style: { fontFamily: 'monospace', fontSize: '0.72rem', color: 'var(--muted)' } }, checksumShort)
        ]),
        createEl('td', {}, [
          createEl('span', { style: { fontSize: '0.72rem', color: 'var(--muted)' } }, pubDate)
        ]),
        createEl('td', {}, [
          !isPub
            ? createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { rollbackVersion: String(r.version), track: trackId } }, 'ROLLBACK')
            : createEl('span', { style: { fontSize: '0.7rem', color: '#34d399', fontWeight: '600' } }, 'ACTIVE')
        ])
      ]);
    }));

    tbody.querySelectorAll('[data-rollback-version]').forEach((btn) => {
      btn.onclick = async () => {
        const ver = btn.dataset.rollbackVersion;
        const trk = btn.dataset.track;
        btn.disabled = true;
        btn.textContent = 'REVERTING…';
        try {
          const result = await adminApi(`/api/admin/tracks/${trk}/releases/${ver}/rollback`, {}, 'POST');
          showAdminToast(`✓ ${result.message}`);
          loadReleasesTab();
        } catch (err) {
          showAdminToast(`Rollback failed: ${err.message}`);
          btn.disabled = false;
          btn.textContent = 'ROLLBACK';
        }
      };
    });
  } catch (err) {
    if (tbody) {
      tbody.replaceChildren(
        createEl('tr', {}, [
          createEl('td', { colspan: '5', style: { textAlign: 'center', color: '#ff8e88', padding: '20px' } }, `Error: ${err.message}`)
        ])
      );
    }
  }
}

async function loadObservabilityMetrics() {
  try {
    const [metrics, config] = await Promise.all([
      adminApi('/api/admin/system/metrics', {}, 'GET'),
      adminApi('/api/admin/system/config', {}, 'GET'),
    ]);
    if (!metrics) return;

    // 1. Query Latency
    const ql = metrics.database_query_latency || {};
    const qlVal = $('#kpi-val-query-latency');
    if (qlVal) qlVal.textContent = `${ql.avg_duration_ms || 0} ms`;
    const qlSub = $('#kpi-sub-query-latency');
    if (qlSub) qlSub.textContent = `Avg: ${ql.avg_duration_ms || 0} ms | Max: ${ql.max_duration_ms || 0} ms`;

    // 2. Pool Utilization
    const pool = config?.database_pool || {};
    const poolVal = $('#kpi-val-pool-utilization');
    if (poolVal) poolVal.textContent = `${pool.checked_out || 0} / ${pool.pool_size || 5}`;
    const poolSub = $('#kpi-sub-pool-utilization');
    if (poolSub) poolSub.textContent = `Overflow: ${pool.overflow || 0} / ${pool.max_overflow || 10}`;

    // 3. Track Load Time
    const tl = metrics.track_bundle_load_time || {};
    const tlVal = $('#kpi-val-track-load');
    if (tlVal) tlVal.textContent = `${tl.avg_duration_ms || 0} ms`;

    // 4. Cache Hit Ratio
    const cache = config?.track_cache || {};
    const ratio = Math.round((cache.hit_ratio || 0) * 100);
    const crVal = $('#kpi-val-cache-ratio');
    if (crVal) crVal.textContent = `${ratio}%`;
    const crSub = $('#kpi-sub-cache-ratio');
    if (crSub) crSub.textContent = `Hits: ${cache.hits || 0} | Misses: ${cache.misses || 0}`;

    // 5. Cache Memory
    const cm = metrics.cache_memory_consumption || {};
    const cmVal = $('#kpi-val-cache-memory');
    if (cmVal) cmVal.textContent = `${cm.total_bundle_memory_kb || 0} KB`;

    // 6. JSON Fallbacks
    const jf = metrics.json_fallback_count || 0;
    const jfVal = $('#kpi-val-json-fallbacks');
    if (jfVal) jfVal.textContent = jf;
    $('#kpi-json-fallbacks')?.classList.toggle('alert', jf > 0);

    // 7. Ingestion Failures
    const ivf = metrics.ingestion_validation_failures || 0;
    const ivfVal = $('#kpi-val-ingestion-failures');
    if (ivfVal) ivfVal.textContent = ivf;
    $('#kpi-ingestion-failures')?.classList.toggle('alert', ivf > 0);

    // 8. Version Mismatches
    const cvm = metrics.content_version_mismatches || 0;
    const cvmVal = $('#kpi-val-version-mismatches');
    if (cvmVal) cvmVal.textContent = cvm;
    $('#kpi-version-mismatches')?.classList.toggle('alert', cvm > 0);

    // 9. Combat Conflicts
    const ccu = metrics.concurrent_combat_update_conflicts || 0;
    const ccuVal = $('#kpi-val-combat-conflicts');
    if (ccuVal) ccuVal.textContent = ccu;
    $('#kpi-combat-conflicts')?.classList.toggle('alert', ccu > 0);

    // Runtime profile banner
    if (config?.runtime_environment) {
      const re = config.runtime_environment;
      if ($('#runtime-env-mode')) $('#runtime-env-mode').textContent = (re.environment || 'development').toUpperCase();
      if ($('#runtime-env-file')) $('#runtime-env-file').textContent = re.loaded_env_file || '--';
      if ($('#runtime-env-debug')) $('#runtime-env-debug').textContent = re.debug ? 'Active (Verbose)' : 'Disabled (Prod)';
      if ($('#runtime-env-cookie')) $('#runtime-env-cookie').textContent = re.cookie_secure ? 'Strict HTTPS' : 'Lax (HTTP Dev)';
      if ($('#runtime-env-fallback')) $('#runtime-env-fallback').textContent = re.allow_json_fallback ? 'Permitted' : 'Strict DB Only';
      if ($('#runtime-env-cluster')) $('#runtime-env-cluster').textContent = `${re.max_cluster_connections} conns (limit: ${re.db_max_connections_limit})`;
    }
  } catch (err) {
    console.error('Failed to load observability metrics:', err);
  }
}

function setupObsAutoRefresh() {
  if (adminObsInterval) clearInterval(adminObsInterval);
  const select = $('#admin-obs-autorefresh');
  const ms = select ? parseInt(select.value, 10) : 15000;
  if (ms > 0) {
    adminObsInterval = setInterval(() => {
      if (currentAdminTab === 'observability') {
        loadObservabilityMetrics();
      }
    }, ms);
  }
}

async function loadRuntimeProfile() {
  try {
    const config = await adminApi('/api/admin/system/config', {}, 'GET');
    if (config?.runtime_environment) {
      const re = config.runtime_environment;
      if ($('#runtime-env-mode')) $('#runtime-env-mode').textContent = (re.environment || 'development').toUpperCase();
      if ($('#runtime-env-file')) $('#runtime-env-file').textContent = re.loaded_env_file || '--';
      if ($('#runtime-env-debug')) $('#runtime-env-debug').textContent = re.debug ? 'Active (Verbose)' : 'Disabled (Prod)';
      if ($('#runtime-env-cookie')) $('#runtime-env-cookie').textContent = re.cookie_secure ? 'Strict HTTPS' : 'Lax (HTTP Dev)';
      if ($('#runtime-env-fallback')) $('#runtime-env-fallback').textContent = re.allow_json_fallback ? 'Permitted' : 'Strict DB Only';
      if ($('#runtime-env-cluster')) $('#runtime-env-cluster').textContent = `${re.max_cluster_connections} conns (limit: ${re.db_max_connections_limit})`;
    }
  } catch (err) {
    console.error('Failed to load runtime profile:', err);
  }
}

async function loadLearningAnalytics() {
  await ensureTracksLoaded();
  const trackId = $('#admin-analytics-track-select')?.value || '';
  const url = trackId ? `/api/admin/analytics/overview?track_id=${trackId}` : '/api/admin/analytics/overview';

  try {
    const res = await adminApi(url, {}, 'GET');
    if (!res) return;

    if ($('#analytics-total-attempts')) $('#analytics-total-attempts').textContent = res.total_attempts || 0;
    if ($('#analytics-cohort-accuracy')) $('#analytics-cohort-accuracy').textContent = `${Math.round((res.overall_accuracy || 0) * 100)}%`;
    if ($('#analytics-correct-attempts')) $('#analytics-correct-attempts').textContent = `${res.correct_attempts || 0} correct attempts`;
    if ($('#analytics-unique-players')) $('#analytics-unique-players').textContent = res.unique_players || 0;

    const tbody = $('#admin-analytics-struggling-tbody');
    if (!tbody) return;

    const questions = res.struggling_questions || [];
    if (!questions.length) {
      tbody.replaceChildren(
        createEl('tr', {}, [
          createEl('td', { colspan: '6', style: { textAlign: 'center', color: 'var(--muted)', padding: '24px' } }, 'No struggling questions found (all questions ≥ 70% accuracy).')
        ])
      );
      return;
    }

    tbody.replaceChildren(...questions.map((q) => {
      const accPercent = Math.round((q.accuracy || 0) * 100);
      return createEl('tr', {}, [
        createEl('td', { style: { fontFamily: "'DM Mono', monospace", fontWeight: '700', color: 'var(--cyan)' } }, String(q.question_id)),
        createEl('td', { style: { fontSize: '0.8rem', lineHeight: '1.35', color: 'var(--ink)' } }, q.prompt),
        createEl('td', {}, [
          createEl('span', { style: { fontFamily: "'DM Mono', monospace", fontSize: '0.72rem', color: 'var(--muted)' } }, q.topic || 'General')
        ]),
        createEl('td', { style: { fontFamily: "'DM Mono', monospace", fontSize: '0.75rem' } }, String(q.total_attempts)),
        createEl('td', {}, [
          createEl('span', { style: { fontWeight: '700', fontFamily: "'DM Mono', monospace", color: '#ff8e88' } }, `${accPercent}%`)
        ]),
        createEl('td', {}, [
          createEl('div', { style: { display: 'flex', gap: '6px' } }, [
            createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { inspectDistractors: String(q.question_id) } }, 'DISTRACTORS'),
            createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { editInBank: String(q.question_id) } }, 'EDIT')
          ])
        ])
      ]);
    }));

    tbody.querySelectorAll('[data-inspect-distractors]').forEach((btn) => {
      btn.onclick = () => openDistractorAnalytics(btn.dataset.inspectDistractors);
    });

    tbody.querySelectorAll('[data-edit-in-bank]').forEach((btn) => {
      btn.onclick = () => {
        switchAdminTab('questions');
        openQuestionEditor(btn.dataset.editInBank);
      };
    });
  } catch (err) {
    console.error('Failed to load learning analytics:', err);
  }
}

async function openDistractorAnalytics(questionId) {
  const modal = $('#admin-question-analytics-modal');
  if (!modal) return;

  try {
    const res = await adminApi(`/api/admin/analytics/questions/${questionId}`, {}, 'GET');
    if (!res) return;

    if ($('#admin-qa-prompt')) $('#admin-qa-prompt').textContent = res.prompt || '';
    if ($('#admin-qa-attempts')) $('#admin-qa-attempts').textContent = res.total_attempts || 0;
    if ($('#admin-qa-accuracy')) $('#admin-qa-accuracy').textContent = `${Math.round((res.accuracy || 0) * 100)}%`;
    if ($('#admin-qa-correct')) $('#admin-qa-correct').textContent = `${res.correct_option} (${res.correct_answer || ''})`;

    const container = $('#admin-qa-distractor-bars');
    if (container) {
      const dist = res.option_distribution || {};
      const total = res.total_attempts || 1;
      const opts = ['A', 'B', 'C', 'D'];

      container.replaceChildren(...opts.map((opt) => {
        const count = dist[opt] || 0;
        const pct = Math.round((count / total) * 100);
        const isCorr = opt === (res.correct_option || '').toUpperCase();
        const barClass = isCorr ? 'distractor-correct' : 'distractor-wrong';

        const labelLeftChildren = [createEl('strong', {}, `Option ${opt}`)];
        if (isCorr) {
          labelLeftChildren.push(document.createTextNode(' '));
          labelLeftChildren.push(createEl('span', { style: { color: '#34d399' } }, '(Correct)'));
        }

        return createEl('div', { className: 'distractor-row' }, [
          createEl('div', { className: 'distractor-label' }, [
            createEl('span', {}, labelLeftChildren),
            createEl('span', {}, `${count} picks (${pct}%)`)
          ]),
          createEl('div', { className: 'distractor-bar-container' }, [
            createEl('div', { className: `distractor-bar-fill ${barClass}`, style: { width: `${pct}%` } })
          ])
        ]);
      }));
    }

    modal.classList.remove('hidden');
  } catch (err) {
    showAdminToast(`Failed to load distractor data: ${err.message}`);
  }
}

function closeDistractorAnalytics() {
  $('#admin-question-analytics-modal')?.classList.add('hidden');
}

async function openUserMasteryModal(userId, username) {
  const modal = $('#admin-user-mastery-modal');
  if (!modal) return;

  if ($('#admin-um-username')) $('#admin-um-username').textContent = `MASTERY: ${username}`;
  if ($('#admin-um-id')) $('#admin-um-id').textContent = `User ID: ${userId}`;

  try {
    const res = await adminApi(`/api/admin/analytics/users/${userId}/mastery`, {}, 'GET');
    const s = res?.summary || {};

    if ($('#admin-um-total')) $('#admin-um-total').textContent = s.total_tracked_questions || 0;
    if ($('#admin-um-mastered')) $('#admin-um-mastered').textContent = s.mastered_count || 0;
    if ($('#admin-um-accuracy')) $('#admin-um-accuracy').textContent = `${Math.round((s.overall_accuracy || 0) * 100)}%`;

    modal.classList.remove('hidden');
  } catch (err) {
    showAdminToast(`Failed to load mastery data: ${err.message}`);
  }
}

function closeUserMasteryModal() {
  $('#admin-user-mastery-modal')?.classList.add('hidden');
}

function openSessionInspectModal(sessionObj) {
  const modal = $('#admin-session-inspect-modal');
  if (!modal) return;

  if ($('#admin-si-user')) $('#admin-si-user').textContent = `SESSION: ${sessionObj.username} (${sessionObj.track_name || sessionObj.track_id})`;
  if ($('#admin-si-id')) $('#admin-si-id').textContent = `ID: ${sessionObj.session_id}`;
  if ($('#admin-si-turn')) $('#admin-si-turn').textContent = sessionObj.turn_id || 'None (No active question pending)';
  if ($('#admin-si-version')) $('#admin-si-version').textContent = `v${sessionObj.version || 1}`;

  const logEl = $('#admin-si-log');
  if (logEl) {
    logEl.textContent = (sessionObj.log && sessionObj.log.length) ? sessionObj.log.join('\n') : '[No events recorded]';
  }

  const cdEl = $('#admin-si-cooldowns');
  if (cdEl) {
    cdEl.textContent = JSON.stringify(sessionObj.cooldowns || {}, null, 2);
  }

  modal.classList.remove('hidden');
}

function closeSessionInspectModal() {
  $('#admin-session-inspect-modal')?.classList.add('hidden');
}

async function toggleUserVerification(userId) {
  try {
    const res = await adminApi(`/api/admin/users/${userId}/verify`, {}, 'POST');
    showAdminToast(`✓ ${res.message}`);
    const user = adminUsersData.find(u => u.id === userId);
    if (user) user.verified = res.verified ? 1 : 0;
    renderAdminUsers($('#admin-user-search')?.value || '');
  } catch (err) {
    showAdminToast(`Verification update failed: ${err.message}`);
  }
}

async function loadStorageConfig() {
  try {
    const res = await adminApi('/api/admin/system/config', {}, 'GET');
    if (!res) return;

    // Set Database Radio & URI
    const isPg = res.active_database.dialect === 'postgresql';
    const radio = document.querySelector(`input[name="db_dialect"][value="${res.active_database.dialect}"]`);
    if (radio) radio.checked = true;
    const uriInput = $('#admin-db-uri-input');
    if (uriInput) {
      uriInput.value = isPg ? res.active_database.url : '';
      uriInput.placeholder = isPg
        ? 'postgresql+psycopg2://user:pass@host:5432/dbname (leave blank for configured default)'
        : 'sqlite:///organic_battles.sqlite3 (leave blank for default)';
    }

    // Populate Track Select
    const select = $('#admin-folder-track-select');
    if (select && res.tracks) {
      const currentSelected = select.value;
      select.replaceChildren(...res.tracks.map(t => createEl('option', { value: t.id }, `${t.title} (${t.id})`)));
      if (currentSelected && res.tracks.some(t => t.id === currentSelected)) {
        select.value = currentSelected;
      }
      select.onchange = () => {
        const trk = res.tracks.find(t => t.id === select.value);
        if (trk) {
          const dataInput = $('#admin-folder-data-input');
          const bossInput = $('#admin-folder-boss-input');
          if (dataInput) dataInput.value = trk.data_folder || '';
          if (bossInput) bossInput.value = trk.boss_folder || '';
        }
      };
      select.dispatchEvent(new Event('change'));
    }
  } catch (err) {
    console.error('Failed to load storage config:', err);
  }
}

async function loadSystemStorageConfig() {
  await loadStorageConfig();
  await loadLoggingConfig();
}

async function loadLoggingConfig() {
  try {
    const res = await adminApi('/api/admin/system/logging', {}, 'GET');
    if (!res || !res.levels) return;

    if ($('#admin-log-level-root')) $('#admin-log-level-root').value = res.levels.root || 'INFO';
    if ($('#admin-log-level-api')) $('#admin-log-level-api').value = res.levels['organicbattles.api'] || 'INFO';
    if ($('#admin-log-level-battle')) $('#admin-log-level-battle').value = res.levels['organicbattles.battle'] || 'INFO';
    if ($('#admin-log-level-auth')) $('#admin-log-level-auth').value = res.levels['organicbattles.auth'] || 'INFO';
    if ($('#admin-log-level-database')) $('#admin-log-level-database').value = res.levels['organicbattles.database'] || 'INFO';

    const badge = $('#admin-log-file-badge');
    if (badge) badge.textContent = res.log_file_relative || 'logs/organic_battles.log';

    const sizeLabel = $('#admin-log-size-label');
    if (sizeLabel) sizeLabel.textContent = `SIZE: ${res.file_size_formatted || '0 KB'}`;

    await fetchLiveLogs();
  } catch (err) {
    console.error('Failed to load logging config:', err);
  }
}

async function fetchLiveLogs() {
  const consoleEl = $('#admin-log-console');
  if (!consoleEl) return;
  try {
    const res = await adminApi('/api/admin/system/logging/tail?lines=100', {}, 'GET');
    if (res && res.lines) {
      consoleEl.textContent = res.lines.join('');
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }
  } catch (err) {
    console.error('Failed to read live logs:', err);
    consoleEl.textContent = `[Failed to read live logs: ${err.message}]`;
  }
}


function renderAdminStatus() {
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
    tbody.replaceChildren(
      createEl('tr', {}, [
        createEl('td', { colspan: '6', style: { textAlign: 'center', color: 'var(--muted)', padding: '30px' } }, `No users found matching '${filterText}'.`)
      ])
    );
    return;
  }

  tbody.replaceChildren(...filtered.map((u) => {
    const trackLabel = u.track_name || (u.track_id ? u.track_id.toUpperCase() : 'Default Track');

    const actions = [
      createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { toggleVerify: u.id } }, u.verified ? 'UNVERIFY' : 'VERIFY'),
      createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { userMastery: u.id, username: u.username } }, 'MASTERY')
    ];
    if (u.session_id) {
      actions.push(createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { userSession: u.session_id } }, 'BATTLE'));
    }
    actions.push(createEl('button', { type: 'button', className: 'admin-cred-btn', dataset: { editCred: u.id }, title: 'Edit Username or Password' }, '🔑 CREDENTIALS'));

    return createEl('tr', { dataset: { userId: u.id } }, [
      createEl('td', {}, [
        createEl('div', { className: 'user-cell-name' }, u.username),
        createEl('div', { className: 'user-cell-id' }, `${u.id.slice(0, 8)}…`)
      ]),
      createEl('td', {}, [
        createEl('span', { style: { color: 'var(--muted)' } }, u.email)
      ]),
      createEl('td', {}, [
        createEl('span', { className: u.verified ? 'badge-verified' : 'badge-unverified' }, u.verified ? 'VERIFIED' : 'UNVERIFIED')
      ]),
      createEl('td', {}, [
        createEl('span', { className: 'pill-effective mode-json', style: { fontSize: '0.7rem' }, title: `Track: ${trackLabel}` }, trackLabel)
      ]),
      createEl('td', {}, [
        createEl('span', { style: { fontFamily: "'DM Mono', monospace", fontSize: '0.72rem', color: 'var(--cyan)' } }, `Ch ${u.chapter} // Boss ${u.boss_index + 1}`)
      ]),
      createEl('td', {}, [
        createEl('div', { style: { display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' } }, actions)
      ])
    ]);
  }));

  // Bind Actions
  tbody.querySelectorAll('[data-toggle-verify]').forEach((btn) => {
    btn.onclick = () => toggleUserVerification(btn.dataset.toggleVerify);
  });

  tbody.querySelectorAll('[data-user-mastery]').forEach((btn) => {
    btn.onclick = () => openUserMasteryModal(btn.dataset.userMastery, btn.dataset.username);
  });

  tbody.querySelectorAll('[data-user-session]').forEach((btn) => {
    btn.onclick = () => {
      switchAdminTab('sessions');
      const search = $('#admin-session-search');
      if (search) {
        search.value = btn.dataset.userSession.slice(0, 8);
        renderAdminSessions(search.value);
      }
    };
  });

  tbody.querySelectorAll('[data-edit-cred]').forEach((btn) => {
    const userId = btn.dataset.editCred;
    const user = adminUsersData.find((u) => u.id === userId);
    if (user) {
      btn.onclick = () => openAdminCredentialsModal(user);
    }
  });
}

function renderAdminSessions(filterText = '') {
  const tbody = $('#admin-sessions-tbody');
  if (!tbody) return;

  const query = filterText.toLowerCase().trim();
  const filtered = adminSessionsData.filter((s) => !query || s.username.toLowerCase().includes(query) || s.email.toLowerCase().includes(query) || s.boss_name.toLowerCase().includes(query) || String(s.chapter).includes(query) || s.session_id.includes(query));

  const stats = $('#admin-session-stats-summary');
  if (stats) {
    stats.textContent = `Total Active Sessions: ${adminSessionsData.length}`;
  }

  if (!filtered.length) {
    tbody.replaceChildren(
      createEl('tr', {}, [
        createEl('td', { colspan: '8', style: { textAlign: 'center', color: 'var(--muted)', padding: '30px' } }, `No game sessions found matching '${filterText}'.`)
      ])
    );
    return;
  }

  tbody.replaceChildren(...filtered.map((s) => {
    const trackLabel = s.track_name || (s.track_id ? s.track_id.toUpperCase() : 'Default Track');
    const chapters = s.available_chapters || [{ id: 1, name: 'Chapter 1' }];

    const chapterSelect = createEl('select', { className: 'admin-chapter-select', dataset: { chapterSelect: 'true' } },
      chapters.map((ch) => {
        const opt = createEl('option', { value: String(ch.id) }, `Ch ${ch.id}: ${ch.name.slice(0, 18)}…`);
        if (ch.id === s.chapter) opt.selected = true;
        return opt;
      })
    );

    return createEl('tr', { dataset: { sessionId: s.session_id } }, [
      createEl('td', {}, [
        createEl('div', { className: 'user-cell-name' }, s.username),
        createEl('div', { className: 'user-cell-id' }, `${s.session_id.slice(0, 8)}…`)
      ]),
      createEl('td', {}, [
        createEl('span', { className: 'pill-effective mode-json', style: { fontSize: '0.7rem' }, title: `Track: ${trackLabel}` }, trackLabel)
      ]),
      createEl('td', {}, [
        createEl('div', { style: { fontWeight: '600', color: 'var(--ink)' } }, `Ch ${s.chapter}: ${s.chapter_name}`),
        createEl('div', { style: { font: "500 0.68rem 'DM Mono', monospace", color: 'var(--orange)', marginTop: '3px' } }, `Boss ${s.boss_index + 1}: ${s.boss_name}`)
      ]),
      createEl('td', {}, [
        createEl('div', { className: 'session-hp-tag' }, [
          createEl('span', { className: 'hp-player' }, `Player: ${s.player_hp}/${s.player_max_hp} HP`),
          document.createTextNode(' '),
          createEl('span', { className: 'hp-boss' }, `Boss: ${s.boss_hp}/${s.boss_max_hp} HP`)
        ])
      ]),
      createEl('td', {}, [
        createEl('div', { style: { font: "600 0.72rem 'DM Mono', monospace", color: 'var(--cyan)' } }, `v${s.version || 1}`),
        createEl('div', { style: { font: "500 0.65rem 'DM Mono', monospace", color: 'var(--muted)' }, title: s.turn_id || 'No turn' }, `Turn: ${s.turn_id ? s.turn_id.slice(0, 8) + '…' : 'None'}`)
      ]),
      createEl('td', {}, [
        createEl('span', { className: 'badge-verified' }, `${s.completed_count} Defeated`)
      ]),
      createEl('td', {}, [
        createEl('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
          chapterSelect,
          createEl('button', { type: 'button', className: 'btn-reset', dataset: { resetSession: s.session_id } }, '⟲ RESET')
        ])
      ]),
      createEl('td', {}, [
        createEl('div', { style: { display: 'flex', gap: '6px', alignItems: 'center' } }, [
          createEl('button', { type: 'button', className: 'btn-action-sm', dataset: { inspectSession: s.session_id } }, 'INSPECT'),
          createEl('button', { type: 'button', className: 'btn-danger', dataset: { deleteSession: s.session_id } }, '🗑 DELETE')
        ])
      ])
    ]);
  }));

  // Bind Reset, Delete, and Inspect actions
  tbody.querySelectorAll('tr').forEach((row) => {
    const sessionId = row.dataset.sessionId;
    const sessionObj = adminSessionsData.find((s) => s.session_id === sessionId);
    if (!sessionObj) return;

    const chapterSelect = row.querySelector('[data-chapter-select]');
    const resetBtn = row.querySelector('[data-reset-session]');
    const deleteBtn = row.querySelector('[data-delete-session]');
    const inspectBtn = row.querySelector('[data-inspect-session]');

    if (inspectBtn) {
      inspectBtn.onclick = () => openSessionInspectModal(sessionObj);
    }

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
  $('#admin-tab-questions')?.addEventListener('click', () => switchAdminTab('questions'));
  $('#admin-tab-releases')?.addEventListener('click', () => switchAdminTab('releases'));
  $('#admin-tab-observability')?.addEventListener('click', () => switchAdminTab('observability'));
  $('#admin-tab-analytics')?.addEventListener('click', () => switchAdminTab('analytics'));
  $('#admin-tab-storage')?.addEventListener('click', () => switchAdminTab('storage'));
  $('#admin-tab-system')?.addEventListener('click', () => switchAdminTab('system'));

  document.querySelectorAll('input[name="db_dialect"]').forEach(r => {
    r.addEventListener('change', (e) => {
      const uriInput = $('#admin-db-uri-input');
      if (!uriInput) return;
      uriInput.value = '';
      if (e.target.value === 'sqlite') {
        uriInput.placeholder = 'sqlite:///organic_battles.sqlite3 (leave blank for default)';
      } else {
        uriInput.placeholder = 'postgresql+psycopg2://user:pass@host:5432/dbname (leave blank for configured default)';
      }
    });
  });

  $('#admin-db-switch-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const dialect = document.querySelector('input[name="db_dialect"]:checked')?.value || 'sqlite';
    let connection_url = $('#admin-db-uri-input')?.value.trim() || undefined;
    if (connection_url && connection_url.includes('***:***')) {
      connection_url = undefined;
    }
    const migrate_data = $('#admin-db-migrate-check')?.checked || false;
    const status = $('#admin-db-status');

    if (status) {
      status.textContent = 'Switching database…';
      status.className = 'admin-modal-status hint';
    }
    try {
      const res = await adminApi('/api/admin/system/database', { dialect, connection_url, migrate_data }, 'POST');
      if (status) {
        const migMsg = res.migration ? ` (${res.migration.users || 0} users copied)` : '';
        status.textContent = `Switched to ${res.dialect.toUpperCase()} successfully!${migMsg}`;
        status.className = 'admin-modal-status hint';
      }
      showAdminToast(`Database switched to ${res.dialect.toUpperCase()}`);
      loadStorageConfig();
      loadAdminDashboard().catch(() => {});
    } catch (err) {
      if (status) {
        status.textContent = `Error: ${err.message}`;
        status.className = 'admin-modal-status error';
      }
    }
  });

  $('#admin-folder-switch-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const track_id = $('#admin-folder-track-select')?.value;
    const data_folder = $('#admin-folder-data-input')?.value.trim();
    const boss_folder = $('#admin-folder-boss-input')?.value.trim() || undefined;
    const status = $('#admin-folder-status');

    if (status) {
      status.textContent = 'Updating paths…';
      status.className = 'admin-modal-status hint';
    }
    try {
      await adminApi('/api/admin/system/folders', { track_id, data_folder, boss_folder }, 'POST');
      if (status) {
        status.textContent = 'Folders updated and cache cleared!';
        status.className = 'admin-modal-status hint';
      }
      showAdminToast('Content folders updated');
      loadStorageConfig();
    } catch (err) {
      if (status) {
        status.textContent = `Error: ${err.message}`;
        status.className = 'admin-modal-status error';
      }
    }
  });

  $('#admin-logging-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const levels = {
      root: $('#admin-log-level-root')?.value || 'INFO',
      'organicbattles.api': $('#admin-log-level-api')?.value || 'INFO',
      'organicbattles.battle': $('#admin-log-level-battle')?.value || 'INFO',
      'organicbattles.auth': $('#admin-log-level-auth')?.value || 'INFO',
      'organicbattles.database': $('#admin-log-level-database')?.value || 'INFO',
    };
    const status = $('#admin-logging-status');
    if (status) {
      status.textContent = 'Saving logging thresholds…';
      status.className = 'admin-modal-status hint';
    }

    try {
      const res = await adminApi('/api/admin/system/logging', { levels }, 'POST');
      if (status) {
        status.textContent = 'Logging thresholds updated & persisted!';
        status.className = 'admin-modal-status hint';
      }
      showAdminToast('Logging thresholds updated');
      await loadLoggingConfig();
    } catch (err) {
      if (status) {
        status.textContent = `Error: ${err.message}`;
        status.className = 'admin-modal-status error';
      }
    }
  });

  $('#admin-refresh-logs-btn')?.addEventListener('click', async () => {
    await fetchLiveLogs();
    showAdminToast('Live logs refreshed');
  });

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
      await adminApi('/api/admin/login', { username, password, client_type: 'browser' }, 'POST');
      try { localStorage.removeItem('orgo_admin_token'); } catch (_) {}
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
    try { localStorage.removeItem('orgo_admin_token'); } catch (_) {}
    showAdminLogin();
  });

  $('#admin-user-search')?.addEventListener('input', (event) => {
    renderAdminUsers(event.target.value);
  });

  $('#admin-session-search')?.addEventListener('input', (event) => {
    renderAdminSessions(event.target.value);
  });

  $('#admin-qb-track-select')?.addEventListener('change', () => { qbCurrentPage = 1; loadQuestionBank(); });
  $('#admin-qb-chapter-select')?.addEventListener('change', () => { qbCurrentPage = 1; loadQuestionBank(); });
  $('#admin-qb-difficulty-select')?.addEventListener('change', () => { qbCurrentPage = 1; loadQuestionBank(); });
  $('#admin-qb-search-btn')?.addEventListener('click', () => { qbCurrentPage = 1; loadQuestionBank(); });
  $('#admin-qb-search-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); qbCurrentPage = 1; loadQuestionBank(); } });
  $('#admin-qb-prev-btn')?.addEventListener('click', () => { if (qbCurrentPage > 1) { qbCurrentPage--; loadQuestionBank(); } });
  $('#admin-qb-next-btn')?.addEventListener('click', () => { if (qbCurrentPage < qbTotalPages) { qbCurrentPage++; loadQuestionBank(); } });

  $('#admin-qe-cancel-btn')?.addEventListener('click', closeQuestionEditor);
  $('#admin-qe-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const qId = $('#admin-qe-question-id')?.value;
    const status = $('#admin-qe-status');
    const saveBtn = $('#admin-qe-save-btn');

    const prompt = $('#admin-qe-prompt')?.value.trim();
    const topic = $('#admin-qe-topic')?.value.trim();
    const difficulty = $('#admin-qe-difficulty')?.value;
    const explanation = $('#admin-qe-explanation')?.value.trim();

    const optA = $('#admin-qe-opt-a')?.value.trim();
    const optB = $('#admin-qe-opt-b')?.value.trim();
    const optC = $('#admin-qe-opt-c')?.value.trim();
    const optD = $('#admin-qe-opt-d')?.value.trim();
    const correctOpt = document.querySelector('input[name="qe_correct_option"]:checked')?.value || 'A';

    const options = [
      { label: 'A', text: optA },
      { label: 'B', text: optB },
    ];
    if (optC) options.push({ label: 'C', text: optC });
    if (optD) options.push({ label: 'D', text: optD });

    let spells = [20, 30, 45];
    const rawSpells = $('#admin-qe-spells')?.value.trim();
    if (rawSpells) {
      spells = rawSpells.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
    }

    let health = [100];
    const rawHealth = $('#admin-qe-health')?.value.trim();
    if (rawHealth) {
      health = rawHealth.split(',').map(h => parseInt(h.trim(), 10)).filter(n => !isNaN(n));
    }

    const corrObj = options.find(o => o.label === correctOpt);
    const correctAnswer = corrObj ? corrObj.text : (options[0] ? options[0].text : '');

    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'SAVING…'; }
    if (status) { status.textContent = 'Validating and saving question…'; status.className = 'admin-modal-status hint'; }

    try {
      const res = await adminApi(`/api/admin/questions/${qId}`, {
        prompt,
        topic,
        difficulty,
        explanation,
        options,
        correct_option: correctOpt,
        correct_answer: correctAnswer,
        spells,
        health,
      }, 'PUT');

      showAdminToast(`✓ ${res.message}`);
      closeQuestionEditor();
      loadQuestionBank();
    } catch (err) {
      if (status) { status.textContent = `Error: ${err.message}`; status.className = 'admin-modal-status error'; }
      if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'SAVE QUESTION'; }
    }
  });

  $('#admin-qa-close-btn')?.addEventListener('click', closeDistractorAnalytics);
  $('#admin-si-close-btn')?.addEventListener('click', closeSessionInspectModal);
  $('#admin-um-close-btn')?.addEventListener('click', closeUserMasteryModal);

  $('#admin-ingest-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const track_id = $('#admin-ingest-track-select')?.value || null;
    const batch_size = parseInt($('#admin-ingest-batch-size')?.value, 10) || 1000;
    const status = $('#admin-ingest-status');
    const btn = $('#admin-ingest-btn');

    if (btn) { btn.disabled = true; btn.textContent = 'INGESTING…'; }
    if (status) { status.textContent = 'Parsing and ingesting questions into draft release…'; status.className = 'admin-modal-status hint'; }

    try {
      const res = await adminApi('/api/admin/questions/ingest', { track_id, batch_size }, 'POST');
      if (status) {
        status.textContent = `Successfully processed ${res.total_questions} questions across ${res.tracks_processed} track(s)!`;
        status.className = 'admin-modal-status hint';
      }
      showAdminToast(`✓ Ingested ${res.total_questions} questions`);
      loadReleasesTab();
    } catch (err) {
      if (status) {
        status.textContent = `Ingestion failed: ${err.message}`;
        status.className = 'admin-modal-status error';
      }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'START BATCH INGESTION'; }
    }
  });

  $('#admin-releases-track-select')?.addEventListener('change', loadReleasesTab);

  $('#admin-obs-refresh-btn')?.addEventListener('click', () => {
    loadObservabilityMetrics();
    showAdminToast('Observability metrics refreshed');
  });

  $('#admin-obs-warm-btn')?.addEventListener('click', async () => {
    const btn = $('#admin-obs-warm-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'WARMING…'; }
    try {
      const res = await adminApi('/api/admin/system/cache/warm', {}, 'POST');
      showAdminToast(`✓ Warmed ${Object.keys(res.results || {}).length} tracks`);
      loadObservabilityMetrics();
    } catch (err) {
      showAdminToast(`Cache warming failed: ${err.message}`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '⚡ WARM CACHE'; }
    }
  });

  $('#admin-obs-autorefresh')?.addEventListener('change', setupObsAutoRefresh);

  $('#admin-analytics-track-select')?.addEventListener('change', loadLearningAnalytics);
  $('#admin-analytics-refresh-btn')?.addEventListener('click', () => {
    loadLearningAnalytics();
    showAdminToast('Analytics refreshed');
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

  // --- Track Selection Screen Management ---
  let selectedTrackId = localStorage.getItem('organic_battles_selected_track') || 'adv-outcomes';
  let trackFilterCurriculum = 'all';
  let trackSearchQuery = '';

  function getCustomFolders() {
    try {
      return JSON.parse(localStorage.getItem('organic_battles_track_folders') || '{}');
    } catch (_) {
      return {};
    }
  }

  function saveCustomFolder(trackId, folderPath) {
    const folders = getCustomFolders();
    if (folderPath && folderPath.trim()) {
      folders[trackId] = folderPath.trim();
    } else {
      delete folders[trackId];
    }
    localStorage.setItem('organic_battles_track_folders', JSON.stringify(folders));
  }

  function getTrackDataFolder(track) {
    const custom = getCustomFolders();
    return custom[track.id] || track.data_folder;
  }

  function getTracksList() {
    return (typeof TRACKS !== 'undefined' ? TRACKS : (window.TRACKS || []));
  }

  function showTrackSelectionScreen(avatarId = null) {
    $('#boot')?.classList.add('hidden');
    $('#auth-screen')?.classList.add('hidden');
    $('#avatar-creator')?.classList.add('hidden');
    $('#game-shell')?.classList.add('hidden');
    $('#track-screen')?.classList.remove('hidden');

    const charId = avatarId || session?.avatar?.character || selectedAvatar;
    const char = charId && CHARACTERS[charId] ? CHARACTERS[charId] : null;
    const companionName = char ? char.name : 'Alchemist';
    const initials = companionName.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase() || 'AL';

    const avatarEl = $('#track-player-avatar');
    const nameEl = $('#track-player-name');
    if (avatarEl) avatarEl.textContent = initials;
    if (nameEl) nameEl.textContent = companionName;

    renderTrackSelection();
  }

  function renderTrackSelection() {
    const gallery = $('#track-gallery');
    const emptyState = $('#track-empty-state');
    const availableCount = $('#track-available-count');
    const tracks = getTracksList();
    if (!gallery) return;

    const query = trackSearchQuery.trim().toLowerCase();
    const filtered = tracks.filter((t) => {
      const matchesCurriculum = trackFilterCurriculum === 'all' || t.curriculum === trackFilterCurriculum;
      const matchesQuery = !query || `${t.title} ${t.detail} ${t.boss}`.toLowerCase().includes(query);
      return matchesCurriculum && matchesQuery;
    });

    if (availableCount) {
      availableCount.textContent = `${filtered.length} TRACKS AVAILABLE`;
    }

    const clearBtn = $('#track-search-clear');
    if (clearBtn) {
      clearBtn.classList.toggle('hidden', !trackSearchQuery);
    }

    if (!tracks.some((t) => t.id === selectedTrackId)) {
      selectedTrackId = tracks[0]?.id || 'adv-outcomes';
    }

    if (filtered.length === 0) {
      gallery.classList.add('hidden');
      emptyState?.classList.remove('hidden');
    } else {
      gallery.classList.remove('hidden');
      emptyState?.classList.add('hidden');

      gallery.replaceChildren(...filtered.map((track, index) => {
        const isSelected = track.id === selectedTrackId;
        const isAdv = track.curriculum === 'advanced';
        const curTagClass = isAdv ? 'adv' : 'found';
        const curTagLetter = isAdv ? 'A' : 'F';
        const waterIndex = String(index + 1).padStart(2, '0');

        const card = createEl('div', {
          className: `track-card ${isSelected ? 'selected' : ''}`,
          dataset: { trackId: track.id },
          role: 'button',
          tabindex: '0',
          'aria-pressed': isSelected ? 'true' : 'false'
        }, [
          createEl('div', { className: 'track-card-header' }, [
            createEl('span', { className: `curriculum-tag ${curTagClass}`, title: isAdv ? 'Advanced Mechanistic Mastery' : 'Foundational Open' }, curTagLetter),
            createEl('div', { className: 'track-card-actions' }, [
              createEl('button', { type: 'button', className: 'track-tile-config-btn', title: `Configure JSON folder location for ${track.title}` }, '⚙ PATH'),
              createEl('span', { className: 'track-check-indicator' }, '✓')
            ])
          ]),
          createEl('div', { className: 'track-card-body' }, [
            createEl('div', { className: 'track-card-title' }, track.title),
            createEl('div', { className: 'track-card-detail' }, track.detail),
            createEl('div', { className: 'track-card-boss' }, `⚔ Archetype: ${track.boss}`)
          ]),
          createEl('span', { className: 'track-watermark', 'aria-hidden': 'true' }, waterIndex)
        ]);

        card.querySelector('.track-tile-config-btn').addEventListener('click', (e) => {
          e.stopPropagation();
          openTrackFolderModal(track.id);
        });

        card.addEventListener('click', () => {
          selectedTrackId = track.id;
          localStorage.setItem('organic_battles_selected_track', track.id);
          renderTrackSelection();
        });

        card.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            selectedTrackId = track.id;
            localStorage.setItem('organic_battles_selected_track', track.id);
            renderTrackSelection();
          }
        });

        return card;
      }));
    }

    // Update Loadout Preview Box
    const activeTrack = tracks.find((t) => t.id === selectedTrackId) || tracks[0];
    if (activeTrack) {
      const isAdv = activeTrack.curriculum === 'advanced';
      const badge = $('#loadout-curriculum-badge');
      if (badge) {
        badge.textContent = isAdv ? 'A' : 'F';
        badge.style.background = isAdv ? 'var(--cyan)' : 'var(--violet)';
        badge.style.color = '#06111b';
      }
      const titleEl = $('#loadout-track-title');
      if (titleEl) titleEl.textContent = activeTrack.title;
      const curEl = $('#loadout-track-curriculum');
      if (curEl) curEl.textContent = `${isAdv ? 'ADVANCED' : 'FOUNDATIONAL'} · ${activeTrack.questions.toLocaleString()} QUESTIONS`;
      const detailEl = $('#loadout-track-detail');
      if (detailEl) detailEl.textContent = activeTrack.detail;
      const folderEl = $('#loadout-folder-path');
      if (folderEl) folderEl.textContent = getTrackDataFolder(activeTrack);
      const poolEl = $('#loadout-pool-count');
      if (poolEl) {
        poolEl.replaceChildren(
          document.createTextNode(`${activeTrack.questions.toLocaleString()} `),
          createEl('span', { className: 'stat-unit' }, 'questions')
        );
      }
    }
  }

  function openTrackFolderModal(trackId) {
    const tracks = getTracksList();
    const track = tracks.find((t) => t.id === trackId);
    if (!track) return;

    const modal = $('#track-folder-modal');
    if (!modal) return;

    $('#folder-modal-track-id').value = track.id;
    $('#folder-modal-track-name').value = track.title;
    $('#folder-modal-path-input').value = getTrackDataFolder(track);

    const status = $('#folder-modal-status');
    if (status) {
      status.textContent = '';
      status.className = 'admin-modal-status';
    }

    modal.classList.remove('hidden');
    $('#folder-modal-path-input')?.focus();
  }

  function closeTrackFolderModal() {
    $('#track-folder-modal')?.classList.add('hidden');
  }

  function bindTrackEvents() {
    $('#track-search-input')?.addEventListener('input', (e) => {
      trackSearchQuery = e.target.value;
      renderTrackSelection();
    });

    $('#track-search-clear')?.addEventListener('click', () => {
      trackSearchQuery = '';
      const input = $('#track-search-input');
      if (input) input.value = '';
      renderTrackSelection();
    });

    $('#track-curriculum-select')?.addEventListener('change', (e) => {
      trackFilterCurriculum = e.target.value;
      renderTrackSelection();
    });

    $('#track-reset-filters-btn')?.addEventListener('click', () => {
      trackSearchQuery = '';
      trackFilterCurriculum = 'all';
      const input = $('#track-search-input');
      if (input) input.value = '';
      const select = $('#track-curriculum-select');
      if (select) select.value = 'all';
      renderTrackSelection();
    });

    $('#loadout-configure-folder-btn')?.addEventListener('click', () => {
      openTrackFolderModal(selectedTrackId);
    });

    $('#track-folder-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const trackId = $('#folder-modal-track-id').value;
      const newPath = $('#folder-modal-path-input').value;
      const status = $('#folder-modal-status');

      saveCustomFolder(trackId, newPath);
      if (status) {
        status.textContent = 'Folder path saved successfully!';
        status.className = 'admin-modal-status success';
      }
      renderTrackSelection();
      setTimeout(() => {
        closeTrackFolderModal();
      }, 500);
    });

    $('#reset-folder-path-btn')?.addEventListener('click', () => {
      const trackId = $('#folder-modal-track-id').value;
      const tracks = getTracksList();
      const track = tracks.find((t) => t.id === trackId);
      if (!track) return;

      saveCustomFolder(trackId, '');
      $('#folder-modal-path-input').value = track.data_folder;
      const status = $('#folder-modal-status');
      if (status) {
        status.textContent = 'Reset to default folder.';
        status.className = 'admin-modal-status hint';
      }
      renderTrackSelection();
    });

    $('#cancel-folder-modal-btn')?.addEventListener('click', closeTrackFolderModal);
    $('#track-folder-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'track-folder-modal') closeTrackFolderModal();
    });

    $('#track-blocked-resume-btn')?.addEventListener('click', () => {
      $('#track-blocked-modal')?.classList.add('hidden');
      $('#track-screen')?.classList.add('hidden');
      $('#game-shell')?.classList.remove('hidden');
      startPhaser();
      render(session);
    });
    $('#track-blocked-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'track-blocked-modal') {
        $('#track-blocked-modal')?.classList.add('hidden');
      }
    });

    $('#start-battle-button')?.addEventListener('click', async () => {
      const startBtn = $('#start-battle-button');
      if (!startBtn) return;

      startBtn.disabled = true;
      startBtn.replaceChildren(createEl('span', {}, 'PREPARING ARENA…'));

      try {
        const tracks = getTracksList();
        const activeTrack = tracks.find((t) => t.id === selectedTrackId) || tracks[0];
        const folderPath = getTrackDataFolder(activeTrack);

        if (session?.session_id) {
          try {
            const res = await api('/api/game/track', {
              session_id: session.session_id,
              track_id: selectedTrackId,
              data_folder: folderPath,
              boss_folder: activeTrack?.boss_folder,
            });
            clearExplanation();
            if (res && res.session) {
              session = res.session;
            }
          } catch (trackErr) {
            console.warn('Track switch blocked:', trackErr);
            const msgEl = $('#track-blocked-message');
            if (msgEl) {
              msgEl.textContent = trackErr.message || 'Please complete your active chapter in this track before switching tracks!';
            }
            $('#track-blocked-modal')?.classList.remove('hidden');
            startBtn.disabled = false;
            startBtn.replaceChildren(
              createEl('span', {}, 'START THE BATTLE'),
              document.createTextNode(' '),
              createEl('span', { className: 'btn-arrow' }, '→')
            );
            return;
          }
        }

        $('#track-screen')?.classList.add('hidden');
        $('#game-shell')?.classList.remove('hidden');
        startPhaser();
        render(session);
      } catch (err) {
        console.error('Failed to start duel:', err);
        startBtn.disabled = false;
        startBtn.replaceChildren(
          createEl('span', {}, 'START THE BATTLE'),
          document.createTextNode(' '),
          createEl('span', { className: 'btn-arrow' }, '→')
        );
      }
    });

    $('#back-to-avatar-button')?.addEventListener('click', () => {
      $('#track-screen')?.classList.add('hidden');
      $('#avatar-creator')?.classList.remove('hidden');
    });
  }

  $('#keep-avatar')?.addEventListener('click', () => {
    $('#avatar-creator')?.classList.add('hidden');
    showTrackSelectionScreen(session.avatar?.character || selectedAvatar);
  });

  const acceptButton = $('#accept-avatar');
  if (acceptButton) {
    acceptButton.addEventListener('click', async () => {
      if (!selectedAvatar) return;
      if (session.finalized && selectedAvatar === session.avatar?.character) {
        $('#avatar-creator')?.classList.add('hidden');
        showTrackSelectionScreen(selectedAvatar);
        return;
      }
      acceptButton.disabled = true;
      acceptButton.textContent = 'CONFIRMING COMPANION…';
      try {
        const avatar = { character: selectedAvatar, body: 'arc', config: { ...DEFAULT_AVATAR_CONFIG, baseCharacter: selectedAvatar } };
        session = await api('/api/avatar/finalize', { session_id: session.session_id, ...avatar });
        playerAvatar = null;
        acceptButton.disabled = false;
        acceptButton.textContent = 'CONTINUE TO BATTLEFIELD';
        $('#avatar-creator')?.classList.add('hidden');
        showTrackSelectionScreen(selectedAvatar);
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

  bindTrackEvents();
  ensureExplanationUi();
  bindAuthEvents();
  bindAdminEvents();
}


if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bindDomEvents);
} else {
  bindDomEvents();
}

