/**
 * GHOST.OS — Main Application Orchestrator
 */

document.addEventListener('DOMContentLoaded', () => {
  const terminal = new GhostTerminal('terminal-console', 120);
  terminal.sys('GHOST.OS ACCESS TERMINAL INITIALIZED.');
  terminal.sys('PROTOCOL: ghost.v1 // SYSTEM TIME SYNCHRONIZED.');

  // Initialize Oscilloscopes
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

  // UI Element References
  const badgeSource = document.getElementById('badge-source');
  const badgeAlert = document.getElementById('badge-alert');
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
  const elSensorStatus = document.getElementById('stat-sensor-status');

  let lastFrameTime = performance.now();
  let frameCount = 0;
  let measuredHz = 10.0;
  let prevAnomalyState = false;

  // Rate calculator loop
  setInterval(() => {
    measuredHz = frameCount;
    frameCount = 0;
    if (elRate) elRate.textContent = `${measuredHz.toFixed(1)} HZ`;
  }, 1000);

  // WebSocket Telemetry Client
  let ws = null;
  let reconnectTimeout = null;

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    terminal.info(`Connecting telemetry stream: ${wsUrl}`);
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
      terminal.warn('Telemetry stream disconnected. Reconnecting in 2.0s...');
      clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
      terminal.crit('Telemetry transport error detected.');
    };
  }

  function handleTelemetryFrame(f) {
    const mpu = f.mpu6050;
    const health = f.health;
    const flags = f.flags;

    // Update Source Badge
    if (badgeSource) {
      if (f.simulated) {
        badgeSource.textContent = 'SIMULATION ACTIVE';
        badgeSource.className = 'badge badge-sim';
      } else {
        badgeSource.textContent = 'HARDWARE LINKED';
        badgeSource.className = 'badge badge-hardware';
      }
    }

    // Update Anomaly Status Badge
    if (flags.anomaly_active) {
      badgeAlert.textContent = 'ANOMALY DETECTED';
      badgeAlert.className = 'badge badge-status-alert';
      if (!prevAnomalyState) {
        terminal.crit(`ANOMALY TRIGGERED [Code 0x${flags.error_code.toString(16).toUpperCase()}] Status: ${mpu.status}`);
      }
    } else {
      badgeAlert.textContent = 'NOMINAL';
      badgeAlert.className = 'badge badge-status-online';
      if (prevAnomalyState) {
        terminal.sys('TELEMETRY STABILIZED. RECOVERY VERIFIED.');
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

    // Update digital stats
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
    if (elSensorStatus) elSensorStatus.textContent = mpu.status;
  }

  // Connect on boot
  connectWebSocket();

  // Scenario Trigger Handlers
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
      } else {
        terminal.crit(`Scenario injection rejected: ${data.detail || 'Unknown error'}`);
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
});
