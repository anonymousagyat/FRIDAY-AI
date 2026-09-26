class ParticleSystem {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.numParticles = 100;
        this.state = 'idle';
        
        this.resize();
        window.addEventListener('resize', () => this.resize());
        
        this.initParticles();
        
        this.isRunning = true;
        this.loop = this.loop.bind(this);
        requestAnimationFrame(this.loop);
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    initParticles() {
        this.particles = [];
        const colors = [
            'rgba(0, 212, 255, 0.4)',
            'rgba(123, 47, 247, 0.4)',
            'rgba(255, 255, 255, 0.2)'
        ];
        
        for(let i=0; i<this.numParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: Math.random() * 2 + 0.5,
                color: colors[Math.floor(Math.random() * colors.length)],
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                baseVx: (Math.random() - 0.5) * 0.5,
                baseVy: (Math.random() - 0.5) * 0.5,
                angle: Math.random() * Math.PI * 2
            });
        }
    }
    
    setState(state) {
        this.state = state;
    }
    
    loop() {
        if (!this.isRunning) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        
        this.ctx.globalCompositeOperation = 'lighter';
        
        for(let i=0; i<this.particles.length; i++) {
            const p = this.particles[i];
            
            // State-based movement
            const dx = cx - p.x;
            const dy = cy - p.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            
            if (this.state === 'idle') {
                p.vx = p.baseVx + (dx * 0.0001);
                p.vy = p.baseVy + (dy * 0.0001);
            } 
            else if (this.state === 'listening') {
                // Vortex
                const force = 0.001;
                p.vx = p.baseVx * 2 + (dy * force) + (dx * force);
                p.vy = p.baseVy * 2 - (dx * force) + (dy * force);
            }
            else if (this.state === 'processing') {
                // Spiral in
                const force = 0.005;
                p.vx = (dy * force) + (dx * force * 0.5);
                p.vy = -(dx * force) + (dy * force * 0.5);
            }
            else if (this.state === 'speaking') {
                // Gentle outward
                const force = -0.0005;
                p.vx = p.baseVx + (dx * force);
                p.vy = p.baseVy + (dy * force);
            }
            
            // Limit speed
            const maxSpeed = this.state === 'processing' ? 3 : (this.state === 'listening' ? 2 : 0.5);
            const speed = Math.sqrt(p.vx*p.vx + p.vy*p.vy);
            if(speed > maxSpeed) {
                p.vx = (p.vx / speed) * maxSpeed;
                p.vy = (p.vy / speed) * maxSpeed;
            }
            
            p.x += p.vx;
            p.y += p.vy;
            
            // Screen wrap
            if(p.x < 0) p.x = this.canvas.width;
            if(p.x > this.canvas.width) p.x = 0;
            if(p.y < 0) p.y = this.canvas.height;
            if(p.y > this.canvas.height) p.y = 0;
            
            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.fill();
            
            // Draw connections
            for(let j=i+1; j<this.particles.length; j++) {
                const p2 = this.particles[j];
                const ddx = p.x - p2.x;
                const ddy = p.y - p2.y;
                const ddist = ddx*ddx + ddy*ddy;
                
                if (ddist < 10000) { // 100px squared
                    this.ctx.beginPath();
                    this.ctx.strokeStyle = `rgba(0, 212, 255, ${0.1 * (1 - ddist/10000)})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.stroke();
                }
            }
        }
        
        requestAnimationFrame(this.loop);
    }
    
    destroy() {
        this.isRunning = false;
    }
}
