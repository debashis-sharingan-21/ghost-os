/**
 * GHOST.OS — Screen One: 3D Ghost Gate Experience
 * Genuine procedural WebGL 3D Skull with lighting, eye lights, particles, and interaction.
 * Zero external network dependencies (uses locally bundled three.min.js).
 */

class GhostGate3D {
  constructor(canvasContainerId, options = {}) {
    this.container = document.getElementById(canvasContainerId);
    if (!this.container) {
      console.warn(`Container #${canvasContainerId} not found`);
      return;
    }

    this.onAwakenComplete = options.onAwakenComplete || (() => {});
    this.isAwakening = false;
    this.isRunning = false;
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    this.init();
  }

  init() {
    if (typeof THREE === 'undefined') {
      console.error('Three.js not loaded. Falling back to 2D.');
      return;
    }

    // 1. Scene & Camera
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x020602, 0.08);

    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;

    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 0, 7.5);

    // 2. Renderer with graceful WebGL fallback
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
      this.renderer.setSize(w, h);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.container.appendChild(this.renderer.domElement);
    } catch (e) {
      console.warn('WebGL initialization failed, falling back to 2D display:', e);
      this.container.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#00ff66;font-family:var(--font-mono, monospace);text-align:center;">
          <div style="font-size:64px;filter:drop-shadow(0 0 12px #00ff66);animation:pulse-amber 1.5s infinite alternate;">☠</div>
          <div style="font-size:11px;margin-top:10px;color:#88aa88;letter-spacing:1px;">[2D AUTONOMOUS CARRIER ENGAGED // WEBGL ACCELERATOR BYPASS]</div>
        </div>
      `;
      return;
    }

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0x003311, 1.2);
    this.scene.add(ambientLight);

    this.scanLight = new THREE.SpotLight(0x00ff66, 3.5, 20, Math.PI / 4, 0.5, 1);
    this.scanLight.position.set(0, 4, 5);
    this.scene.add(this.scanLight);

    // 4. Procedural 3D Skull Group
    this.skullGroup = new THREE.Group();
    this.scene.add(this.skullGroup);

    this.buildProceduralSkull();
    this.buildCyberParticles();
    this.buildScannerPlane();

    // 5. Events
    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('mousemove', (e) => this.onMouseMove(e));

    this.isRunning = true;
    this.clock = new THREE.Clock();
    this.animate();
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
    const skullMat = new THREE.MeshStandardMaterial({
      color: 0x021606,
      emissive: 0x003311,
      roughness: 0.3,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85,
    });
    this.skullMesh = new THREE.Mesh(craniumGeom, skullMat);
    this.skullGroup.add(this.skullMesh);

    // Glowing Neon Wireframe overlay
    const wireGeom = new THREE.WireframeGeometry(craniumGeom);
    this.wireMat = new THREE.LineBasicMaterial({
      color: 0x00ff66,
      transparent: true,
      opacity: 0.75,
      linewidth: 1.5,
    });
    this.wireframeMesh = new THREE.LineSegments(wireGeom, this.wireMat);
    this.skullGroup.add(this.wireframeMesh);

    // Living Eye Sockets: PointLights & Emissive Spheres
    const eyeGeom = new THREE.SphereGeometry(0.16, 16, 16);
    this.eyeMat = new THREE.MeshBasicMaterial({ color: 0x70ff9c });

    this.leftEye = new THREE.Mesh(eyeGeom, this.eyeMat);
    this.leftEye.position.set(-0.62, 0.15, 1.05);
    this.leftLight = new THREE.PointLight(0x00ff66, 2.5, 4);
    this.leftEye.add(this.leftLight);
    this.skullGroup.add(this.leftEye);

    this.rightEye = new THREE.Mesh(eyeGeom, this.eyeMat);
    this.rightEye.position.set(0.62, 0.15, 1.05);
    this.rightLight = new THREE.PointLight(0x00ff66, 2.5, 4);
    this.rightEye.add(this.rightLight);
    this.skullGroup.add(this.rightEye);

    // Mandibular Teeth Matrix (distinct phosphor tooth pegs)
    const teethGeom = new THREE.BoxGeometry(0.12, 0.22, 0.14);
    const teethMat = new THREE.MeshStandardMaterial({ color: 0x00ff66, emissive: 0x00993d, roughness: 0.4 });
    this.teethGroup = new THREE.Group();
    for (let t = -3; t <= 3; t++) {
      if (t === 0) continue;
      const tooth = new THREE.Mesh(teethGeom, teethMat);
      tooth.position.set(t * 0.15, -1.15, 1.0 - Math.abs(t) * 0.08);
      this.teethGroup.add(tooth);
    }
    this.skullGroup.add(this.teethGroup);
  }

  buildCyberParticles() {
    const particleCount = 280;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const radius = 2.0 + Math.random() * 3.5;
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

    const pMat = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });

    this.particles = new THREE.Points(geom, pMat);
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
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  onMouseMove(e) {
    this.mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
    this.mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
  }

  awaken() {
    if (this.isAwakening) return;
    this.isAwakening = true;

    // Flare eye lights
    this.leftLight.intensity = 8.0;
    this.rightLight.intensity = 8.0;
    this.leftEye.scale.set(1.6, 1.6, 1.6);
    this.rightEye.scale.set(1.6, 1.6, 1.6);
    this.wireMat.opacity = 1.0;

    // Rapid camera dolly and scale convergence
    const startTime = performance.now();
    const duration = 900; // ms

    const animateAwaken = (now) => {
      const elapsed = now - startTime;
      const p = Math.min(1.0, elapsed / duration);

      // Ease in camera
      this.camera.position.z = 7.5 - p * 3.8;
      this.skullGroup.rotation.y += 0.08 * (1 - p);
      this.scanPlane.position.y = -2 + p * 4;

      if (p < 1.0) {
        requestAnimationFrame(animateAwaken);
      } else {
        this.onAwakenComplete();
      }
    };
    requestAnimationFrame(animateAwaken);
  }

  animate() {
    if (!this.isRunning) return;
    requestAnimationFrame(() => this.animate());

    const t = this.clock.getElapsedTime();

    // Damped mouse tracking parallax
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

    if (!this.isAwakening) {
      this.skullGroup.rotation.y = this.mouse.x * 0.45 + Math.sin(t * 0.8) * 0.08;
      this.skullGroup.rotation.x = -this.mouse.y * 0.35 + Math.cos(t * 0.6) * 0.05;
      this.skullGroup.position.y = Math.sin(t * 1.5) * 0.08;

      // Laser scanner sweep up and down
      this.scanPlane.position.y = Math.sin(t * 1.8) * 1.8;
      this.scanLight.position.y = this.scanPlane.position.y + 1.5;

      // Subtle living eye blink
      const blinkCycle = Math.sin(t * 2.5);
      if (blinkCycle > 0.96) {
        this.leftEye.scale.y = 0.1;
        this.rightEye.scale.y = 0.1;
      } else {
        this.leftEye.scale.y = 1.0;
        this.rightEye.scale.y = 1.0;
      }

      // Rotate particle nebula
      if (this.particles) {
        this.particles.rotation.y = t * 0.05;
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
      this.animate();
    }
  }
}
