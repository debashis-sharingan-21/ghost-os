/**
 * GHOST.OS — Main Application Orchestrator & Cinematic Opening Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const stageGate = document.getElementById('stage-ghost-gate');
  const stageAwakening = document.getElementById('stage-hardware-awakening');
  const stageCommand = document.getElementById('stage-command-center');
  const btnAwaken = document.getElementById('btn-awaken');
  const btnSkipAwakening = document.getElementById('btn-skip-awakening');
  const btnLockTerminal = document.getElementById('btn-lock-terminal');
  const chkSkipIntro = document.getElementById('chk-skip-intro');

  const awakeningLog = document.getElementById('awakening-log');
  const awakeningProgressLabel = document.getElementById('awakening-progress-label');
  const hwStatusSummary = document.getElementById('hardware-status-summary');
  const esp32Canvas = document.getElementById('esp32-wireframe-canvas');

  // Terminal & Charts
  const terminal = new GhostTerminal('terminal-console', 120);

  const accelChart = new GhostOscilloscope('accel-canvas', {
    maxPoints: 120,
    minValue: -25,
    maxValue: 25,
    autoscale: true,
    unit: ' m/s²',
    traces: [
      { key: 'ax', color: '#ff3366', label: 'Ax' },
      { key: 'ay', color: '#00ff66', label: 'Ay' },
      { key: 'az', color: '#00ccff', label: 'Az' },
      { key: 'mag', color: '#ffcc00', label: '|A|' },
    ],
  });

  const gyroChart = new GhostOscilloscope('gyro-canvas', {
    maxPoints: 120,
    minValue: -300,
    maxValue: 300,
    autoscale: true,
    unit: ' °/s',
    traces: [
      { key: 'gx', color: '#ff6600', label: 'Gx (Roll)' },
      { key: 'gy', color: '#ff00ff', label: 'Gy (Pitch)' },
      { key: 'gz', color: '#33ffff', label: 'Gz (Yaw)' },
    ],
  });

  // UI Badges & Stats
  const badgeSource = document.getElementById('badge-source');
  const badgeAlert = document.getElementById('badge-alert');
  const indicatorLink = document.getElementById('indicator-link');
  const btnToggleLink = document.getElementById('btn-toggle-link');
  const serialPortSelect = document.getElementById('serial-port-select');
  const baudRateSelect = document.getElementById('baud-rate-select');

  const elSeq = document.getElementById('stat-seq');
  const elRate = document.getElementById('stat-rate');
  const elUptime = document.getElementById('stat-uptime');
  const elAx = document.getElementById('stat-ax');
  const elAy = document.getElementById('stat-ay');
  const elAz = document.getElementById('stat-az');
  const elAmag = document.getElementById('stat-amag');
  const elGx = document.getElementById('stat-gx');
  const elGy = document.getElementById('stat-gy');
  const elGz = document.getElementById('stat-gz');
  const elTemp = document.getElementById('stat-temp');
  const elHeap = document.getElementById('stat-heap');
  const elVcc = document.getElementById('stat-vcc');

  let frameCount = 0;
  let prevAnomalyState = false;
  let selectedEventId = null;

  // Rate calculator loop
  setInterval(() => {
    if (elRate) elRate.textContent = `${frameCount.toFixed(1)} HZ`;
    frameCount = 0;
  }, 1000);

  // ========================================================
  // STAGE TRANSITIONS & CINEMATIC STARTUP FLOW
  // ========================================================

  function enterCommandCenter() {
    stageGate.classList.add('stage-hidden');
    stageAwakening.classList.add('stage-hidden');
    stageCommand.style.display = 'flex';
    accelChart.resize();
    gyroChart.resize();
    terminal.sys('COMMAND CENTER ACTIVE. TELEMETRY DISPLAY RESTORED.');
    refreshSerialPorts();
    refreshAnomaliesList();
    refreshAiStatus();
    refreshSessionsList();
  }

  function returnToGhostGate() {
    stageGate.classList.remove('stage-hidden');
    stageAwakening.classList.add('stage-hidden');
    terminal.warn('TERMINAL ACCESS LOCKED. CARRIER CONFINED TO GHOST GATE.');
  }

  // Check skip intro preference
  if (sessionStorage.getItem('ghost_skip_intro') === 'true') {
    if (chkSkipIntro) chkSkipIntro.checked = true;
    enterCommandCenter();
  } else {
    // Show Gate
    stageGate.classList.remove('stage-hidden');
    stageAwakening.classList.add('stage-hidden');
  }

  if (chkSkipIntro) {
    chkSkipIntro.addEventListener('change', (e) => {
      sessionStorage.setItem('ghost_skip_intro', e.target.checked ? 'true' : 'false');
    });
  }

  // Stage 1 -> Stage 2 trigger
  function awakenSystem() {
    stageGate.classList.add('stage-hidden');
    stageAwakening.classList.remove('stage-hidden');
    startHardwareAwakening();
  }

  if (btnAwaken) {
    btnAwaken.addEventListener('click', awakenSystem);
  }

  window.addEventListener('keydown', (e) => {
    if (!stageGate.classList.contains('stage-hidden')) {
      if (e.key === 'Escape') {
        enterCommandCenter();
      } else {
        awakenSystem();
      }
    } else if (!stageAwakening.classList.contains('stage-hidden')) {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        enterCommandCenter();
      }
    }
  });

  if (btnSkipAwakening) {
    btnSkipAwakening.addEventListener('click', enterCommandCenter);
  }

  if (btnLockTerminal) {
    btnLockTerminal.addEventListener('click', returnToGhostGate);
  }

  // Stage 2: Hardware Awakening Animation
  let awakeningAnimId = null;

  async function startHardwareAwakening() {
    awakeningLog.innerHTML = '';
    const addLog = (msg, level = 'info') => {
      const line = document.createElement('div');
      line.className = `log-line log-${level}`;
      line.textContent = `[BOOT] ${msg}`;
      awakeningLog.appendChild(line);
      awakeningLog.scrollTop = awakeningLog.scrollHeight;
    };

    addLog('XTENSA DUAL-CORE RTOS TICK INITIALIZED (240 MHz)', 'sys');
    addLog('MAPPING I2C BUS (SDA=GPIO21, SCL=GPIO22 @ 400 kHz)...', 'info');

    // Query real backend status
    let realStatus = null;
    try {
      const res = await fetch('/api/status');
      realStatus = await res.json();
    } catch (err) {
      console.warn('Backend probe during boot:', err);
    }

    // Draw ESP32 Wireframe Canvas
    if (esp32Canvas) {
      const ctx = esp32Canvas.getContext('2d');
      const w = esp32Canvas.width = esp32Canvas.parentElement.clientWidth;
      const h = esp32Canvas.height = esp32Canvas.parentElement.clientHeight;

      let step = 0;
      const maxSteps = 100;

      function renderWireframe() {
        ctx.fillStyle = '#010401';
        ctx.fillRect(0, 0, w, h);

        const progress = Math.min(1.0, step / maxSteps);
        awakeningProgressLabel.textContent = `INITIALIZING [${Math.round(progress * 100)}%]`;

        // PCB Silhouette
        ctx.strokeStyle = '#00ff66';
        ctx.lineWidth = 1.5;
        const pcbW = w * 0.7;
        const pcbH = h * 0.75;
        const ox = (w - pcbW) / 2;
        const oy = (h - pcbH) / 2;

        ctx.strokeRect(ox, oy, pcbW * progress, pcbH);

        // Antenna trace on top
        if (progress > 0.3) {
          ctx.strokeStyle = '#00ccff';
          ctx.beginPath();
          ctx.moveTo(ox + 10, oy + 10);
          ctx.lineTo(ox + 50, oy + 10);
          ctx.lineTo(ox + 50, oy + 25);
          ctx.lineTo(ox + 80, oy + 25);
          ctx.stroke();
        }

        // Dual Xtensa Cores
        if (progress > 0.5) {
          ctx.strokeStyle = '#ffb000';
          const chipW = 70;
          const chipH = 50;
          const cx = w / 2 - chipW / 2;
          const cy = h / 2 - chipH / 2;
          ctx.strokeRect(cx, cy, chipW, chipH);
          ctx.fillStyle = 'rgba(255, 176, 0, 0.1)';
          ctx.fillRect(cx, cy, chipW, chipH);

          // Core 0 & Core 1
          ctx.fillStyle = '#ffb000';
          ctx.font = '9px monospace';
          ctx.fillText('CORE 0', cx + 6, cy + 20);
          ctx.fillText('CORE 1', cx + 6, cy + 38);
        }

        // I2C Bus trace to MPU6050
        if (progress > 0.75) {
          ctx.strokeStyle = '#00ff66';
          ctx.beginPath();
          ctx.moveTo(w / 2 + 35, h / 2);
          ctx.lineTo(ox + pcbW - 20, h / 2);
          ctx.stroke();

          // MPU6050 chip box
          ctx.strokeRect(ox + pcbW - 20, h / 2 - 15, 30, 30);
          ctx.fillText('MPU', ox + pcbW - 16, h / 2 + 5);
        }

        step += 2;
        if (step <= maxSteps) {
          awakeningAnimId = requestAnimationFrame(renderWireframe);
        } else {
          // Finished progressive draw
          if (realStatus && realStatus.is_hardware_connected) {
            addLog(`PHYSICAL ESP32 LINK CONFIRMED: ${realStatus.serial_port}`, 'sys');
            hwStatusSummary.textContent = `HARDWARE LINKED: ${realStatus.serial_port}`;
          } else {
            addLog('PHYSICAL HARDWARE: NO COM CARRIER DETECTED.', 'warn');
            addLog('ENGAGING DETERMINISTIC TELEMETRY SIMULATOR (10 HZ)...', 'sys');
            hwStatusSummary.textContent = 'MODE: SIMULATOR VIRTUAL LINK ACTIVE';
          }
          addLog('SYSTEM READY. TRANSITIONING TO COMMAND CENTER...', 'sys');
          setTimeout(enterCommandCenter, 600);
        }
      }
      renderWireframe();
    } else {
      setTimeout(enterCommandCenter, 500);
    }
  }

  // ========================================================
  // WEBSOCKET TELEMETRY STREAM
  // ========================================================

  let ws = null;
  let reconnectTimeout = null;

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      terminal.sys('TELEMETRY CARRIER LOCK ESTABLISHED. 10 HZ STREAM ACTIVE.');
    };

    ws.onmessage = (event) => {
      frameCount++;
      try {
        const frame = JSON.parse(event.data);
        handleTelemetryFrame(frame);
      } catch (err) {
        console.error('Failed to parse frame JSON:', err);
      }
    };

    ws.onclose = () => {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectWebSocket, 2000);
    };
  }

  function handleTelemetryFrame(f) {
    const mpu = f.mpu6050;
    const health = f.health;
    const flags = f.flags;

    // Badges
    if (badgeSource) {
      if (f.simulated) {
        badgeSource.textContent = 'SIMULATION ACTIVE';
        badgeSource.className = 'badge badge-sim';
      } else {
        badgeSource.textContent = 'HARDWARE LINKED';
        badgeSource.className = 'badge badge-hardware';
      }
    }

    if (flags.anomaly_active) {
      badgeAlert.textContent = 'ANOMALY DETECTED';
      badgeAlert.className = 'badge badge-status-alert';
      if (!prevAnomalyState) {
        terminal.crit(`ANOMALY TRIGGERED [Code 0x${flags.error_code.toString(16).toUpperCase()}] Status: ${mpu.status}`);
        refreshAnomaliesList();
      }
    } else {
      badgeAlert.textContent = 'NOMINAL';
      badgeAlert.className = 'badge badge-status-online';
      if (prevAnomalyState) {
        terminal.sys('TELEMETRY STABILIZED. RECOVERY VERIFIED.');
        refreshAnomaliesList();
      }
    }
    prevAnomalyState = flags.anomaly_active;

    // Push into charts
    accelChart.pushPoint({
      ax: mpu.accel_x,
      ay: mpu.accel_y,
      az: mpu.accel_z,
      mag: mpu.accel_mag,
    });

    gyroChart.pushPoint({
      gx: mpu.gyro_x,
      gy: mpu.gyro_y,
      gz: mpu.gyro_z,
    });

    // Digital readouts
    if (elSeq) elSeq.textContent = f.seq;
    if (elUptime) elUptime.textContent = `${(health.uptime_ms / 1000).toFixed(1)}s`;
    if (elAx) elAx.textContent = mpu.accel_x.toFixed(2);
    if (elAy) elAy.textContent = mpu.accel_y.toFixed(2);
    if (elAz) elAz.textContent = mpu.accel_z.toFixed(2);
    if (elAmag) elAmag.textContent = mpu.accel_mag.toFixed(2);
    if (elGx) elGx.textContent = mpu.gyro_x.toFixed(1);
    if (elGy) elGy.textContent = mpu.gyro_y.toFixed(1);
    if (elGz) elGz.textContent = mpu.gyro_z.toFixed(1);
    if (elTemp) elTemp.textContent = mpu.temp_c.toFixed(1);
    if (elHeap) elHeap.textContent = `${Math.round(health.free_heap / 1024)} KB`;
    if (elVcc) elVcc.textContent = `${(health.vcc_mv / 1000).toFixed(2)} V`;
  }

  // Connect on load
  connectWebSocket();

  // ========================================================
  // HARDWARE SERIAL LINK CONTROLS
  // ========================================================

  window.refreshSerialPorts = async () => {
    try {
      const res = await fetch('/api/serial/ports');
      const data = await res.json();
      serialPortSelect.innerHTML = '<option value="sim">VIRTUAL SIMULATOR (10 Hz)</option>';
      data.ports.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.port;
        opt.textContent = `${p.port} (${p.description})`;
        serialPortSelect.appendChild(opt);
      });
      terminal.info(`Scanned COM ports: ${data.ports.length} physical port(s) detected.`);
    } catch (err) {
      terminal.warn(`Failed scanning serial ports: ${err.message}`);
    }
  };

  window.toggleSerialConnection = async () => {
    const selected = serialPortSelect.value;
    const baud = parseInt(baudRateSelect.value) || 115200;

    if (selected === 'sim') {
      await fetch('/api/serial/disconnect', { method: 'POST' });
      btnToggleLink.textContent = 'CONNECT SERIAL';
      indicatorLink.style.background = 'var(--amber-warning)';
      terminal.sys('SERIAL DISENGAGED. VIRTUAL SIMULATOR ACTIVE.');
    } else {
      const res = await fetch('/api/serial/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: selected, baud }),
      });
      const data = await res.json();
      if (data.ok) {
        btnToggleLink.textContent = 'DISCONNECT';
        indicatorLink.style.background = 'var(--phosphor-green)';
        terminal.sys(`LINKING TO PHYSICAL PORT: ${selected} @ ${baud} bps...`);
      } else {
        terminal.crit(`Connection failed: ${data.message}`);
      }
    }
  };

  // ========================================================
  // ANOMALY MATRIX & GHOST TRACE FORENSICS
  // ========================================================

  window.triggerScenario = async (scenarioName, durationSec) => {
    terminal.warn(`DISPATCHING SCENARIO INJECTION: ${scenarioName.toUpperCase()}...`);
    try {
      const res = await fetch('/api/simulator/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioName, duration_sec: durationSec }),
      });
      const data = await res.json();
      if (data.ok) {
        terminal.info(`Scenario ${scenarioName} active for ${data.duration_sec}s`);
      }
    } catch (err) {
      terminal.crit(`API request failure: ${err.message}`);
    }
  };

  window.resetScenario = async () => {
    terminal.info('RESETTING SIMULATOR TO NOMINAL BASELINE...');
    try {
      await fetch('/api/simulator/reset', { method: 'POST' });
      terminal.sys('BASELINE RESTORED.');
    } catch (err) {
      terminal.crit(`Reset failed: ${err.message}`);
    }
  };

  window.refreshAnomaliesList = async () => {
    try {
      const res = await fetch('/api/anomalies');
      const data = await res.json();
      const listEl = document.getElementById('trace-events-list');
      if (!listEl) return;

      if (!data.events || data.events.length === 0) {
        listEl.innerHTML = '<div style="color: var(--text-muted); padding: 8px;">No anomaly events recorded yet. Trigger a scenario to generate evidence.</div>';
        return;
      }

      listEl.innerHTML = '';
      data.events.forEach(ev => {
        const card = document.createElement('div');
        const sevClass = ev.severity === 'CRITICAL' ? 'crit' : 'warn';
        card.className = `event-card ${sevClass}`;
        card.innerHTML = `
          <div class="event-card-top">
            <span>${ev.title}</span>
            <span>${ev.is_active ? 'ACTIVE' : 'RECOVERED'}</span>
          </div>
          <div class="event-card-detail">
            ID: ${ev.event_id} | Onset: Frame #${ev.seq_onset} | Trace: ${ev.trace_length} samples
          </div>
        `;
        card.onclick = () => selectAnomalyEvent(ev.event_id);
        listEl.appendChild(card);
      });
    } catch (err) {
      console.error('Error refreshing anomalies:', err);
    }
  };

  window.selectAnomalyEvent = async (eventId) => {
    selectedEventId = eventId;
    try {
      const res = await fetch(`/api/anomalies/${eventId}/trace`);
      const data = await res.json();
      const detailView = document.getElementById('trace-detail-view');
      const statsEl = document.getElementById('trace-detail-stats');
      const titleEl = document.getElementById('trace-detail-title');

      if (detailView && statsEl) {
        detailView.style.display = 'block';
        titleEl.textContent = `FORENSIC EVIDENCE: ${data.title} [${data.event_id}]`;
        const st = data.trace_summary_stats || {};
        statsEl.innerHTML = `
          <div>Samples: <b>${st.samples || 0}</b></div>
          <div>Peak Accel: <b>${st.accel_mag_max || 0} m/s²</b></div>
          <div>Min Accel: <b>${st.accel_mag_min || 0} m/s²</b></div>
          <div>Max Angular Rate: <b>${st.gyro_max_rate || 0} °/s</b></div>
          <div>Die Temp: <b>${st.temp_max || 0} °C</b></div>
          <div>Supply Rail: <b>${st.vcc_min || 0} mV</b></div>
        `;
      }
    } catch (err) {
      terminal.crit(`Failed loading trace for ${eventId}: ${err.message}`);
    }
  };

  // ========================================================
  // AI INTERROGATION
  // ========================================================

  window.refreshAiStatus = async () => {
    try {
      const res = await fetch('/api/ai/status');
      const data = await res.json();
      const el = document.getElementById('ai-active-mode');
      if (el) el.textContent = data.active_mode;
    } catch (err) {
      console.error('Failed refreshing AI status:', err);
    }
  };

  window.interrogateSelectedEvent = async () => {
    if (!selectedEventId) {
      terminal.warn('Please select an anomaly event in Ghost Trace first.');
      return;
    }
    switchTab('tab-ai');
    const resultContainer = document.getElementById('ai-result-container');
    resultContainer.innerHTML = '<div style="color: var(--cyan-accent); font-size: 11px;">SYNTHESIZING PHYSICAL FORENSIC EXPLANATION...</div>';

    try {
      const res = await fetch(`/api/ai/interrogate/${selectedEventId}`, { method: 'POST' });
      const exp = await res.json();

      let hypHtml = '';
      (exp.hypotheses || []).forEach(h => {
        hypHtml += `
          <div style="margin-bottom: 6px;">
            <b style="color: var(--text-bright);">${h.rank}. ${h.title}</b> (${h.confidence_pct}% Confidence - ${h.probability})
            <div style="color: var(--text-dim); font-size: 10px;">${h.reasoning}</div>
          </div>
        `;
      });

      let obsHtml = (exp.observations || []).map(o => `<li>${o}</li>`).join('');
      let testHtml = (exp.recommended_tests || []).map(t => `<li>${t}</li>`).join('');
      let uncertHtml = (exp.uncertainties || []).map(u => `<li>${u}</li>`).join('');

      resultContainer.innerHTML = `
        <div class="ai-meta-bar">
          <span>EVENT: ${exp.event_id}</span>
          <span>PROVIDER: ${exp.provider} (${exp.model})</span>
          <span>LATENCY: ${exp.latency_ms} ms</span>
        </div>
        <div style="font-size: 12px; font-weight: bold; color: var(--phosphor-green);">${exp.summary}</div>
        
        <div class="ai-section-title">1. OBSERVED EVIDENCE (PHYSICAL FACTS)</div>
        <ul class="ai-list">${obsHtml}</ul>

        <div class="ai-section-title">2. PHYSICAL HYPOTHESES & ROOT CAUSE</div>
        <div style="margin-left: 6px;">${hypHtml}</div>

        <div class="ai-section-title">3. RECOMMENDED ENGINEERING BENCH TESTS</div>
        <ul class="ai-list">${testHtml}</ul>

        ${uncertHtml ? `<div class="ai-section-title">4. UNCERTAINTIES</div><ul class="ai-list">${uncertHtml}</ul>` : ''}
      `;
      terminal.sys(`AI FORENSIC REPORT GENERATED FOR ${exp.event_id} VIA ${exp.provider}.`);
    } catch (err) {
      resultContainer.innerHTML = `<div style="color: var(--red-alert);">Interrogation failed: ${err.message}</div>`;
    }
  };

  // ========================================================
  // DIGITAL AFTERLIFE RECORDING & REPLAY
  // ========================================================

  let isRecording = false;

  window.toggleRecording = async () => {
    const btn = document.getElementById('btn-record');
    const label = document.getElementById('record-status-label');
    const ind = document.getElementById('indicator-recording');

    if (!isRecording) {
      const res = await fetch('/api/sessions/record/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_name: 'ghost_session' }),
      });
      const data = await res.json();
      if (data.ok) {
        isRecording = true;
        btn.textContent = 'STOP REC';
        label.textContent = 'RECORDING...';
        label.style.color = 'var(--red-alert)';
        ind.style.background = 'var(--red-alert)';
        terminal.crit(`SESSION RECORDER ENGAGED: ${data.session_id}`);
      }
    } else {
      const res = await fetch('/api/sessions/record/stop', { method: 'POST' });
      const data = await res.json();
      isRecording = false;
      btn.textContent = 'REC SESSION';
      label.textContent = 'IDLE';
      label.style.color = 'var(--text-dim)';
      ind.style.background = 'var(--text-dim)';
      terminal.sys(`RECORDING CONCLUDED. Saved ${data.summary?.frames_recorded || 0} frames.`);
      refreshSessionsList();
    }
  };

  window.refreshSessionsList = async () => {
    try {
      const res = await fetch('/api/sessions');
      const data = await res.json();
      const sel = document.getElementById('replay-session-select');
      if (!sel) return;
      sel.innerHTML = '';
      (data.sessions || []).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.session_id;
        opt.textContent = `${s.session_id} (${Math.round(s.size_bytes / 1024)} KB)`;
        sel.appendChild(opt);
      });
    } catch (err) {
      console.error('Error refreshing sessions:', err);
    }
  };

  window.loadReplaySession = async () => {
    const sel = document.getElementById('replay-session-select');
    if (!sel || !sel.value) return;
    try {
      const res = await fetch('/api/sessions/replay/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sel.value }),
      });
      const data = await res.json();
      if (data.ok) {
        document.getElementById('replay-progress-text').textContent = `Loaded ${data.frames_loaded} frames from ${data.session_id}`;
        terminal.sys(`SESSION LOADED FOR REPLAY: ${data.session_id} (${data.frames_loaded} frames)`);
      }
    } catch (err) {
      terminal.crit(`Failed loading session replay: ${err.message}`);
    }
  };

  window.playReplay = async () => {
    await fetch('/api/sessions/replay/play', { method: 'POST' });
    document.getElementById('replay-progress-text').textContent = 'Playback: STREAMING REPLAY...';
    terminal.sys('DIGITAL AFTERLIFE REPLAY PLAYING.');
  };

  window.pauseReplay = async () => {
    await fetch('/api/sessions/replay/pause', { method: 'POST' });
    document.getElementById('replay-progress-text').textContent = 'Playback: PAUSED';
  };

  window.stepReplay = async () => {
    await fetch('/api/sessions/replay/pause', { method: 'POST' });
    // Single step
    terminal.info('REPLAY: STEPPED 1 FRAME');
  };

  window.changeReplaySpeed = async (spd) => {
    await fetch('/api/sessions/replay/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed: parseFloat(spd) }),
    });
    terminal.info(`Replay speed set to ${spd}x`);
  };

  // ========================================================
  // TAB NAVIGATION
  // ========================================================

  window.switchTab = (tabId) => {
    const tabs = ['tab-live', 'tab-trace', 'tab-ai', 'tab-replay'];
    tabs.forEach(t => {
      const view = document.getElementById(`view-${t}`);
      if (view) view.style.display = t === tabId ? 'flex' : 'none';
    });

    const btns = document.querySelectorAll('.nav-tabs .tab-btn');
    btns.forEach(b => {
      b.classList.remove('active');
      if (b.getAttribute('onclick')?.includes(tabId)) {
        b.classList.add('active');
      }
    });

    if (tabId === 'tab-live') {
      accelChart.resize();
      gyroChart.resize();
    } else if (tabId === 'tab-trace') {
      refreshAnomaliesList();
    } else if (tabId === 'tab-ai') {
      refreshAiStatus();
    } else if (tabId === 'tab-replay') {
      refreshSessionsList();
    }
  };
});
