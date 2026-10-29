/**
 * GHOST.OS — Real-Time Multi-Trace Oscilloscope Canvas Engine
 * Premium retro-cyber visual rendering with phosphor glow, dynamic auto-scale,
 * in-canvas HUD readouts, and zero external dependencies.
 */

class GhostOscilloscope {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.warn(`Canvas #${canvasId} not found`);
      return;
    }
    this.ctx = this.canvas.getContext('2d');
    this.maxPoints = options.maxPoints || 140;
    this.minValue = options.minValue ?? -25;
    this.maxValue = options.maxValue ?? 25;
    this.currentMin = this.minValue;
    this.currentMax = this.maxValue;
    this.autoscale = options.autoscale ?? true;
    this.unit = options.unit || '';
    this.title = options.title || '';
    this.traces = options.traces || [
      { key: 'ax', color: '#ff3366', label: 'Ax' },
      { key: 'ay', color: '#00ff66', label: 'Ay' },
      { key: 'az', color: '#00ccff', label: 'Az' },
    ];

    this.history = []; // Array of { [key]: value }
    this.lastValues = {};

    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const w = rect.width > 20 ? rect.width : 540;
    const h = rect.height > 20 ? rect.height : 220;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.dpr = dpr;
    this.render();
  }

  pushPoint(pointObj) {
    this.history.push(pointObj);
    this.lastValues = pointObj;
    if (this.history.length > this.maxPoints) {
      this.history.shift();
    }
    this.render();
  }

  render() {
    if (!this.canvas || !this.ctx) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const dpr = this.dpr || 1;

    // Clear background
    ctx.fillStyle = '#020502';
    ctx.fillRect(0, 0, w, h);

    // Grid lines (subtle dark green phosphor matrix)
    ctx.strokeStyle = '#071609';
    ctx.lineWidth = 1 * dpr;
    const gridCols = 12;
    const gridRows = 6;

    for (let c = 1; c < gridCols; c++) {
      const x = (w / gridCols) * c;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    for (let r = 1; r < gridRows; r++) {
      const y = (h / gridRows) * r;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Dynamic auto-scale calculations
    if (this.autoscale && this.history.length > 2) {
      let localMin = Infinity;
      let localMax = -Infinity;
      for (const p of this.history) {
        for (const tr of this.traces) {
          const v = p[tr.key];
          if (typeof v === 'number' && !isNaN(v)) {
            if (v < localMin) localMin = v;
            if (v > localMax) localMax = v;
          }
        }
      }
      if (localMin !== Infinity && localMax !== -Infinity) {
        const span = Math.max(2.0, localMax - localMin);
        const targetMin = localMin - span * 0.15;
        const targetMax = localMax + span * 0.15;
        // Smooth damping
        this.currentMin += (targetMin - this.currentMin) * 0.1;
        this.currentMax += (targetMax - this.currentMax) * 0.1;
      }
    } else {
      this.currentMin = this.minValue;
      this.currentMax = this.maxValue;
    }

    const minV = this.currentMin;
    const maxV = this.currentMax;

    const valToY = (val) => {
      const clamped = Math.max(minV, Math.min(maxV, val));
      const norm = (clamped - minV) / (maxV - minV || 1);
      return h - norm * h;
    };

    // Zero-axis reference line
    const zeroY = valToY(0);
    ctx.strokeStyle = 'rgba(0, 255, 102, 0.25)';
    ctx.setLineDash([4 * dpr, 4 * dpr]);
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(w, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw Multi-Trace lines with glow
    const stepX = w / (this.maxPoints - 1);

    for (const trace of this.traces) {
      if (this.history.length < 2) continue;

      ctx.strokeStyle = trace.color;
      ctx.lineWidth = 1.8 * dpr;
      ctx.shadowColor = trace.color;
      ctx.shadowBlur = 8 * dpr;
      ctx.beginPath();

      const startIdx = this.maxPoints - this.history.length;
      for (let i = 0; i < this.history.length; i++) {
        const x = (startIdx + i) * stepX;
        const v = this.history[i][trace.key] ?? 0;
        const y = valToY(v);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      ctx.shadowBlur = 0; // Reset shadow for performance
    }

    // Top and Bottom Scale Labels
    ctx.fillStyle = '#447744';
    ctx.font = `${10 * dpr}px monospace`;
    ctx.fillText(`${maxV.toFixed(1)}${this.unit}`, 8 * dpr, 14 * dpr);
    ctx.fillText(`${minV.toFixed(1)}${this.unit}`, 8 * dpr, h - 6 * dpr);

    // In-canvas HUD readout in top-right corner
    let hudX = w - 12 * dpr;
    const hudY = 14 * dpr;
    ctx.textAlign = 'right';

    let hudText = '';
    for (const tr of this.traces) {
      const val = this.lastValues[tr.key];
      const valStr = (typeof val === 'number') ? val.toFixed(1) : '--';
      ctx.fillStyle = tr.color;
      hudText = `${tr.label}: ${valStr}`;
      ctx.fillText(hudText, hudX, hudY);
      hudX -= (ctx.measureText(hudText).width + 12 * dpr);
    }
    ctx.textAlign = 'left';
  }
}
