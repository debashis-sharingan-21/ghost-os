/**
 * GHOST.OS — 3D Holographic Ghost Engine (Screen One: Ghost Gate & Command Center Core)
 * Procedural WebGL 3D Skull with lighting, eye sockets, cyber particles, and event-driven awakening.
 * Zero external dependencies (uses locally bundled three.min.js).
 */

class GhostSkull3D {
  constructor(canvasContainerId, options = {}) {
    this.container = document.getElementById(canvasContainerId);
    if (!this.container) {
      console.warn(`Container #${canvasContainerId} not found`);
      return;
    }

    this.options = options;
    this.isGate = options.isGate ?? false;
    this.onAwakenComplete = options.onAwakenComplete || (() => {});
    this.isAwakening = false;
    this.isRunning = false;
    this.cameraZ = options.cameraZ || (this.isGate ? 7.5 : 5.8);
    this.scaleFactor = options.scale || (this.isGate ? 1.0 : 0.85);

    // Mouse tracking
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    // Dynamic Animation & Scenario State
    this.animState = 'dormant'; // 'dormant' | 'awakening' | 'reaction' | 'narrative'
    this.currentScenario = 'NORMAL';
    this.scenarioTimer = 0;
    this.scenarioDuration = 1.6; // seconds
    this.scenarioStartTime = 0;

    // Offsets & dynamics
    this.dispOffsetY = 0;
    this.targetOffsetY = 0;
    this.spinVelY = 0;
    this.spinVelX = 0;
    this.spinVelZ = 0;
    this.shakeIntensity = 0;
    this.freezeActive = false;
    this.dimFactor = 1.0;
    this.targetDimFactor = 1.0;
    this.scalePulse = 1.0;
    this.targetScalePulse = 1.0;

    // Particle velocity modifiers
    this.particleBurstSpeed = 0;

    // Material base colors
    this.COLOR_PHOSPHOR_GREEN = 0x00ff66;
    this.COLOR_EYE_GREEN = 0x70ff9c;
    this.COLOR_ALERT_RED = 0xff2222;
    this.COLOR_AMBER_SPIKE = 0xffaa00;
    this.COLOR_CYAN_RECOVER = 0x00ffff;

    // Reduced motion preference
    this.reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.init();
  }

  init() {
    if (typeof THREE === 'undefined') {
      console.error('Three.js not loaded. Falling back to 2D.');
      this.render2DFallback();
      return;
    }

    // 1. Scene & Camera
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x020602, this.isGate ? 0.08 : 0.12);

