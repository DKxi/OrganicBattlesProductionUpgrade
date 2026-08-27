from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def start():
    return client.post('/api/game/new').json()

def avatar():
    return {'body':'arc','skin':'warm','hair':'nebula','outfit':'coat','accessory':'goggles','aura':'teal'}

def test_new_game_defaults():
    s = start()
    assert s['player']['hp'] == 150
    assert s['boss']['name'] == 'Hybridization Goblin'

def test_avatar_is_permanent():
    s = start(); sid = s['session_id']
    assert client.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar()).status_code == 200
    assert client.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar()).status_code == 409

def test_avatar_v3_configuration_persists():
    s = start(); sid = s['session_id']
    config = {'baseCharacter': 'organic-apprentice', 'skinTone': 'medium-deep', 'hair': {'style': 'spiky', 'color': 'dark-purple'}, 'glasses': 'thin-silver', 'coat': 'blue-trim', 'flask': 'blue-catalyst'}
    payload = {**avatar(), 'config': config}
    response = client.post('/api/avatar/finalize', params={'session_id': sid}, json=payload)
    assert response.status_code == 200
    assert response.json()['avatar']['config'] == config

def test_correct_answer_deals_damage():
    s = start(); sid = s['session_id']
    client.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar())
    q = client.post('/api/battle/select-spell', params={'session_id':sid}, json={'spell_id':'fire-spark'}).json()
    answers = {
        'What does sp3 hybridization describe?':'Four equivalent hybrid orbitals',
        'A nucleophile is best described as…':'An electron-pair donor',
        'SN2 reactions are characterized by…':'Backside attack and inversion',
        'Enantiomers are molecules that are':'Non-superimposable mirror images',
        'IR spectroscopy is especially useful for identifying…':'Functional-group vibrations',
        'In a resonance hybrid, the real molecule has…':'Electron density spread across contributors',
    }
    answer = next(v for k, v in answers.items() if q['question']['prompt'].startswith(k))
    result = client.post('/api/battle/answer', params={'session_id':sid}, json={'answer':answer}).json()
    assert result['damage'] == 20


def test_favicon_endpoint_exists():
    response = client.get('/favicon.ico')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/')


def test_page_uses_versioned_static_assets():
    html = client.get('/').text
    assert '/static/css/game.css?v=' in html
    assert '/static/js/main.js?v=' in html


# --- Avatar-only regression tests (added alongside the avatar art/cleanup pass) ---
# These verify the avatar layer stays purely presentational: combat math, cooldowns,
# and progression must be identical regardless of what avatar config is stored.

def test_avatar_with_missing_config_still_works_like_a_legacy_save():
    """An avatar payload with no `config` (as an older/legacy save might have) must
    still finalize successfully and default to a safe empty config rather than
    erroring or blocking gameplay."""
    s = start(); sid = s['session_id']
    response = client.post('/api/avatar/finalize', params={'session_id': sid}, json=avatar())
    assert response.status_code == 200
    assert response.json()['avatar']['config'] == {}
    # Gameplay must remain fully available with this minimal/legacy avatar.
    spell = client.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'acid-shot'})
    assert spell.status_code == 200


def test_avatar_customization_does_not_change_damage_or_cooldowns():
    """Two sessions with different avatar configs but the same spell/answer choices
    must produce identical combat outcomes: avatar config is presentation-only."""
    outcomes = []
    for config in ({}, {'skinTone': 'deep', 'hair': {'style': 'curly', 'color': 'blue-black'}, 'coat': 'reaction-coat', 'accessory': 'wrist-device'}):
        s = start(); sid = s['session_id']
        client.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': config})
        q = client.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'fire-spark'}).json()
        answers = {
            'What does sp3 hybridization describe?': 'Four equivalent hybrid orbitals',
            'A nucleophile is best described as…': 'An electron-pair donor',
            'SN2 reactions are characterized by…': 'Backside attack and inversion',
            'Enantiomers are molecules that are': 'Non-superimposable mirror images',
            'IR spectroscopy is especially useful for identifying…': 'Functional-group vibrations',
            'In a resonance hybrid, the real molecule has…': 'Electron density spread across contributors',
        }
        answer = next(v for k, v in answers.items() if q['question']['prompt'].startswith(k))
        result = client.post('/api/battle/answer', params={'session_id': sid}, json={'answer': answer}).json()
        outcomes.append((result['damage'], result['correct'], round(result['cooldowns']['fire-spark'])))
    assert outcomes[0] == outcomes[1]


def test_avatar_config_persists_unchanged_across_subsequent_state_reads():
    """The exact avatar configuration selected at finalize time must still be
    present, byte-for-byte, when the game state is re-fetched later (e.g. as the
    battle screen re-renders the avatar on every turn)."""
    s = start(); sid = s['session_id']
    config = {'skinTone': 'light', 'hair': {'style': 'medium-layered', 'color': 'brown'}, 'flask': 'orange-energy', 'accentColor': 'crimson'}
    client.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': config})
    client.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'carbon-punch'})
    state = client.get('/api/game/state', params={'session_id': sid}).json()
    assert state['avatar']['config'] == config


def test_avatar_endpoints_do_not_expose_boss_or_progression_regressions():
    """Sanity check that finalizing an avatar (with a rich config) leaves boss HP,
    chapter, and progression exactly as a fresh session would have them."""
    s = start(); sid = s['session_id']
    before = client.get('/api/progression', params={'session_id': sid}).json()
    client.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': {'coat': 'advanced-chemist'}})
    after = client.get('/api/progression', params={'session_id': sid}).json()
    assert before['boss']['hp'] == after['boss']['hp']
    assert before['chapter'] == after['chapter']
    assert before['completed'] == after['completed'] == []
