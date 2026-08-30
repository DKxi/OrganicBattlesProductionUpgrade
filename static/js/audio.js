/**
 * Organic Battles V4P - Web Audio Synthesizer & Sound Engine
 * Procedural SFX engine using standard Web Audio API with zero external dependencies.
 */


class SoundEngine {
  constructor() {
    this.ctx = null;
    this.muted = false;
    this.volume = 0.35;
    this.masterGain = null;
    this.initialized = false;

    // Load persisted mute preference
    try {
      if (typeof localStorage !== 'undefined') {
        const savedMute = localStorage.getItem('orgo_audio_muted');
        if (savedMute !== null) {
          this.muted = savedMute === 'true';
        }
      }
    } catch (e) {
      // Ignore localStorage restrictions
    }

    // Auto-suspend / resume on tab visibility change
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          if (this.ctx && this.ctx.state === 'running') {
            this.ctx.suspend().catch(() => {});
          }
        } else {
          if (this.ctx && this.ctx.state === 'suspended' && !this.muted) {
            this.ctx.resume().catch(() => {});
          }
        }
      });
    }
  }

  ensureContext() {
    if (!this.ctx && (typeof window !== 'undefined')) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.setValueAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime);
        this.masterGain.connect(this.ctx.destination);
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
    this.initialized = true;
    return this.ctx;
  }

  toggleMute() {
    this.setMuted(!this.muted);
    return this.muted;
  }

  setMuted(isMuted) {
    this.muted = Boolean(isMuted);
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('orgo_audio_muted', String(this.muted));
      }
    } catch (e) {}

    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime);
    }
  }

  isMuted() {
    return this.muted;
  }

  setVolume(val) {
    this.volume = Math.max(0, Math.min(1, val));
    if (this.masterGain && this.ctx && !this.muted) {
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  getVolume() {
    return this.volume;
  }

  // --- Sound Effects Synthesis ---

  playTone(freq, type = 'sine', duration = 0.15, gain = 0.3) {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);

      g.gain.setValueAtTime(gain, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {}
  }

  playClick() {
    this.playTone(800, 'triangle', 0.04, 0.12);
  }

  playSpellCast(tier = 'basic') {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      const startFreq = tier === 'heavy' || tier === 'strong' ? 180 : tier === 'medium' ? 240 : 320;
      const endFreq = tier === 'heavy' || tier === 'strong' ? 720 : tier === 'medium' ? 640 : 580;
      const duration = tier === 'heavy' || tier === 'strong' ? 0.35 : 0.22;

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(startFreq, now);
      osc.frequency.exponentialRampToValueAtTime(endFreq, now + duration);

      g.gain.setValueAtTime(0.25, now);
      g.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(now + duration);
    } catch (e) {}
  }

  playBossHit() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.exponentialRampToValueAtTime(40, now + 0.3);

      g.gain.setValueAtTime(0.4, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(now + 0.3);
    } catch (e) {}
  }

  playPlayerHit() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(120, now);
      osc.frequency.linearRampToValueAtTime(60, now + 0.25);

      g.gain.setValueAtTime(0.28, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(now + 0.25);
    } catch (e) {}
  }

  playSpellFizzle() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(90, now + 0.4);

      g.gain.setValueAtTime(0.3, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(now + 0.4);
    } catch (e) {}
  }

  playBossMiss() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(500, now);
      osc.frequency.linearRampToValueAtTime(200, now + 0.2);

      g.gain.setValueAtTime(0.18, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

      osc.connect(g);
      g.connect(this.masterGain);

      osc.start();
      osc.stop(now + 0.2);
    } catch (e) {}
  }

  playVictory() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const notes = [523.25, 659.25, 783.99, 1046.50];
      const now = ctx.currentTime;

      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        const noteStart = now + idx * 0.12;
        const noteDuration = idx === notes.length - 1 ? 0.6 : 0.15;

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, noteStart);

        g.gain.setValueAtTime(0.28, noteStart);
        g.gain.exponentialRampToValueAtTime(0.0001, noteStart + noteDuration);

        osc.connect(g);
        g.connect(this.masterGain);

        osc.start(noteStart);
        osc.stop(noteStart + noteDuration);
      });
    } catch (e) {}
  }

  playDefeat() {
    if (this.muted) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    try {
      const notes = [349.23, 293.66, 233.08, 220.00];
      const now = ctx.currentTime;

      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        const noteStart = now + idx * 0.15;
        const noteDuration = idx === notes.length - 1 ? 0.7 : 0.18;

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(freq, noteStart);

        g.gain.setValueAtTime(0.25, noteStart);
        g.gain.exponentialRampToValueAtTime(0.0001, noteStart + noteDuration);

        osc.connect(g);
        g.connect(this.masterGain);

        osc.start(noteStart);
        osc.stop(noteStart + noteDuration);
      });
    } catch (e) {}
  }
}

export const soundEngine = new SoundEngine();