    const w = this.container.clientWidth || 300;
    const h = this.container.clientHeight || 200;

    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 0, this.cameraZ);

    // 2. Renderer with graceful WebGL fallback
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
      this.renderer.setSize(w, h);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.container.appendChild(this.renderer.domElement);
    } catch (e) {
      console.warn('WebGL initialization failed, falling back to 2D display:', e);
      this.render2DFallback();
      return;
    }

    // 3. Lighting
    this.ambientLight = new THREE.AmbientLight(0x003311, 1.4);
    this.scene.add(this.ambientLight);

    this.scanLight = new THREE.SpotLight(0x00ff66, 3.5, 20, Math.PI / 4, 0.5, 1);
    this.scanLight.position.set(0, 4, 5);
    this.scene.add(this.scanLight);

    // 4. Procedural 3D Skull Group
    this.skullGroup = new THREE.Group();
    this.skullGroup.scale.setScalar(this.scaleFactor);
    this.scene.add(this.skullGroup);

    this.buildProceduralSkull();
    this.buildCyberParticles();
    if (this.isGate) {
      this.buildScannerPlane();
    }

    // 5. Events
    window.addEventListener('resize', () => this.onResize());
    if (this.isGate) {
      window.addEventListener('mousemove', (e) => this.onMouseMove(e));
    }

    this.clock = new THREE.Clock();
    this.isRunning = true;
    this.animate();
  }

  render2DFallback() {
    this.container.innerHTML = `
      <div class="ghost-2d-fallback" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#00ff66;font-family:var(--font-mono, monospace);text-align:center;">
        <div id="fallback-skull-glyph" style="font-size:48px;filter:drop-shadow(0 0 10px #00ff66);animation:crt-flicker 1.5s infinite alternate;">☠</div>
        <div id="fallback-status-text" style="font-size:10px;margin-top:6px;color:#88aa88;letter-spacing:1px;">[2D AUTONOMOUS CARRIER // WEBGL BYPASS]</div>
      </div>
    `;
  }

  buildProceduralSkull() {
    // 3D Cranium Base Mesh (Deformed Icosahedron for cyber-faceted surface)
    const craniumGeom = new THREE.IcosahedronGeometry(1.6, 2);
    const pos = craniumGeom.attributes.position;

    // Sculpt cranium into anatomical skull proportions
    for (let i = 0; i < pos.count; i++) {
      let x = pos.getX(i);
      let y = pos.getY(i);
      let z = pos.getZ(i);

      // Flatten sides (temporal fossa)
      if (Math.abs(x) > 0.8) x *= 0.82;

      // Cheekbones (zygomatic arch)
      if (y > -0.5 && y < 0.2 && Math.abs(x) > 0.9) x *= 1.15;

      // Mandible narrowing (jaw & chin)
      if (y < -0.4) {
        x *= 0.7;
        if (z > 0) z *= 0.85;
      }

      // Orbital indentation (eye sockets)
      if (y > -0.1 && y < 0.5 && Math.abs(x) > 0.35 && Math.abs(x) < 0.95 && z > 0.8) {
        z *= 0.65;
        y *= 0.9;
      }

      // Nasal depression
      if (y > -0.4 && y < 0.0 && Math.abs(x) < 0.35 && z > 1.0) {
        z *= 0.75;
      }

      pos.setXYZ(i, x, y, z);
    }
    craniumGeom.computeVertexNormals();

    // Solid inner face material (semi-transparent cyber green glass)
    this.skullMat = new THREE.MeshStandardMaterial({
      color: 0x021606,
      emissive: 0x003311,
      roughness: 0.3,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85,
    });
    this.skullMesh = new THREE.Mesh(craniumGeom, this.skullMat);
    this.skullGroup.add(this.skullMesh);

    // Glowing Neon Wireframe overlay
    const wireGeom = new THREE.WireframeGeometry(craniumGeom);
    this.wireMat = new THREE.LineBasicMaterial({
      color: this.COLOR_PHOSPHOR_GREEN,
      transparent: true,
      opacity: 0.75,
      linewidth: 1.5,
    });
    this.wireframeMesh = new THREE.LineSegments(wireGeom, this.wireMat);
    this.skullGroup.add(this.wireframeMesh);

    // Living Eye Sockets: PointLights & Emissive Spheres
    const eyeGeom = new THREE.SphereGeometry(0.16, 16, 16);
    this.eyeMat = new THREE.MeshBasicMaterial({ color: this.COLOR_EYE_GREEN });

    this.leftEye = new THREE.Mesh(eyeGeom, this.eyeMat);
    this.leftEye.position.set(-0.62, 0.15, 1.05);
    this.leftLight = new THREE.PointLight(this.COLOR_PHOSPHOR_GREEN, 2.5, 4);
    this.leftEye.add(this.leftLight);
    this.skullGroup.add(this.leftEye);

    this.rightEye = new THREE.Mesh(eyeGeom, this.eyeMat);
    this.rightEye.position.set(0.62, 0.15, 1.05);
    this.rightLight = new THREE.PointLight(this.COLOR_PHOSPHOR_GREEN, 2.5, 4);
    this.rightEye.add(this.rightLight);
    this.skullGroup.add(this.rightEye);

    // Mandibular Teeth Matrix (distinct phosphor tooth pegs)
    const teethGeom = new THREE.BoxGeometry(0.12, 0.22, 0.14);
    this.teethMat = new THREE.MeshStandardMaterial({
      color: this.COLOR_PHOSPHOR_GREEN,
      emissive: 0x00993d,
      roughness: 0.4,
    });
    this.teethGroup = new THREE.Group();
    for (let t = -3; t <= 3; t++) {
      if (t === 0) continue;
      const tooth = new THREE.Mesh(teethGeom, this.teethMat);
      tooth.position.set(t * 0.15, -1.15, 1.0 - Math.abs(t) * 0.08);
      this.teethGroup.add(tooth);
    }
    this.skullGroup.add(this.teethGroup);
  }

  buildCyberParticles() {
    const particleCount = this.isGate ? 280 : 180;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    this.particleBaseRadii = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const radius = 1.8 + Math.random() * 3.0;
      this.particleBaseRadii[i] = radius;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      colors[i * 3] = 0.0;
      colors[i * 3 + 1] = Math.random() > 0.3 ? 1.0 : 0.7;
      colors[i * 3 + 2] = Math.random() > 0.6 ? 0.8 : 0.2;
    }

    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    this.pMat = new THREE.PointsMaterial({
      size: this.isGate ? 0.05 : 0.04,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });

    this.particles = new THREE.Points(geom, this.pMat);
    this.scene.add(this.particles);
  }

  buildScannerPlane() {
    const planeGeom = new THREE.PlaneGeometry(6, 0.04);
    const planeMat = new THREE.MeshBasicMaterial({
      color: 0x00ffff,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
    });
    this.scanPlane = new THREE.Mesh(planeGeom, planeMat);
    this.scanPlane.position.set(0, 0, 1.2);
    this.scene.add(this.scanPlane);
  }

  onResize() {
    if (!this.renderer || !this.camera || !this.container) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  onMouseMove(e) {
    this.mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
    this.mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
  }

  /**
   * Stage 1 Full Awakening Sequence
   */
  awaken() {
    if (this.isAwakening) return;
    this.isAwakening = true;

    // Flare eye lights
    if (this.leftLight) this.leftLight.intensity = 8.0;
    if (this.rightLight) this.rightLight.intensity = 8.0;
    if (this.leftEye) this.leftEye.scale.set(1.6, 1.6, 1.6);
    if (this.rightEye) this.rightEye.scale.set(1.6, 1.6, 1.6);
    if (this.wireMat) this.wireMat.opacity = 1.0;

    const startTime = performance.now();
    const duration = 900; // ms

    const animateAwaken = (now) => {
      const elapsed = now - startTime;
      const p = Math.min(1.0, elapsed / duration);

      this.camera.position.z = this.cameraZ - p * (this.cameraZ * 0.5);
      this.skullGroup.rotation.y += 0.08 * (1 - p);
      if (this.scanPlane) this.scanPlane.position.y = -2 + p * 4;

      if (p < 1.0) {
        requestAnimationFrame(animateAwaken);
      } else {
        this.onAwakenComplete();
      }
    };
    requestAnimationFrame(animateAwaken);
  }

  /**
   * Event-Driven Anomaly Awakening & Scenario Reaction
   * @param {string} scenarioType - 'FREE_FALL', 'HIGH_G_IMPACT', 'TUMBLE_SPIN', 'SENSOR_FREEZE', 'THERMAL_SPIKE', 'BROWNOUT', 'NORMAL'
   * @param {string} severity - 'CRITICAL', 'WARNING', 'INFO'
   * @param {string} eventLabel - Display title
   * @param {string} narrativeMsg - Forensic narrative subtitle
   */
  triggerAnomaly(scenarioType, severity = 'CRITICAL', eventLabel = '', narrativeMsg = '') {
    if (!this.renderer) {
      this.update2DFallback(scenarioType, severity, eventLabel, narrativeMsg);
      return;
    }

    const type = (scenarioType || 'NORMAL').toUpperCase();
    this.currentScenario = type;
    this.scenarioStartTime = performance.now();
    this.scenarioDuration = type === 'NORMAL' ? 0.8 : (type === 'HIGH_G_IMPACT' ? 1.4 : 1.8);
    this.animState = type === 'NORMAL' ? 'dormant' : 'reaction';

    // 1. Initial Perspective Emergence / Pulse
    if (!this.reducedMotion) {
      this.targetScalePulse = type === 'NORMAL' ? 1.0 : 1.25;
      this.particleBurstSpeed = type === 'NORMAL' ? 0 : 2.5;
    }

    // 2. Trigger controlled CRT scanline pulse & glitch
    this.triggerScreenPulse(type, severity);

    // 3. Scenario-Specific Reactions
    switch (type) {
      case 'FREE_FALL':
        // Downward drop and float recovery
        this.targetOffsetY = this.reducedMotion ? 0 : -0.9;
        this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.9, 3.5);
        this.freezeActive = false;
        break;

      case 'HIGH_G_IMPACT':
        // Severe shockwave, red alert flash, sharp camera jolt
        this.shakeIntensity = this.reducedMotion ? 0 : 0.22;
        this.setMaterialsColor(this.COLOR_ALERT_RED, 1.0, 8.0);
        this.freezeActive = false;
        break;

      case 'TUMBLE_SPIN':
      case 'HIGH_ANGULAR_RATE':
        // Accelerated tumbling rotation across y, x, and z axes
        this.spinVelY = this.reducedMotion ? 0.05 : 0.45;
        this.spinVelX = this.reducedMotion ? 0 : 0.15;
        this.spinVelZ = this.reducedMotion ? 0 : 0.12;
        this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.85, 4.0);
        this.freezeActive = false;
        break;

      case 'SENSOR_FREEZE':
      case 'SEQUENCE_GAP':
        // Lock skull in place; fragmented intermittent flicker
        this.freezeActive = true;
        this.spinVelY = 0;
        this.spinVelX = 0;
        this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.85, 3.0);
        break;

      case 'THERMAL_SPIKE':
        // Transition glow from phosphor green to burning hot amber
        this.setMaterialsColor(this.COLOR_AMBER_SPIKE, 0.95, 5.0, 0x442200);
        this.targetScalePulse = this.reducedMotion ? 1.0 : 1.15;
        this.freezeActive = false;
        break;

      case 'BROWNOUT':
        // Progressive voltage droop & dimming
        this.targetOffsetY = this.reducedMotion ? 0 : -0.3;
        this.targetDimFactor = 0.18;
        this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.25, 0.4);
        this.freezeActive = false;
        break;

      case 'NORMAL':
      default:
        // Smooth restoration to nominal green holographic appearance
        this.targetOffsetY = 0;
        this.targetDimFactor = 1.0;
        this.targetScalePulse = 1.0;
        this.spinVelY = 0;
        this.spinVelX = 0;
        this.spinVelZ = 0;
        this.shakeIntensity = 0;
        this.freezeActive = false;
        this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.75, 2.5, 0x003311);
        break;
    }

    // 4. Update HUD Overlays if present
    this.updateHud(type, severity, eventLabel, narrativeMsg);

    // 5. Schedule Return to Dormant State
    if (this.returnTimer) clearTimeout(this.returnTimer);
    if (type !== 'NORMAL') {
      this.returnTimer = setTimeout(() => {
        this.resetToDormant();
      }, this.scenarioDuration * 1000);
    }
  }

  /**
   * Reset skull smoothly to baseline dormant floating
   */
  resetToDormant() {
    this.animState = 'dormant';
    this.targetOffsetY = 0;
    this.targetDimFactor = 1.0;
    this.targetScalePulse = 1.0;
    this.shakeIntensity = 0;
    this.freezeActive = false;
    this.spinVelY = 0;
    this.spinVelX = 0;
    this.spinVelZ = 0;
    this.particleBurstSpeed = 0;
    this.setMaterialsColor(this.COLOR_PHOSPHOR_GREEN, 0.75, 2.5, 0x003311);
    this.updateHud('NOMINAL', 'INFO', 'DORMANT // CARRIER SYNCHRONIZED', '');
  }

  /**
   * Set forensic narrative banner with cyber text glow
   */
  setNarrative(text, durationMs = 2000, theme = 'cyan') {
    const banner = document.getElementById('ghost-hud-narrative');
    if (banner) {
      banner.textContent = text;
      banner.style.color = theme === 'cyan' ? 'var(--cyan-accent)' : 'var(--phosphor-green)';
      banner.style.textShadow = theme === 'cyan' ? '0 0 10px var(--cyan-accent)' : '0 0 10px var(--phosphor-green)';
      banner.classList.add('narrative-active');
    }

    if (this.narrativeTimer) clearTimeout(this.narrativeTimer);
    this.narrativeTimer = setTimeout(() => {
      if (banner && this.animState === 'dormant') {
        banner.textContent = 'CARRIER ACTIVE';
        banner.style.color = 'var(--text-dim)';
        banner.style.textShadow = 'none';
        banner.classList.remove('narrative-active');
      }
    }, durationMs);

    // Subtle eye socket glow response
    if (this.leftLight && this.rightLight) {
      const col = theme === 'cyan' ? this.COLOR_CYAN_RECOVER : this.COLOR_PHOSPHOR_GREEN;
      this.leftLight.color.setHex(col);
      this.rightLight.color.setHex(col);
      this.leftLight.intensity = 4.0;
      this.rightLight.intensity = 4.0;
    }
  }

  /**
   * Helper to set wireframe, eye lights, and skull material colors smoothly
   */
  setMaterialsColor(hexColor, wireOpacity = 0.75, lightIntensity = 2.5, emissiveHex = 0x003311) {
    if (this.wireMat) {
      this.wireMat.color.setHex(hexColor);
      this.wireMat.opacity = wireOpacity;
    }
    if (this.eyeMat) {
      this.eyeMat.color.setHex(hexColor);
    }
    if (this.leftLight && this.rightLight) {
      this.leftLight.color.setHex(hexColor);
      this.rightLight.color.setHex(hexColor);
      this.leftLight.intensity = lightIntensity;
      this.rightLight.intensity = lightIntensity;
    }
    if (this.skullMat) {
      this.skullMat.emissive.setHex(emissiveHex);
    }
    if (this.teethMat) {
      this.teethMat.color.setHex(hexColor);
    }
  }

  /**
   * Screen pulse & controlled scanline glitch
   */
  triggerScreenPulse(scenario, severity) {
    const pulseEl = document.getElementById('screen-pulse-overlay');
    if (!pulseEl) return;

    pulseEl.className = 'screen-pulse-overlay';
    if (this.reducedMotion) return;

    if (scenario === 'HIGH_G_IMPACT' || severity === 'CRITICAL') {
      pulseEl.classList.add('pulse-red');
    } else if (scenario === 'THERMAL_SPIKE') {
      pulseEl.classList.add('pulse-amber');
    } else if (scenario === 'FREE_FALL' || scenario === 'TUMBLE_SPIN') {
      pulseEl.classList.add('pulse-cyan');
    }

    setTimeout(() => {
      pulseEl.className = 'screen-pulse-overlay';
    }, 600);

    // Controlled holographic glitch on viewport
    const vp = document.getElementById('ghost-core-viewport') || this.container;
    if (vp) {
      vp.classList.add('hologram-glitch');
      setTimeout(() => vp.classList.remove('hologram-glitch'), 400);
    }
  }

  /**
   * Update floating HUD badges over 3D Ghost
   */
  updateHud(type, severity, label, narrative) {
    const tag = document.getElementById('ghost-hud-tag');
    const narr = document.getElementById('ghost-hud-narrative');
    const ind = document.getElementById('indicator-ghost-presence');

    if (tag) {
      if (type === 'NORMAL') {
        tag.textContent = 'NOMINAL';
        tag.className = 'ghost-hud-tag tag-nominal';
      } else {
        tag.textContent = `${severity || 'ALERT'} // ${label || type}`;
        tag.className = `ghost-hud-tag ${severity === 'CRITICAL' ? 'tag-crit' : 'tag-warn'}`;
      }
    }

    if (narr && narrative) {
      narr.textContent = narrative;
      narr.style.color = severity === 'CRITICAL' ? 'var(--red-alert)' : 'var(--amber-warning)';
      narr.style.textShadow = '0 0 8px currentColor';
    }

    if (ind) {
      if (type === 'NORMAL') {
        ind.style.background = 'var(--phosphor-green)';
        ind.style.boxShadow = '0 0 6px var(--phosphor-green)';
      } else if (severity === 'CRITICAL') {
        ind.style.background = 'var(--red-alert)';
        ind.style.boxShadow = '0 0 8px var(--red-alert)';
      } else {
        ind.style.background = 'var(--amber-warning)';
        ind.style.boxShadow = '0 0 8px var(--amber-warning)';
      }
    }
  }

  update2DFallback(scenario, severity, label, narrative) {
    const glyph = document.getElementById('fallback-skull-glyph');
    const txt = document.getElementById('fallback-status-text');
    if (glyph) {
      glyph.style.color = scenario === 'HIGH_G_IMPACT' ? '#ff3333' : (scenario === 'THERMAL_SPIKE' ? '#ffaa00' : '#00ff66');
    }
    if (txt) {
      txt.textContent = `[${severity} // ${label || scenario}] ${narrative || ''}`;
    }
    this.updateHud(scenario, severity, label, narrative);
  }

  animate() {
    if (!this.isRunning) return;
    requestAnimationFrame(() => this.animate());

    const dt = this.clock.getDelta();
    const t = this.clock.getElapsedTime();

    // Damped mouse tracking parallax
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

    // Smooth offsets and transitions
    this.dispOffsetY += (this.targetOffsetY - this.dispOffsetY) * 0.08;
    this.dimFactor += (this.targetDimFactor - this.dimFactor) * 0.1;
    this.scalePulse += (this.targetScalePulse - this.scalePulse) * 0.1;

    if (!this.isAwakening) {
      if (this.freezeActive) {
        // SENSOR FREEZE: Fragmented flicker (rapid square-wave opacity jitter)
        const flicker = Math.sin(t * 35) > 0 ? 0.9 : 0.15;
        if (this.wireMat) this.wireMat.opacity = flicker * this.dimFactor;
        if (this.leftLight) this.leftLight.intensity = flicker * 3.0 * this.dimFactor;
        if (this.rightLight) this.rightLight.intensity = flicker * 3.0 * this.dimFactor;
      } else {
        // Dormant / Active Floating Kinematics
        const floatY = Math.sin(t * 1.5) * 0.08 + this.dispOffsetY;
        const targetRotY = this.mouse.x * 0.45 + Math.sin(t * 0.8) * 0.08;
        const targetRotX = -this.mouse.y * 0.35 + Math.cos(t * 0.6) * 0.05;

        // Apply spin velocities (e.g. TUMBLE_SPIN) with smooth deceleration
        if (Math.abs(this.spinVelY) > 0.001) {
          this.skullGroup.rotation.y += this.spinVelY;
          this.spinVelY *= 0.95;
        } else {
          this.skullGroup.rotation.y += (targetRotY - this.skullGroup.rotation.y) * 0.06;
        }

        if (Math.abs(this.spinVelX) > 0.001) {
          this.skullGroup.rotation.x += this.spinVelX;
          this.spinVelX *= 0.95;
        } else {
          this.skullGroup.rotation.x += (targetRotX - this.skullGroup.rotation.x) * 0.06;
        }

        if (Math.abs(this.spinVelZ) > 0.001) {
          this.skullGroup.rotation.z += this.spinVelZ;
          this.spinVelZ *= 0.95;
        } else {
          this.skullGroup.rotation.z *= 0.9;
        }

        // High-G Impact Shudder / Shockwave Shake Decay
        let shakeX = 0;
        let shakeY = 0;
        if (this.shakeIntensity > 0.001) {
          shakeX = (Math.random() - 0.5) * this.shakeIntensity;
          shakeY = (Math.random() - 0.5) * this.shakeIntensity;
          this.shakeIntensity *= 0.88;
        }

        this.skullGroup.position.set(shakeX, floatY + shakeY, 0);

        // Perspective scale pulse (Emergence)
        const baseScale = this.scaleFactor * this.scalePulse;
        this.skullGroup.scale.setScalar(baseScale);

        // Living Eye Sockets subtle blink
        const blinkCycle = Math.sin(t * 2.5);
        const blinkScale = blinkCycle > 0.96 ? 0.1 : 1.0;
        if (this.leftEye) this.leftEye.scale.y = blinkScale;
        if (this.rightEye) this.rightEye.scale.y = blinkScale;

        // Laser scanner sweep up and down (if present)
        if (this.scanPlane && this.scanLight) {
          this.scanPlane.position.y = Math.sin(t * 1.8) * 1.8;
          this.scanLight.position.y = this.scanPlane.position.y + 1.5;
        }

        // Dimming factor application (e.g. BROWNOUT)
        if (this.wireMat && this.animState !== 'reaction') {
          this.wireMat.opacity = 0.75 * this.dimFactor;
        }
      }

      // Cyber particle dynamics & burst expansion
      if (this.particles) {
        this.particles.rotation.y = t * (0.05 + this.particleBurstSpeed * 0.1);
        if (this.particleBurstSpeed > 0.01) {
          this.particleBurstSpeed *= 0.93;
        }
      }
    }

    this.renderer.render(this.scene, this.camera);
  }

  pause() {
    this.isRunning = false;
  }

  resume() {
    if (!this.isRunning) {
      this.isRunning = true;
      this.clock.start();
      this.animate();
      this.onResize();
    }
  }
}

// Backward-compatible alias for existing GhostGate3D references
class GhostGate3D extends GhostSkull3D {
  constructor(canvasContainerId, options = {}) {
    super(canvasContainerId, { ...options, isGate: true });
  }
}
