/**
 * GHOST.OS — Real-Time Multi-Trace Oscilloscope Canvas Engine
 * Completely offline, zero external dependencies.
 */

class GhostOscilloscope {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.warn(`Canvas #${canvasId} not found`);
      return;
    }
    this.ctx = this.canvas.getContext('2d');
    this.maxPoints = options.maxPoints || 120;
    this.minValue = options.minValue ?? -20;
    this.maxValue = options.maxValue ?? 20;
    this.autoscale = options.autoscale ?? false;
    this.unit = options.unit || '';
    this.traces = options.traces || [
      { key: 'x', color: '#ff3366', label: 'X' },
      { key: 'y', color: '#00ff66', label: 'Y' },
      { key: 'z', color: '#00ccff', label: 'Z' },
    ];

    this.history = []; // Array of { [key]: value }

    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.floor(rect.width * window.devicePixelRatio || 1);
    this.canvas.height = Math.floor(rect.height * window.devicePixelRatio || 1);
    this.render();
  }

  pushPoint(pointObj) {
    this.history.push(pointObj);
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

    // Clear background
    ctx.fillStyle = '#020402';
    ctx.fillRect(0, 0, w, h);

    // Grid lines (subtle dark green phosphor grid)
    ctx.strokeStyle = '#0a1a0a';
    ctx.lineWidth = 1;
    const gridCols = 10;
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

    // Zero-axis line
    const zeroY = this.valToY(0, h);
    ctx.strokeStyle = '#183818';
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(w, zeroY);
    ctx.stroke();

    // Scale bounds
    let minV = this.minValue;
    let maxV = this.maxValue;

    if (this.autoscale && this.history.length > 2) {
      let localMin = Infinity;
      let localMax = -Infinity;
      for (const p of this.history) {
        for (const tr of this.traces) {
          const v = p[tr.key];
          if (typeof v === 'number') {
            if (v < localMin) localMin = v;
            if (v > localMax) localMax = v;
          }
        }
      }
      if (localMin !== Infinity && localMax !== -Infinity) {
        const span = Math.max(0.5, localMax - localMin);
        minV = localMin - span * 0.15;
        maxV = localMax + span * 0.15;
      }
    }

    const valToY = (val) => {
      const clamped = Math.max(minV, Math.min(maxV, val));
      const norm = (clamped - minV) / (maxV - minV || 1);
      return h - norm * h;
    };

    // Draw traces
    const stepX = w / (this.maxPoints - 1);

    for (const trace of this.traces) {
      if (this.history.length < 2) continue;

      ctx.strokeStyle = trace.color;
      ctx.lineWidth = 1.8 * (window.devicePixelRatio || 1);
      ctx.shadowColor = trace.color;
      ctx.shadowBlur = 6;
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
      ctx.shadowBlur = 0; // Reset shadow
    }

    // Min / Max legend text
    ctx.fillStyle = '#446644';
    ctx.font = `${10 * (window.devicePixelRatio || 1)}px monospace`;
    ctx.fillText(`${maxV.toFixed(1)}${this.unit}`, 6, 14 * (window.devicePixelRatio || 1));
    ctx.fillText(`${minV.toFixed(1)}${this.unit}`, 6, h - 4);
  }

  valToY(val, h) {
    const norm = (val - this.minValue) / (this.maxValue - this.minValue || 1);
    return h - norm * h;
  }
}
