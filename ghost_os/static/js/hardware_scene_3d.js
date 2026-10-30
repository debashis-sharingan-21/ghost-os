/**
 * GHOST.OS — Screen Two: 3D Hardware Awakening Scene
 * Real 3D interactive embedded system: ESP32-WROOM-32 + MPU6050 + I2C Signal Pulses.
 * Completely offline using local Three.js.
 */

class HardwareAwakening3D {
  constructor(canvasContainerId, options = {}) {
    this.container = document.getElementById(canvasContainerId);
    if (!this.container) {
      console.warn(`Container #${canvasContainerId} not found`);
      return;
    }

    this.onBootComplete = options.onBootComplete || (() => {});
    this.isRunning = false;
    this.stage = 0; // 0 to 5
    this.pulses = [];

    this.init();
  }

  init() {
    if (typeof THREE === 'undefined') {
      console.error('Three.js not loaded');
      return;
    }

    // 1. Scene & Environment
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x020502, 0.05);

    const w = this.container.clientWidth || 800;
    const h = this.container.clientHeight || 400;

    this.camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 100);
    this.camera.position.set(0, 3.5, 7.5);
    this.camera.lookAt(0, 0, 0);

    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(w, h);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.container.appendChild(this.renderer.domElement);
    } catch (e) {
      console.warn('WebGL initialization failed for hardware scene:', e);
      this.container.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#00ff66;font-family:var(--font-mono, monospace);text-align:center;">
          <div style="font-size:13px;color:#00ff66;letter-spacing:1px;font-weight:bold;">ESP32-WROOM-32 ◄───[ I²C BUS: SDA=GPIO21 / SCL=GPIO22 ]───► MPU6050</div>
          <div style="font-size:10px;color:#88aa88;margin-top:6px;letter-spacing:1px;">[HARDWARE SCHEMATIC ACTIVE // 2D CARRIER]</div>
        </div>
      `;
      return;
    }

    // 2. Technical Lab Grid
    const grid = new THREE.GridHelper(16, 24, 0x00ff66, 0x0a240e);
    grid.position.y = -1.2;
    this.scene.add(grid);

    // 3. Lighting (Rich cinematic illumination for dark CRT)
    const amb = new THREE.AmbientLight(0x003314, 2.2);
    this.scene.add(amb);

    const spot = new THREE.SpotLight(0x00ff66, 3.5, 20, Math.PI / 4, 0.4);
    spot.position.set(1, 7, 5);
    this.scene.add(spot);

    const cyanRim = new THREE.DirectionalLight(0x00ffff, 1.8);
    cyanRim.position.set(-5, 3, -2);
    this.scene.add(cyanRim);

    const amberRim = new THREE.PointLight(0xffaa00, 2.2, 12);
    amberRim.position.set(3, 3, 2);
    this.scene.add(amberRim);

    // 4. Hardware Models Group
    this.hwGroup = new THREE.Group();
    this.scene.add(this.hwGroup);

    this.buildEsp32Module();
    this.buildMpu6050Module();
    this.buildI2CInterconnect();

    window.addEventListener('resize', () => this.onResize());
    this.clock = new THREE.Clock();
    this.isRunning = true;
    this.animate();
  }

  buildEsp32Module() {
    this.esp32Group = new THREE.Group();
    this.esp32Group.position.set(-1.6, 0, 0);

    // Dark fiberglass PCB
    const pcbGeom = new THREE.BoxGeometry(2.2, 0.08, 4.2);
    const pcbMat = new THREE.MeshStandardMaterial({
      color: 0x071e0c,
      roughness: 0.5,
      metalness: 0.2,
    });
    const pcb = new THREE.Mesh(pcbGeom, pcbMat);
    this.esp32Group.add(pcb);

    // Metallic RF Shield Can (ESP-WROOM-32 module)
    const canGeom = new THREE.BoxGeometry(1.6, 0.22, 2.0);
    const canMat = new THREE.MeshStandardMaterial({
      color: 0x889988,
      metalness: 0.85,
      roughness: 0.25,
    });
    const can = new THREE.Mesh(canGeom, canMat);
    can.position.set(0, 0.12, -0.4);
    this.esp32Group.add(can);

    // Gold Antenna Meander Trace on PCB top
    const antGeom = new THREE.BoxGeometry(1.5, 0.02, 0.8);
    const antMat = new THREE.MeshStandardMaterial({
      color: 0xffaa00,
      metalness: 0.9,
      roughness: 0.1,
      emissive: 0x442200,
    });
    const ant = new THREE.Mesh(antGeom, antMat);
    ant.position.set(0, 0.05, -1.6);
    this.esp32Group.add(ant);

    // Dual-in-line header pins (38 gold pins)
    const pinGeom = new THREE.CylinderGeometry(0.03, 0.03, 0.45, 8);
    const pinMat = new THREE.MeshStandardMaterial({ color: 0xffcc33, metalness: 0.9, roughness: 0.2 });

    for (let i = 0; i < 19; i++) {
      const z = -1.8 + i * 0.2;
      // Left row
      const pinL = new THREE.Mesh(pinGeom, pinMat);
      pinL.position.set(-0.95, 0.15, z);
      this.esp32Group.add(pinL);
      // Right row
      const pinR = new THREE.Mesh(pinGeom, pinMat);
      pinR.position.set(0.95, 0.15, z);
      this.esp32Group.add(pinR);
    }

    // Status LED (GPIO2 Cyan + Power Red)
    const ledGeom = new THREE.BoxGeometry(0.1, 0.08, 0.1);
    const blueLedMat = new THREE.MeshBasicMaterial({ color: 0x00ccff });
    this.espLed = new THREE.Mesh(ledGeom, blueLedMat);
    this.espLed.position.set(0.5, 0.08, 1.2);
    this.esp32Group.add(this.espLed);

    // Micro USB connector
    const usbGeom = new THREE.BoxGeometry(0.7, 0.25, 0.6);
    const usbMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.9, roughness: 0.2 });
    const usb = new THREE.Mesh(usbGeom, usbMat);
    usb.position.set(0, 0.12, 2.05);
    this.esp32Group.add(usb);

    this.hwGroup.add(this.esp32Group);
  }

  buildMpu6050Module() {
    this.mpuGroup = new THREE.Group();
    this.mpuGroup.position.set(2.0, 0.2, 0.2);

    // Blue/Cyan sensor breakout PCB
    const pcbGeom = new THREE.BoxGeometry(1.5, 0.06, 1.8);
    const pcbMat = new THREE.MeshStandardMaterial({
      color: 0x003344,
      emissive: 0x001122,
      roughness: 0.4,
      metalness: 0.3,
    });
    const pcb = new THREE.Mesh(pcbGeom, pcbMat);
    this.mpuGroup.add(pcb);

    // QFN-24 Sensor IC Package (MPU6050)
    const icGeom = new THREE.BoxGeometry(0.65, 0.1, 0.65);
    const icMat = new THREE.MeshStandardMaterial({
      color: 0x111111,
      roughness: 0.6,
      metalness: 0.3,
    });
    const ic = new THREE.Mesh(icGeom, icMat);
    ic.position.set(0, 0.08, 0);
    this.mpuGroup.add(ic);

    // Pin 1 orientation dot
    const dotGeom = new THREE.CylinderGeometry(0.04, 0.04, 0.02, 8);
    const dotMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const dot = new THREE.Mesh(dotGeom, dotMat);
    dot.position.set(-0.2, 0.14, -0.2);
    this.mpuGroup.add(dot);

    // Header pins on sensor module
    const pinGeom = new THREE.CylinderGeometry(0.025, 0.025, 0.35, 8);
    const pinMat = new THREE.MeshStandardMaterial({ color: 0xffcc33, metalness: 0.9 });
    for (let p = 0; p < 8; p++) {
      const pin = new THREE.Mesh(pinGeom, pinMat);
      pin.position.set(-0.55 + p * 0.16, 0.1, 0.75);
      this.mpuGroup.add(pin);
    }

    this.hwGroup.add(this.mpuGroup);
  }

  buildI2CInterconnect() {
    // 3D Bezier Curves for SDA (cyan, GPIO21) and SCL (amber, GPIO22) lines
    // High-contrast color differentiation for distinct signal paths
    const startSDA = new THREE.Vector3(-0.65, 0.15, 0.2);
    const midSDA = new THREE.Vector3(0.5, 0.9, 0.6);
    const endSDA = new THREE.Vector3(1.7, 0.25, 0.75);
    this.sdaCurve = new THREE.QuadraticBezierCurve3(startSDA, midSDA, endSDA);

    const sdaPoints = this.sdaCurve.getPoints(30);
    const sdaGeom = new THREE.BufferGeometry().setFromPoints(sdaPoints);
    const sdaMat = new THREE.LineBasicMaterial({ color: 0x00ffff, linewidth: 2.5, transparent: true, opacity: 0.9 });
    this.sdaLine = new THREE.Line(sdaGeom, sdaMat);
    this.hwGroup.add(this.sdaLine);

    const startSCL = new THREE.Vector3(-0.65, 0.15, 0.4);
    const midSCL = new THREE.Vector3(0.5, 0.85, 0.2);
    const endSCL = new THREE.Vector3(1.54, 0.25, 0.75);
    this.sclCurve = new THREE.QuadraticBezierCurve3(startSCL, midSCL, endSCL);

    const sclPoints = this.sclCurve.getPoints(30);
    const sclGeom = new THREE.BufferGeometry().setFromPoints(sclPoints);
    const sclMat = new THREE.LineBasicMaterial({ color: 0xffaa00, linewidth: 2.5, transparent: true, opacity: 0.9 });
    this.sclLine = new THREE.Line(sclGeom, sclMat);
    this.hwGroup.add(this.sclLine);

    // Traveling Electrical Energy Pulses along SDA (Cyan) and SCL (Amber)
    const pulseGeom = new THREE.SphereGeometry(0.07, 12, 12);
    const sdaPulseMat = new THREE.MeshBasicMaterial({ color: 0x55ffff });
    const sclPulseMat = new THREE.MeshBasicMaterial({ color: 0xffcc33 });

    this.pulseSDA = new THREE.Mesh(pulseGeom, sdaPulseMat);
    this.pulseSCL = new THREE.Mesh(pulseGeom, sclPulseMat);
    this.hwGroup.add(this.pulseSDA);
    this.hwGroup.add(this.pulseSCL);
  }

  setAssemblyProgress(progress) {
    // 0.0 to 1.0
    if (this.esp32Group) {
      this.esp32Group.scale.setScalar(0.7 + progress * 0.3);
    }
    if (this.mpuGroup) {
      this.mpuGroup.scale.setScalar(0.7 + progress * 0.3);
    }
  }

  onResize() {
    if (!this.renderer || !this.camera || !this.container) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  animate() {
    if (!this.isRunning) return;
    requestAnimationFrame(() => this.animate());

    const t = this.clock.getElapsedTime();

    // Gentle hardware floating and slow inspection tilt
    this.hwGroup.rotation.y = Math.sin(t * 0.5) * 0.18;
    this.hwGroup.rotation.x = 0.22 + Math.cos(t * 0.4) * 0.06;
    this.hwGroup.position.y = Math.sin(t * 1.2) * 0.06;

    // Pulse travel along I2C bezier curves
    const sdaU = (t * 0.8) % 1.0;
    const sclU = (t * 0.8 + 0.35) % 1.0;

    if (this.sdaCurve && this.pulseSDA) {
      const pos = this.sdaCurve.getPoint(sdaU);
      this.pulseSDA.position.copy(pos);
    }
    if (this.sclCurve && this.pulseSCL) {
      const pos = this.sclCurve.getPoint(sclU);
      this.pulseSCL.position.copy(pos);
    }

    // Blink ESP32 status LED
    if (this.espLed) {
      this.espLed.visible = Math.sin(t * 8) > 0;
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
