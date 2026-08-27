// ============================================================
// J.A.R.V.I.S. HUD — Background Particle System & Radar Sweep
// ============================================================

(function () {
    const canvas = document.getElementById('hudCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let W, H;
    let PARTICLE_COUNT = 60;
    const CONNECTION_DIST = 140;
    let particleSpeedMult = 1.0;
    let connectionColor = 'rgba(0, 180, 255,';
    let pStatus = 'OFFLINE';

    const particles = [];

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    // Particle class
    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * W;
            this.y = Math.random() * H;
            this.baseVx = (Math.random() - 0.5) * 0.3;
            this.baseVy = (Math.random() - 0.5) * 0.3;
            this.radius = Math.random() * 1.5 + 0.5;
            this.alpha = Math.random() * 0.4 + 0.1;
        }
        update() {
            this.x += this.baseVx * particleSpeedMult;
            this.y += this.baseVy * particleSpeedMult;
            if (this.x < 0) this.x = W;
            if (this.x > W) this.x = 0;
            if (this.y < 0) this.y = H;
            if (this.y > H) this.y = 0;
        }
        draw(ctx) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha * 0.5})`;
            ctx.fill();
        }
    }

    // Initialize max particles
    for (let i = 0; i < 100; i++) {
        particles.push(new Particle());
    }

    function drawHexGrid() {
        const size = 50;
        const h = size * Math.sqrt(3);
        ctx.strokeStyle = 'rgba(0, 120, 200, 0.025)';
        ctx.lineWidth = 0.5;
        for (let row = -1; row < H / h + 1; row++) {
            for (let col = -1; col < W / (size * 1.5) + 1; col++) {
                const cx = col * size * 1.5;
                const cy = row * h + (col % 2 === 0 ? 0 : h / 2);
                drawHex(cx, cy, size * 0.55);
            }
        }
    }

    function drawHex(cx, cy, r) {
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            const x = cx + r * Math.cos(angle);
            const y = cy + r * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
    }

    function animate() {
        ctx.clearRect(0, 0, W, H);
        drawHexGrid();

        const activeParticles = particles.slice(0, PARTICLE_COUNT);
        for (const p of activeParticles) {
            p.update();
            p.draw(ctx);
        }

        for (let i = 0; i < activeParticles.length; i++) {
            for (let j = i + 1; j < activeParticles.length; j++) {
                const dx = activeParticles[i].x - activeParticles[j].x;
                const dy = activeParticles[i].y - activeParticles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < CONNECTION_DIST) {
                    const alpha = (1 - dist / CONNECTION_DIST) * (pStatus === 'PROCESSING' ? 0.25 : 0.12);
                    ctx.beginPath();
                    ctx.moveTo(activeParticles[i].x, activeParticles[i].y);
                    ctx.lineTo(activeParticles[j].x, activeParticles[j].y);
                    ctx.strokeStyle = `${connectionColor} ${alpha})`;
                    if (pStatus === 'SPEAKING') {
                        ctx.shadowBlur = 5;
                        ctx.shadowColor = 'rgba(0,212,255,0.5)';
                    } else {
                        ctx.shadowBlur = 0;
                    }
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                    ctx.shadowBlur = 0;
                }
            }
        }
        requestAnimationFrame(animate);
    }
    animate();

    // ============================================================
    // ARC REACTOR — Multi-Layered Concentric Ring Engine
    // ============================================================
    const rCanvas = document.getElementById('reactorCanvas');
    if (!rCanvas) return;
    const rCtx = rCanvas.getContext('2d');
    const RW = rCanvas.width = 300;
    const RH = rCanvas.height = 300;
    const rcx = RW / 2;
    const rcy = RH / 2;

    let rTime = 0;
    let accentColor = '#00d4ff';
    let accentRgb = '0, 212, 255';

    function updateReactorColor() {
        if (pStatus === 'STANDBY')    { accentColor = '#00d4ff'; accentRgb = '0, 212, 255'; }
        else if (pStatus === 'LISTENING')  { accentColor = '#00ff88'; accentRgb = '0, 255, 136'; }
        else if (pStatus === 'PROCESSING') { accentColor = '#ffaa00'; accentRgb = '255, 170, 0'; }
        else if (pStatus === 'SPEAKING')   { accentColor = '#00d4ff'; accentRgb = '0, 212, 255'; }
        else { accentColor = '#006080'; accentRgb = '0, 96, 128'; }
    }

    function drawRing(radius, lineWidth, alpha) {
        rCtx.beginPath();
        rCtx.arc(rcx, rcy, radius, 0, Math.PI * 2);
        rCtx.strokeStyle = `rgba(${accentRgb}, ${alpha})`;
        rCtx.lineWidth = lineWidth;
        rCtx.stroke();
    }

    function drawSegmentedArc(radius, lineWidth, segments, gapAngle, rotation, alpha) {
        const segAngle = (Math.PI * 2 - segments * gapAngle) / segments;
        for (let i = 0; i < segments; i++) {
            const start = rotation + i * (segAngle + gapAngle);
            rCtx.beginPath();
            rCtx.arc(rcx, rcy, radius, start, start + segAngle);
            rCtx.strokeStyle = `rgba(${accentRgb}, ${alpha})`;
            rCtx.lineWidth = lineWidth;
            rCtx.stroke();
        }
    }

    function drawTickMarks(radius, count, tickLength, lineWidth, rotation, alpha) {
        for (let i = 0; i < count; i++) {
            const angle = rotation + (i / count) * Math.PI * 2;
            const x1 = rcx + Math.cos(angle) * radius;
            const y1 = rcy + Math.sin(angle) * radius;
            const x2 = rcx + Math.cos(angle) * (radius + tickLength);
            const y2 = rcy + Math.sin(angle) * (radius + tickLength);
            rCtx.beginPath();
            rCtx.moveTo(x1, y1);
            rCtx.lineTo(x2, y2);
            rCtx.strokeStyle = `rgba(${accentRgb}, ${alpha})`;
            rCtx.lineWidth = lineWidth;
            rCtx.stroke();
        }
    }

    function drawGearTeeth(radius, count, toothWidth, toothHeight, rotation, alpha) {
        for (let i = 0; i < count; i++) {
            const angle = rotation + (i / count) * Math.PI * 2;
            const halfW = toothWidth / 2;
            const innerR = radius;
            const outerR = radius + toothHeight;
            // Draw each tooth as a small rect
            rCtx.save();
            rCtx.translate(rcx, rcy);
            rCtx.rotate(angle);
            rCtx.fillStyle = `rgba(${accentRgb}, ${alpha})`;
            rCtx.fillRect(innerR, -halfW, toothHeight, toothWidth);
            rCtx.restore();
        }
    }

    function animateReactor() {
        rCtx.clearRect(0, 0, RW, RH);
        const speed = pStatus === 'PROCESSING' ? 1.8 : pStatus === 'SPEAKING' ? 1.2 : pStatus === 'LISTENING' ? 0.8 : 0.4;
        rTime += 0.016 * speed;
        updateReactorColor();

        // === OUTERMOST RING — thick glowing border ===
        rCtx.shadowBlur = 15;
        rCtx.shadowColor = accentColor;
        drawRing(138, 2.5, 0.7);
        rCtx.shadowBlur = 0;

        // Outer tick marks (60 fine ticks)
        drawTickMarks(128, 60, 8, 1, 0, 0.3);
        // Outer major ticks (12 bold ticks)
        drawTickMarks(126, 12, 12, 2, 0, 0.6);

        // === RING 2 — segmented rotating arc (4 segments) ===
        drawSegmentedArc(120, 3, 4, 0.15, rTime * 0.5, 0.5);

        // === RING 3 — thin static ring ===
        drawRing(110, 1, 0.25);

        // === RING 4 — gear teeth ring (rotating opposite) ===
        drawGearTeeth(98, 36, 3, 8, -rTime * 0.7, 0.35);

        // === RING 5 — thick glowing band ===
        rCtx.shadowBlur = 8;
        rCtx.shadowColor = accentColor;
        drawRing(92, 4, 0.6);
        rCtx.shadowBlur = 0;

        // === RING 6 — fine tick marks (48 ticks, rotating) ===
        drawTickMarks(82, 48, 6, 1, rTime * 0.3, 0.4);

        // === RING 7 — segmented arc (8 segments, opposite rotation) ===
        drawSegmentedArc(78, 2, 8, 0.1, -rTime * 0.4, 0.45);

        // === RING 8 — thin glowing ring ===
        rCtx.shadowBlur = 6;
        rCtx.shadowColor = accentColor;
        drawRing(70, 1.5, 0.55);
        rCtx.shadowBlur = 0;

        // === RING 9 — dashed ring (lots of small segments) ===
        drawSegmentedArc(62, 2, 24, 0.08, rTime * 0.6, 0.35);

        // === RING 10 — gear teeth (inner, smaller) ===
        drawGearTeeth(52, 24, 2.5, 6, rTime * 0.8, 0.3);

        // === RING 11 — medium glowing ring ===
        rCtx.shadowBlur = 10;
        rCtx.shadowColor = accentColor;
        drawRing(48, 2.5, 0.65);
        rCtx.shadowBlur = 0;

        // === RING 12 — fine ticks (rotating) ===
        drawTickMarks(40, 36, 5, 1, -rTime * 0.5, 0.35);

        // === RING 13 — segmented arc (6 segments) ===
        drawSegmentedArc(36, 2, 6, 0.2, rTime * 0.9, 0.5);

        // === INNER RING — thin ===
        drawRing(28, 1, 0.3);

        // === INNER GEAR ===
        drawGearTeeth(22, 16, 2, 4, -rTime * 1.1, 0.4);

        // === INNER CORE RING — bright ===
        rCtx.shadowBlur = 12;
        rCtx.shadowColor = accentColor;
        drawRing(18, 2, 0.8);
        rCtx.shadowBlur = 0;

        // === INNERMOST RING ===
        drawRing(12, 1.5, 0.5);

        // === CORE — glowing center dot ===
        const corePulse = 0.6 + 0.4 * Math.sin(rTime * 3);
        rCtx.beginPath();
        rCtx.arc(rcx, rcy, 6, 0, Math.PI * 2);
        rCtx.fillStyle = `rgba(${accentRgb}, ${corePulse})`;
        rCtx.shadowBlur = 20;
        rCtx.shadowColor = accentColor;
        rCtx.fill();
        rCtx.shadowBlur = 0;

        // === CROSSHAIR at center ===
        rCtx.beginPath();
        rCtx.moveTo(rcx - 10, rcy); rCtx.lineTo(rcx - 4, rcy);
        rCtx.moveTo(rcx + 4, rcy);  rCtx.lineTo(rcx + 10, rcy);
        rCtx.moveTo(rcx, rcy - 10); rCtx.lineTo(rcx, rcy - 4);
        rCtx.moveTo(rcx, rcy + 4);  rCtx.lineTo(rcx, rcy + 10);
        rCtx.strokeStyle = `rgba(${accentRgb}, 0.7)`;
        rCtx.lineWidth = 1;
        rCtx.stroke();

        // === AMBIENT GLOW (outer halo) ===
        const haloGrad = rCtx.createRadialGradient(rcx, rcy, 100, rcx, rcy, 150);
        haloGrad.addColorStop(0, `rgba(${accentRgb}, 0.06)`);
        haloGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        rCtx.fillStyle = haloGrad;
        rCtx.fillRect(0, 0, RW, RH);

        requestAnimationFrame(animateReactor);
    }
    animateReactor();

    // ============================================================
    // API
    // ============================================================
    window.setParticleStatus = function(status) {
        pStatus = status;
        const root = document.documentElement;
        
        updateReactorColor();

        if (status === 'STANDBY') {
            PARTICLE_COUNT = 40;
            particleSpeedMult = 0.5;
            connectionColor = 'rgba(0, 180, 255,';
            root.style.setProperty('--flow-dur', '4s');
            root.style.setProperty('--flow-color', 'var(--cyan)');
            root.style.setProperty('--flow-opacity', '0.2');
        } else if (status === 'LISTENING') {
            PARTICLE_COUNT = 60;
            particleSpeedMult = 1.0;
            connectionColor = 'rgba(0, 255, 136,';
            root.style.setProperty('--flow-dur', '2s');
            root.style.setProperty('--flow-color', 'var(--green)');
            root.style.setProperty('--flow-opacity', '0.5');
        } else if (status === 'PROCESSING') {
            PARTICLE_COUNT = 100;
            particleSpeedMult = 3.0;
            connectionColor = 'rgba(255, 170, 0,';
            root.style.setProperty('--flow-dur', '0.5s');
            root.style.setProperty('--flow-color', 'var(--orange)');
            root.style.setProperty('--flow-opacity', '0.8');
        } else if (status === 'SPEAKING') {
            PARTICLE_COUNT = 70;
            particleSpeedMult = 1.5;
            connectionColor = 'rgba(0, 212, 255,';
            root.style.setProperty('--flow-dur', '1.5s');
            root.style.setProperty('--flow-color', 'var(--cyan)');
            root.style.setProperty('--flow-opacity', '0.6');
        } else {
            // OFFLINE
            PARTICLE_COUNT = 20;
            particleSpeedMult = 0.2;
            connectionColor = 'rgba(0, 100, 150,';
            root.style.setProperty('--flow-dur', '6s');
            root.style.setProperty('--flow-color', 'var(--cyan-dim)');
            root.style.setProperty('--flow-opacity', '0.1');
        }
    };
    
    window.setParticleStatus('OFFLINE'); // Initial
})();
