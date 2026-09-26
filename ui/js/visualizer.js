/**
 * AudioWaveVisualizer — Real-Time Holographic Microphone Graph & Waveform Engine
 * Connects directly to Web Audio API AnalyserNode with hardware mic stream,
 * featuring multi-frequency neon oscilloscope traces, dynamic dB meter, and responsive audio spikes.
 */
class AudioWaveVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.state = 'idle'; // idle, ready, listening, processing, speaking
        this.audioLevel = 0.0;
        this.targetAudioLevel = 0.0;
        this.time = 0;

        // Web Audio API components
        this.audioCtx = null;
        this.analyser = null;
        this.micStream = null;
        this.dataArray = null;
        this.bufferLength = 0;
        this.micActive = false;

        // Visualizer color palettes per state
        this.palettes = {
            idle: {
                primary: '#00d4ff',
                secondary: '#7b2ff7',
                glow: 'rgba(0, 212, 255, 0.4)',
                accent: '#00f0ff',
                baseAmp: 6
            },
            ready: {
                primary: '#00f0ff',
                secondary: '#3b82f6',
                glow: 'rgba(0, 240, 255, 0.6)',
                accent: '#38bdf8',
                baseAmp: 8
            },
            listening: {
                primary: '#10b981',      // Vibrant emerald neon
                secondary: '#00f0ff',    // Cyan harmonic
                glow: 'rgba(16, 185, 129, 0.75)',
                accent: '#34d399',
                baseAmp: 18
            },
            processing: {
                primary: '#a855f7',      // Electric purple
                secondary: '#ec4899',    // Hot pink
                glow: 'rgba(168, 85, 247, 0.7)',
                accent: '#f43f5e',
                baseAmp: 12
            },
            speaking: {
                primary: '#38bdf8',      // Azure blue
                secondary: '#f59e0b',    // Stark gold
                glow: 'rgba(56, 189, 248, 0.7)',
                accent: '#fbbf24',
                baseAmp: 22
            }
        };

        this.currentPalette = { ...this.palettes.idle };

        this.resize();
        window.addEventListener('resize', () => this.resize());

        // Initialize mic on user interaction or immediately if permitted
        this.initMicStream();

        // Start render loop
        this.isRunning = true;
        this.render = this.render.bind(this);
        requestAnimationFrame(this.render);
    }

    resize() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = (rect.width || 640) * dpr;
        this.canvas.height = (rect.height || 90) * dpr;
        this.ctx.scale(dpr, dpr);
        this.width = rect.width || 640;
        this.height = rect.height || 90;
    }

    async initMicStream() {
        if (this.micActive || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: false,
                    autoGainControl: true
                }
            });

            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioCtx.createMediaStreamSource(stream);

            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 512;
            this.analyser.smoothingTimeConstant = 0.65;

            source.connect(this.analyser);
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
            this.micStream = stream;
            this.micActive = true;
            console.log("[Visualizer] Live microphone audio stream initialized successfully.");
        } catch (e) {
            console.log("[Visualizer] Microphone access notice (using hybrid synthetic analyzer):", e.message);
        }
    }

    setState(state) {
        this.state = state;
        const target = this.palettes[state] || this.palettes.idle;
        this.currentPalette = { ...target };

        if (this.audioCtx && this.audioCtx.state === 'suspended') {
            this.audioCtx.resume().catch(() => {});
        }
    }

    setAudioLevel(level) {
        this.targetAudioLevel = Math.max(0, Math.min(1.0, level));
    }

    getRealtimeAudioData() {
        if (this.micActive && this.analyser) {
            this.analyser.getByteTimeDomainData(this.dataArray);
            
            // Calculate RMS from time-domain slice
            let sum = 0;
            for (let i = 0; i < this.bufferLength; i++) {
                const norm = (this.dataArray[i] - 128) / 128;
                sum += norm * norm;
            }
            const rms = Math.sqrt(sum / this.bufferLength);
            const liveLevel = Math.min(1.0, rms * 4.5);
            this.audioLevel += (liveLevel - this.audioLevel) * 0.45;
            return this.dataArray;
        }

        // Fallback simulation when direct web mic isn't streaming
        this.audioLevel += (this.targetAudioLevel - this.audioLevel) * 0.25;
        return null;
    }

    render() {
        if (!this.isRunning) return;
        this.time += 0.035;

        const w = this.width;
        const h = this.height;
        const midY = h / 2;
        const ctx = this.ctx;

        ctx.clearRect(0, 0, w, h);

        const data = this.getRealtimeAudioData();
        const p = this.currentPalette;

        // Dynamic base amplitude determined by state and audio level
        let energy = this.audioLevel;
        if (this.state === 'listening' && energy < 0.1) {
            energy = 0.15 + Math.sin(this.time * 4) * 0.05;
        } else if (this.state === 'speaking') {
            energy = Math.max(energy, 0.28 + Math.sin(this.time * 6) * 0.12);
        } else if (this.state === 'processing') {
            energy = 0.12 + Math.abs(Math.sin(this.time * 5)) * 0.08;
        }

        const maxAmplitude = (h * 0.42) * Math.max(0.15, energy);

        // 1. Draw subtle background oscilloscope grid & tech markers
        this.drawBackgroundGrid(ctx, w, h, midY, p);

        // 2. Secondary Harmonic Wave (Violet / Glow)
        this.drawWaveform(ctx, w, midY, data, maxAmplitude * 0.65, this.time * 1.25 + 1.2, p.secondary, 1.5, 0.35, false);

        // 3. Main Audio Oscilloscope Wave (Vibrant Neon Stroke)
        this.drawWaveform(ctx, w, midY, data, maxAmplitude, this.time * 2.0, p.primary, 2.5, 0.95, true);

        // 4. Center Audio Reactive Pulses / Particle Spikes on Peaks
        if (energy > 0.3) {
            this.drawEnergyParticles(ctx, w, midY, energy, p.accent);
        }

        requestAnimationFrame(this.render);
    }

    drawBackgroundGrid(ctx, w, h, midY, palette) {
        ctx.save();
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.07)';
        ctx.lineWidth = 1;

        // Center baseline
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(w, midY);
        ctx.stroke();

        // Upper & lower threshold dotted lines
        ctx.setLineDash([4, 6]);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.beginPath();
        ctx.moveTo(0, midY - h * 0.3);
        ctx.lineTo(w, midY - h * 0.3);
        ctx.moveTo(0, midY + h * 0.3);
        ctx.lineTo(w, midY + h * 0.3);
        ctx.stroke();
        ctx.setLineDash([]);

        // Frequency division markers
        const divisions = [0.15, 0.3, 0.5, 0.7, 0.85];
        ctx.fillStyle = 'rgba(160, 180, 220, 0.25)';
        ctx.font = '9px "JetBrains Mono", Consolas, monospace';
        const labels = ['100Hz', '500Hz', '1kHz', '4kHz', '16kHz'];

        for (let i = 0; i < divisions.length; i++) {
            const x = w * divisions[i];
            ctx.beginPath();
            ctx.moveTo(x, midY - 4);
            ctx.lineTo(x, midY + 4);
            ctx.stroke();
            ctx.fillText(labels[i], x - 12, h - 6);
        }

        // Live status indicator
        ctx.fillStyle = (this.state === 'listening') ? '#10b981' : palette.primary;
        ctx.beginPath();
        ctx.arc(12, 14, 3.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = 'bold 9px "Segoe UI", system-ui, sans-serif';
        ctx.letterSpacing = '1px';
        const labelText = (this.state === 'listening') 
            ? 'AUDIO STREAM // RECORDING' 
            : (this.state === 'speaking') ? 'VOCAL SYNTHESIS // ACTIVE' : 'MIC MONITOR // READY';
        ctx.fillText(labelText, 22, 17);

        // Real-time Gain / dB readout
        const dbLevel = Math.round(-36 + this.audioLevel * 36);
        ctx.textAlign = 'right';
        ctx.fillText(`${dbLevel >= 0 ? '+' : ''}${dbLevel} dB`, w - 12, 17);
        ctx.textAlign = 'left';

        ctx.restore();
    }

    drawWaveform(ctx, w, midY, data, amplitude, phaseOffset, strokeColor, lineWidth, opacity, hasGlow) {
        ctx.save();
        ctx.globalAlpha = opacity;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (hasGlow) {
            ctx.shadowColor = strokeColor;
            ctx.shadowBlur = (this.state === 'listening' || this.audioLevel > 0.25) ? 14 : 6;
        }

        ctx.beginPath();

        const points = 72;
        const sliceWidth = w / (points - 1);

        for (let i = 0; i < points; i++) {
            const x = i * sliceWidth;
            const normX = i / (points - 1);

            // Envelope windowing (Hanning taper on edges so line rests cleanly at edges)
            const windowFactor = Math.sin(normX * Math.PI);

            let waveValue = 0;

            if (data && data.length > 0) {
                // Direct physical time-domain sampling
                const dataIndex = Math.floor(normX * (data.length - 1));
                const rawAudio = (data[dataIndex] - 128) / 128;
                waveValue = rawAudio * amplitude * windowFactor * 1.8;
            } else {
                // Harmonic synthesis based on voice frequency model
                const f1 = Math.sin(normX * 8 + phaseOffset);
                const f2 = Math.sin(normX * 18 - phaseOffset * 1.3) * 0.45;
                const f3 = Math.sin(normX * 32 + phaseOffset * 2.1) * 0.22;
                waveValue = (f1 + f2 + f3) * amplitude * windowFactor;
            }

            const y = midY + waveValue;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                // Smooth bezier curve through points
                const prevX = (i - 1) * sliceWidth;
                const midX = (prevX + x) / 2;
                ctx.quadraticCurveTo(prevX, y, midX, y);
            }
        }

        ctx.stroke();

        // Subtle gradient underfill for high-tech holographic HUD feel
        if (hasGlow && amplitude > 8) {
            ctx.lineTo(w, midY);
            ctx.lineTo(0, midY);
            ctx.closePath();

            const grad = ctx.createLinearGradient(0, midY - amplitude, 0, midY + amplitude);
            grad.addColorStop(0, 'rgba(0, 240, 255, 0.12)');
            grad.addColorStop(0.5, 'rgba(0, 212, 255, 0.03)');
            grad.addColorStop(1, 'rgba(168, 85, 247, 0.08)');
            ctx.fillStyle = grad;
            ctx.fill();
        }

        ctx.restore();
    }

    drawEnergyParticles(ctx, w, midY, energy, color) {
        ctx.save();
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;

        const count = Math.floor(energy * 10);
        for (let i = 0; i < count; i++) {
            const px = w * 0.25 + Math.random() * (w * 0.5);
            const py = midY + (Math.random() - 0.5) * energy * 45;
            const size = 1 + Math.random() * 2.5;

            ctx.beginPath();
            ctx.arc(px, py, size, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
    }
}
