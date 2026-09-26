/**
 * 3D Cybernetic Audio-Reactive Core Sphere & Orbital Rings
 * Ported from IRIS-AI AICoreSphere architecture using Three.js WebGL.
 * Features 900 Fibonacci particles, dual tilted orbital rings, and audio-reactive wave displacement.
 */

class OrbAnimation {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.state = 'ready'; // idle, ready, listening, processing, speaking
        this.audioLevel = 0.0;
        this.smoothAudio = 0.0;
        this.volTarget = 0.0;
        this.volCurrent = 0.0;
        this.isRunning = true;
        this.isSpeaking = false;
        this.isListening = false;

        // Try initializing Three.js WebGL; fall back to 2D if unavailable
        if (typeof THREE !== 'undefined') {
            try {
                this.initThree();
                this.webglAvailable = true;
            } catch (err) {
                console.warn('[OrbAnimation] WebGL init failed, falling back to 2D canvas:', err);
                this.init2DFallback();
                this.webglAvailable = false;
            }
        } else {
            console.warn('[OrbAnimation] THREE is undefined, using 2D fallback');
            this.init2DFallback();
            this.webglAvailable = false;
        }

        window.addEventListener('resize', () => this.resize());
        this.loop = this.loop.bind(this);
        requestAnimationFrame(this.loop);
    }

    initThree() {
        const rect = this.canvas.parentElement ? this.canvas.parentElement.getBoundingClientRect() : { width: 320, height: 320 };
        const width = rect.width || 320;
        const height = rect.height || 320;

        // 1. Scene & Camera
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
        this.camera.position.set(0, 0, 4.8);

        // 2. Low-overhead WebGL Renderer (optimized for GPU memory)
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            alpha: true,
            antialias: false,
            powerPreference: 'default',
            precision: 'lowp'
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

        // 3. Color Palettes
        this.IDLE_COLOR = new THREE.Color('#39ff14');      // Neon Emerald
        this.CYAN_COLOR = new THREE.Color('#00e5ff');      // Electric Cyan
        this.PURPLE_COLOR = new THREE.Color('#a855f7');    // Neural Violet
        this.RING_COLOR = new THREE.Color('#39ff14');
        this.RING_GLOW = new THREE.Color('#ccffb3');

        this.currentColor = this.CYAN_COLOR.clone();
        this.targetColor = this.CYAN_COLOR.clone();

        // 4. Main Group (Core + Rings)
        this.mainGroup = new THREE.Group();
        this.scene.add(this.mainGroup);

        // 5. 900-Particle Fibonacci Shell
        this.COUNT = 900;
        const positions = new Float32Array(this.COUNT * 3);
        this.original = new Float32Array(this.COUNT * 3);
        this.seeds = new Float32Array(this.COUNT * 2);

        for (let i = 0; i < this.COUNT; i++) {
            const phi = Math.acos(1 - (2 * (i + 0.5)) / this.COUNT);
            const theta = Math.PI * (1 + Math.sqrt(5)) * i;
            const r = 1.32;

            const px = r * Math.sin(phi) * Math.cos(theta);
            const py = r * Math.sin(phi) * Math.sin(theta);
            const pz = r * Math.cos(phi);

            positions[i * 3] = px;
            positions[i * 3 + 1] = py;
            positions[i * 3 + 2] = pz;

            this.original[i * 3] = px;
            this.original[i * 3 + 1] = py;
            this.original[i * 3 + 2] = pz;

            this.seeds[i * 2] = Math.random() * Math.PI * 2;         // Phase
            this.seeds[i * 2 + 1] = 0.5 + Math.random() * 0.8;      // Weight
        }

        this.particlesGeo = new THREE.BufferGeometry();
        this.particlesGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        this.particlesMat = new THREE.PointsMaterial({
            size: 0.024,
            color: this.currentColor,
            transparent: true,
            opacity: 0.85,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particlesMesh = new THREE.Points(this.particlesGeo, this.particlesMat);
        this.mainGroup.add(this.particlesMesh);

        // 6. Dual Orbital Rings
        // Ring 1
        const ring1Geo = new THREE.TorusGeometry(1.55, 0.005, 2, 64);
        this.ring1Mat = new THREE.MeshBasicMaterial({
            color: this.RING_COLOR,
            transparent: true,
            opacity: 0.25,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        this.ring1 = new THREE.Mesh(ring1Geo, this.ring1Mat);
        this.ring1.rotation.x = Math.PI * 0.12;
        this.mainGroup.add(this.ring1);

        // Ring 2
        const ring2Geo = new THREE.TorusGeometry(1.78, 0.0035, 2, 64);
        this.ring2Mat = new THREE.MeshBasicMaterial({
            color: this.CYAN_COLOR,
            transparent: true,
            opacity: 0.20,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        this.ring2 = new THREE.Mesh(ring2Geo, this.ring2Mat);
        this.ring2.rotation.x = Math.PI * 0.44;
        this.mainGroup.add(this.ring2);

        this.clock = new THREE.Clock();
    }

    init2DFallback() {
        this.ctx = this.canvas.getContext('2d');
        this.time = 0;
        this.resize();
    }

    resize() {
        if (!this.canvas) return;
        const rect = this.canvas.parentElement ? this.canvas.parentElement.getBoundingClientRect() : { width: 320, height: 320 };
        const width = rect.width || 320;
        const height = rect.height || 320;

        if (this.webglAvailable && this.renderer) {
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        } else if (this.ctx) {
            this.canvas.width = width;
            this.canvas.height = height;
            this.baseRadius = Math.min(width, height) * 0.28;
        }
    }

    setState(state) {
        this.state = state;
        this.isSpeaking = (state === 'speaking');
        this.isListening = (state === 'listening');

        if (!this.webglAvailable) return;

        switch (state) {
            case 'idle':
            case 'ready':
                this.targetColor = this.CYAN_COLOR;
                break;
            case 'listening':
                this.targetColor = this.IDLE_COLOR; // Neon green when mic active
                break;
            case 'processing':
                this.targetColor = this.PURPLE_COLOR; // Violet neural thinking
                break;
            case 'speaking':
                this.targetColor = this.IDLE_COLOR; // Neon green when speaking
                break;
        }
    }

    setAudioLevel(level) {
        this.audioLevel = Math.max(0, Math.min(level, 1.0));
    }

    loop() {
        if (!this.isRunning) return;
        requestAnimationFrame(this.loop);

        if (this.webglAvailable && this.renderer) {
            this.renderThree();
        } else if (this.ctx) {
            this.render2DFallback();
        }
    }

    renderThree() {
        const delta = this.clock.getDelta();
        const t = performance.now() * 0.001;

        // Smooth audio volume target
        let targetVol = this.audioLevel;
        if (this.isSpeaking) {
            const syntheticPulse = Math.abs(Math.sin(t * 9) * 0.55 + Math.sin(t * 4.3) * 0.35);
            targetVol = Math.max(targetVol, syntheticPulse * 0.65);
        } else if (this.isListening) {
            targetVol = Math.max(targetVol, Math.abs(Math.sin(t * 3.5)) * 0.15);
        } else {
            targetVol = Math.max(targetVol, Math.abs(Math.sin(t * 1.5)) * 0.04);
        }

        const lerpSpeed = (this.isSpeaking || this.isListening) ? 0.15 : 0.08;
        this.volCurrent += (targetVol - this.volCurrent) * lerpSpeed;
        const vol = this.volCurrent;

        // Group scale & rotation
        let targetScale = 0.65;
        if (this.state === 'listening') targetScale = 0.78;
        else if (this.state === 'speaking') targetScale = 0.75 + vol * 0.12;
        else if (this.state === 'processing') targetScale = 0.58;

        this.mainGroup.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 3.5);
        this.mainGroup.rotation.y += delta * (0.05 + (this.state === 'processing' ? 0.25 : 0.0));

        // Color Lerp
        this.currentColor.lerp(this.targetColor, delta * 4);
        this.particlesMat.color.copy(this.currentColor);

        // Orbital Rings rotation & reactive pulse
        if (this.ring1) {
            this.ring1.rotation.y += delta * 0.20;
            this.ring1Mat.opacity = 0.15 + vol * 0.55;
            this.ring1Mat.color.copy(this.currentColor);
        }
        if (this.ring2) {
            this.ring2.rotation.y -= delta * 0.14;
            this.ring2Mat.opacity = 0.12 + vol * 0.45;
        }

        // Particle Sinusoidal Wave Displacement
        const posArr = this.particlesGeo.attributes.position.array;
        const count = this.COUNT;
        const orig = this.original;
        const seeds = this.seeds;

        for (let i = 0; i < count; i++) {
            const ix = i * 3;
            const phase = seeds[i * 2];
            const weight = seeds[i * 2 + 1];

            // Wave height equation from IRIS-AI
            const wave = Math.sin(t * 6.5 + phase) * (vol * 0.35 + 0.02) * weight;

            const ox = orig[ix];
            const oy = orig[ix + 1];
            const oz = orig[ix + 2];
            const invR = 0.757; // 1 / 1.32

            posArr[ix] = ox + ox * invR * wave;
            posArr[ix + 1] = oy + oy * invR * wave;
            posArr[ix + 2] = oz + oz * invR * wave;
        }
        this.particlesGeo.attributes.position.needsUpdate = true;

        this.renderer.render(this.scene, this.camera);
    }

    render2DFallback() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        ctx.clearRect(0, 0, w, h);

        this.time += 0.03;
        const cx = w / 2;
        const cy = h / 2;
        const r = this.baseRadius * (1 + this.audioLevel * 0.25);

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

window.OrbAnimation = OrbAnimation;
