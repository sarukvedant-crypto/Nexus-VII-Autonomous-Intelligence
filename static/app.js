// ============================================================
// J.A.R.V.I.S. HUD — Frontend Client
// ============================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// DOM Elements
const statusDot = $('#statusDot');
const statusText = $('#statusText');
const arcReactor = $('#arcReactor');
const arcStatusLabel = $('#arcStatusLabel');
const transcriptScroll = $('#transcriptScroll');
const activateBtn = $('#activateBtn');
const interruptBtn = $('#interruptBtn');
const settingsBtn = $('#settingsBtn');
const settingsOverlay = $('#settingsOverlay');
const closeSettingsBtn = $('#closeSettingsBtn');
const saveSettingsBtn = $('#saveSettingsBtn');
const saveStatus = $('#saveStatus');
const modelDisplay = $('#modelDisplay');

// Skills DOM
const skillsBtn = $('#skillsBtn');
const skillsModal = $('#skillsModal');
const skillsCloseBtn = $('#skillsCloseBtn');
const skillsList = $('#skillsList');
const skillUrlInput = $('#skillUrlInput');
const skillNameInput = $('#skillNameInput');
const importSkillUrlBtn = $('#importSkillUrlBtn');
const skillFileInput = $('#skillFileInput');
const uploadSkillBtn = $('#uploadSkillBtn');

const confirmOverlay = $('#confirmOverlay');
const confirmMessage = $('#confirmMessage');
const confirmDetails = $('#confirmDetails');
const confirmApproveBtn = $('#confirmApproveBtn');
const confirmDenyBtn = $('#confirmDenyBtn');

const mediaFileInput = $('#mediaFileInput');
const chatAttachBtn = $('#chatAttachBtn');
const mediaPreview = $('#mediaPreview');
const mediaPreviewImg = $('#mediaPreviewImg');
const mediaPreviewRemove = $('#mediaPreviewRemove');

// Telemetry DOM
const cpuBar = $('#cpuBar');
const ramBar = $('#ramBar');
const powerBar = $('#powerBar');
const cpuDetail = $('#cpuDetail');
const ramDetail = $('#ramDetail');
const powerDetail = $('#powerDetail');
const cpuValue = $('#cpuValue');
const ramValue = $('#ramValue');
const powerValue = $('#powerValue');
const timeValue = $('#timeValue');
const weatherValue = $('#weatherValue');

// Settings Inputs
const inputBaseUrl = $('#inputBaseUrl');
const inputApiKey = $('#inputApiKey');
const inputModel = $('#inputModel');
const inputMemory = $('#inputMemory');

// ============================================================
// STATE
// ============================================================
let ws = null;
let isRunning = false;
let currentStatus = 'OFFLINE';
let pendingConfirmId = null;
let pendingMediaFile = null;
let pendingMediaPath = null;
let pendingMediaUrl = null;

// ============================================================
// WEBSOCKET
// ============================================================
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        addTranscriptEntry('system', 'Neural uplink established.');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === 'status') {
            updateStatus(msg.data);
        } else if (msg.type === 'transcript') {
            addTranscriptEntry(msg.data.role, msg.data.text);
        } else if (msg.type === 'log') {
            addTranscriptEntry('log', msg.data);
        } else if (msg.type === 'confirm') {
            pendingConfirmId = msg.id;
            confirmMessage.textContent = `Jarvis wants to execute: ${msg.tool}`;
            confirmDetails.textContent = JSON.stringify(msg.args, null, 2);
            confirmOverlay.classList.add('open');
        } else if (msg.type === 'model_change') {
            modelDisplay.textContent = msg.data;
        }
    };

    ws.onclose = () => {
        updateStatus('OFFLINE');
        addTranscriptEntry('system', 'Neural uplink disconnected. Reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

// ============================================================
// STATUS MANAGEMENT
// ============================================================
function updateStatus(status) {
    currentStatus = status;
    const s = status.toUpperCase();
    statusText.textContent = s;
    arcStatusLabel.textContent = s;

    // Reset classes
    statusDot.className = 'status-dot';
    arcReactor.className = 'arc-reactor';
    
    if (window.setParticleStatus) window.setParticleStatus(s);

    if (s === 'STANDBY') {
        statusDot.classList.add('active');
        arcReactor.classList.add('standby');
        interruptBtn.disabled = true;
    } else if (s === 'LISTENING') {
        statusDot.classList.add('listening');
        arcReactor.classList.add('listening');
        interruptBtn.disabled = true;
    } else if (s === 'PROCESSING') {
        statusDot.classList.add('processing');
        arcReactor.classList.add('processing');
        interruptBtn.disabled = true;
    } else if (s === 'SPEAKING') {
        statusDot.classList.add('speaking');
        arcReactor.classList.add('speaking');
        interruptBtn.disabled = false;
    } else {
        // OFFLINE
        interruptBtn.disabled = true;
    }

    // Update activate button
    if (s !== 'OFFLINE') {
        isRunning = true;
        activateBtn.classList.add('active');
        activateBtn.querySelector('.btn-label').textContent = 'DEACTIVATE';
        activateBtn.querySelector('.btn-icon').textContent = '⏻';
    }

    if (s === 'OFFLINE') {
        isRunning = false;
        activateBtn.classList.remove('active');
        activateBtn.querySelector('.btn-label').textContent = 'ACTIVATE';
        activateBtn.querySelector('.btn-icon').textContent = '⏻';
        interruptBtn.disabled = true;
    }
}

// ============================================================
// TRANSCRIPT
// ============================================================
function addTranscriptEntry(role, text) {
    const entry = document.createElement('div');
    entry.className = `transcript-entry ${role}`;

    let prefix = '[SYSTEM]';
    if (role === 'user') prefix = '[USER]';
    else if (role === 'jarvis') prefix = '[J.A.R.V.I.S.]';
    else if (role === 'log') prefix = '[LOG]';

    const prefixSpan = document.createElement('span');
    prefixSpan.className = 'entry-prefix';
    prefixSpan.textContent = prefix;
    entry.appendChild(prefixSpan);

    const textSpan = document.createElement('span');
    textSpan.className = 'entry-text';
    entry.appendChild(textSpan);

    // Check if this is a user message with a pending media preview
    if (role === 'user' && pendingMediaUrl) {
        const img = document.createElement('img');
        img.src = pendingMediaUrl;
        img.className = 'entry-image';
        entry.appendChild(img);
        pendingMediaUrl = null;
    }

    transcriptScroll.appendChild(entry);
    transcriptScroll.scrollTop = transcriptScroll.scrollHeight;

    // Content Rendering
    if (role === 'jarvis' && text.length > 0) {
        if (window.marked) {
            textSpan.innerHTML = marked.parse(text);
        } else {
            textSpan.textContent = text;
        }
    } else {
        textSpan.textContent = text;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// TELEMETRY POLLING
// ============================================================
function setBar(barEl, valueEl, detailEl, pct, detailText) {
    barEl.style.width = pct + '%';
    valueEl.textContent = Math.round(pct) + '%';
    if (detailEl && detailText) detailEl.textContent = detailText;

    // Color thresholds (skip for power bar)
    if (barEl !== powerBar) {
        const gauge = barEl.closest('.hbar-gauge');
        if (pct > 85) {
            barEl.style.background = 'linear-gradient(90deg, #991122, #ff3344)';
            barEl.style.boxShadow = '0 0 10px rgba(255,51,68,0.4)';
            if (gauge) gauge.classList.add('critical');
        } else if (pct > 60) {
            barEl.style.background = 'linear-gradient(90deg, #805500, #ffaa00)';
            barEl.style.boxShadow = '0 0 8px rgba(255,170,0,0.3)';
            if (gauge) gauge.classList.remove('critical');
        } else {
            barEl.style.background = '';
            barEl.style.boxShadow = '';
            if (gauge) gauge.classList.remove('critical');
        }
    }
}

async function pollTelemetry() {
    try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();

        setBar(cpuBar, cpuValue, cpuDetail, data.cpu || 0, '');
        setBar(ramBar, ramValue, ramDetail, data.ram_pct || 0,
               data.ram_used && data.ram_total
                   ? `${data.ram_used} / ${data.ram_total}`
                   : '');
        setBar(powerBar, powerValue, powerDetail, data.power_pct || 0,
               data.power || '');

        timeValue.textContent = data.time || '--';
        weatherValue.textContent = data.weather || '--';
    } catch (e) {
        // Server might be down
    }
}

// ============================================================
// SETTINGS
// ============================================================
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        inputBaseUrl.value = data.AI_BASE_URL || '';
        inputApiKey.value = data.AI_API_KEY || '';
        inputModel.value = data.AI_MODEL || '';
        const inputVoice = document.getElementById('inputVoice');
        if (inputVoice) inputVoice.value = data.AI_VOICE || 'en-GB-RyanNeural';
        inputMemory.value = data.memory || '';
        modelDisplay.textContent = data.AI_MODEL || '--';

        // Load new feature settings if available
        const b1Url = $('#inputBackup1Url');
        const b1Key = $('#inputBackup1Key');
        const b1Model = $('#inputBackup1Model');
        const b2Url = $('#inputBackup2Url');
        const b2Key = $('#inputBackup2Key');
        const b2Model = $('#inputBackup2Model');
        if (b1Url) b1Url.value = data.BACKUP_1_BASE_URL || '';
        if (b1Key) b1Key.value = data.BACKUP_1_API_KEY || '';
        if (b1Model) b1Model.value = data.BACKUP_1_MODEL || '';
        if (b2Url) b2Url.value = data.BACKUP_2_BASE_URL || '';
        if (b2Key) b2Key.value = data.BACKUP_2_API_KEY || '';
        if (b2Model) b2Model.value = data.BACKUP_2_MODEL || '';
    } catch (e) {}
}

async function saveSettings() {
    saveStatus.textContent = 'SAVING...';
    saveStatus.style.color = '#ffaa00';
    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                AI_BASE_URL: inputBaseUrl.value,
                AI_API_KEY: inputApiKey.value,
                AI_MODEL: inputModel.value,
                AI_VOICE: document.getElementById('inputVoice').value,
                memory: inputMemory.value,
                BACKUP_1_BASE_URL: $('#inputBackup1Url')?.value || '',
                BACKUP_1_API_KEY: $('#inputBackup1Key')?.value || '',
                BACKUP_1_MODEL: $('#inputBackup1Model')?.value || '',
                BACKUP_2_BASE_URL: $('#inputBackup2Url')?.value || '',
                BACKUP_2_API_KEY: $('#inputBackup2Key')?.value || '',
                BACKUP_2_MODEL: $('#inputBackup2Model')?.value || '',
                GMAIL_ADDRESS: $('#inputGmailAddress')?.value || '',
                GMAIL_APP_PASSWORD: $('#inputGmailPassword')?.value || '',
                TELEGRAM_BOT_TOKEN: $('#inputTelegramToken')?.value || '',
                TELEGRAM_ALLOWED_UID: $('#inputTelegramUid')?.value || '',
            })
        });
        const data = await res.json();
        if (data.ok) {
            saveStatus.textContent = 'CONFIGURATION SAVED';
            saveStatus.style.color = '#00ff88';
            modelDisplay.textContent = inputModel.value || '--';
        } else {
            saveStatus.textContent = 'SAVE FAILED';
            saveStatus.style.color = '#ff3344';
        }
    } catch (e) {
        saveStatus.textContent = 'CONNECTION ERROR';
        saveStatus.style.color = '#ff3344';
    }
    setTimeout(() => { saveStatus.textContent = ''; }, 3000);
}

// ============================================================
// EVENT LISTENERS
// ============================================================
activateBtn.addEventListener('click', async () => {
    if (isRunning) {
        await fetch('/api/stop', { method: 'POST' });
        updateStatus('OFFLINE');
    } else {
        await fetch('/api/start', { method: 'POST' });
        addTranscriptEntry('system', 'Voice engine activating...');
    }
});

interruptBtn.addEventListener('click', async () => {
    await fetch('/api/interrupt', { method: 'POST' });
    addTranscriptEntry('system', 'Speech interrupted by user.');
});

confirmApproveBtn.addEventListener('click', () => {
    if (pendingConfirmId && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'confirm_response', id: pendingConfirmId, approved: true }));
        addTranscriptEntry('log', '[✓] Action AUTHORIZED by user.');
    }
    confirmOverlay.classList.remove('open');
    pendingConfirmId = null;
});

confirmDenyBtn.addEventListener('click', () => {
    if (pendingConfirmId && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'confirm_response', id: pendingConfirmId, approved: false }));
        addTranscriptEntry('log', '[✗] Action DENIED by user.');
    }
    confirmOverlay.classList.remove('open');
    pendingConfirmId = null;
});

settingsBtn.addEventListener('click', () => {
    loadSettings();
    settingsOverlay.classList.add('open');
});

closeSettingsBtn.addEventListener('click', () => {
    settingsOverlay.classList.remove('open');
});

settingsOverlay.addEventListener('click', (e) => {
    if (e.target === settingsOverlay) settingsOverlay.classList.remove('open');
});

saveSettingsBtn.addEventListener('click', saveSettings);

const chatInput = $('#chatInput');
const chatSendBtn = $('#chatSendBtn');

async function sendChatMessage() {
    const text = chatInput.value.trim();
    if (!text && !pendingMediaFile) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    let mediaPath = null;

    if (pendingMediaFile) {
        // Upload the file first
        const formData = new FormData();
        formData.append('file', pendingMediaFile);
        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.ok) {
                mediaPath = data.path;
                pendingMediaUrl = data.url;  // For inline transcript rendering
            }
        } catch (e) {
            addTranscriptEntry('log', '[!] Failed to upload media file.');
        }
        // Clear the preview
        pendingMediaFile = null;
        pendingMediaPath = null;
        mediaPreview.style.display = 'none';
        mediaPreviewImg.src = '';
    }

    ws.send(JSON.stringify({ action: 'chat', text: text || '', media_path: mediaPath }));
    chatInput.value = '';
}

const autocompleteMenu = $('#autocompleteMenu');

chatInput.addEventListener('input', (e) => {
    const text = chatInput.value;
    const match = text.match(/\/\s*([a-zA-Z0-9_-]*)$/) || text.match(/\/skill\s*([a-zA-Z0-9_-]*)$/i);
    
    if (match) {
        const query = match[1] ? match[1].toLowerCase() : '';
        const filtered = availableSkills.filter(s => s.name.toLowerCase().includes(query));
        
        autocompleteMenu.innerHTML = '';
        if (filtered.length > 0) {
            filtered.forEach(skill => {
                const item = document.createElement('div');
                item.style.padding = '8px 12px';
                item.style.cursor = 'pointer';
                item.style.color = 'var(--text-primary)';
                item.style.borderBottom = '1px solid rgba(0, 212, 255, 0.1)';
                item.style.fontFamily = 'monospace';
                item.textContent = `/skill ${skill.name}`;
                item.onmouseenter = () => item.style.background = 'rgba(0, 212, 255, 0.2)';
                item.onmouseleave = () => item.style.background = 'transparent';
                item.onclick = () => {
                    const before = text.substring(0, text.lastIndexOf('/'));
                    chatInput.value = before + `/skill ${skill.name} `;
                    autocompleteMenu.style.display = 'none';
                    chatInput.focus();
                };
                autocompleteMenu.appendChild(item);
            });
            autocompleteMenu.style.display = 'flex';
        } else {
            autocompleteMenu.style.display = 'none';
        }
    } else {
        autocompleteMenu.style.display = 'none';
    }
});

chatSendBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendChatMessage();
    }
});

chatInput.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let index in items) {
        const item = items[index];
        if (item.kind === 'file' && item.type.startsWith('image/')) {
            const blob = item.getAsFile();
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(blob);
            mediaFileInput.files = dataTransfer.files;
            
            // Trigger the change event manually
            const event = new Event('change', { bubbles: true });
            mediaFileInput.dispatchEvent(event);
            
            // Optional: Give a visual cue that image was pasted
            e.preventDefault();
            break;
        }
    }
});

chatAttachBtn.addEventListener('click', () => {
    mediaFileInput.click();
});

mediaFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    pendingMediaFile = file;
    
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
            mediaPreviewImg.src = ev.target.result;
            mediaPreviewImg.style.display = 'block';
            $('#mediaPreviewText').style.display = 'none';
            mediaPreview.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    } else {
        // For PDF or TXT
        mediaPreviewImg.src = '';
        mediaPreviewImg.style.display = 'none';
        const textSpan = $('#mediaPreviewText');
        textSpan.textContent = file.name;
        textSpan.style.display = 'block';
        mediaPreview.style.display = 'flex';
    }
    mediaFileInput.value = '';  // Reset so the same file can be re-selected
});

mediaPreviewRemove.addEventListener('click', () => {
    pendingMediaFile = null;
    pendingMediaPath = null;
    mediaPreview.style.display = 'none';
    mediaPreviewImg.style.display = 'none';
    $('#mediaPreviewText').style.display = 'none';
    mediaPreviewImg.src = '';
});

// ============================================================
// SKILLS LOGIC
// ============================================================
let availableSkills = [];

async function loadSkills() {
    if (!skillsList) return;
    try {
        const res = await fetch('/api/list_skills');
        const data = await res.json();
        if (data.status === 'success') {
            availableSkills = data.skills;
            skillsList.innerHTML = '';
            if (data.skills.length === 0) {
                skillsList.innerHTML = '<div style="color: var(--text-dim); font-size: 12px; font-family: var(--font-display);">No skills installed.</div>';
            }
            data.skills.forEach(skill => {
                const div = document.createElement('div');
                div.style.display = 'flex';
                div.style.justifyContent = 'space-between';
                div.style.alignItems = 'center';
                div.style.padding = '8px';
                div.style.background = 'rgba(0, 212, 255, 0.05)';
                div.style.border = '1px solid rgba(0, 212, 255, 0.1)';
                div.style.borderRadius = '4px';
                
                const name = document.createElement('span');
                name.style.color = 'var(--cyan)';
                name.style.fontFamily = 'monospace';
                name.textContent = skill.name;
                
                const delBtn = document.createElement('button');
                delBtn.className = 'hud-btn';
                delBtn.style.padding = '2px 6px';
                delBtn.style.fontSize = '10px';
                delBtn.style.borderColor = 'var(--red)';
                delBtn.style.color = 'var(--red)';
                delBtn.textContent = 'DELETE';
                delBtn.onclick = async () => {
                    await fetch('/api/delete_skill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: skill.name })
                    });
                    loadSkills();
                };
                
                div.appendChild(name);
                div.appendChild(delBtn);
                skillsList.appendChild(div);
            });
        }
    } catch (e) { console.error(e); }
}

if (skillsBtn) {
    skillsBtn.addEventListener('click', () => {
        skillsModal.classList.add('open');
        loadSkills();
    });
}
if (skillsCloseBtn) {
    skillsCloseBtn.addEventListener('click', () => skillsModal.classList.remove('open'));
}

if (importSkillUrlBtn) {
    importSkillUrlBtn.addEventListener('click', async () => {
        const url = skillUrlInput.value;
        const name = skillNameInput.value || 'imported_skill';
        if (!url) return;
        
        importSkillUrlBtn.textContent = '...';
        try {
            const res = await fetch('/api/import_skill_url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, name })
            });
            await res.json();
            skillUrlInput.value = '';
            skillNameInput.value = '';
            loadSkills();
        } catch (e) { console.error(e); }
        importSkillUrlBtn.textContent = 'IMPORT';
    });
}

if (uploadSkillBtn) {
    uploadSkillBtn.addEventListener('click', async () => {
        const file = skillFileInput.files[0];
        if (!file) return;
        
        uploadSkillBtn.textContent = '...';
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/upload_skill', {
                method: 'POST',
                body: formData
            });
            await res.json();
            skillFileInput.value = '';
            loadSkills();
        } catch (e) { console.error(e); }
        uploadSkillBtn.textContent = 'UPLOAD';
    });
}

// ============================================================
// MEDIA ATTACHMENTS
// ============================================================
// ============================================================
// MEMORY VAULT
// ============================================================
const mvTextInput = $('#mvTextInput');
const mvFileInput = $('#mvFileInput');
const mvSubmitBtn = $('#mvSubmitBtn');
const mvStatus = $('#mvStatus');

if (mvSubmitBtn) {
    mvSubmitBtn.addEventListener('click', async () => {
        const text = mvTextInput.value.trim();
        const file = mvFileInput.files[0];
        
        if (!text && !file) {
            mvStatus.textContent = 'Please provide text or an image.';
            mvStatus.style.color = '#ff4444';
            return;
        }

        mvStatus.textContent = 'Processing memory...';
        mvStatus.style.color = 'var(--cyan)';
        
        const formData = new FormData();
        formData.append('text', text);
        if (file) formData.append('file', file);

        try {
            const res = await fetch('/api/memory/add', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                mvStatus.textContent = data.message || 'Memory stored successfully.';
                mvStatus.style.color = '#00ffcc';
                mvTextInput.value = '';
                mvFileInput.value = '';
            } else {
                mvStatus.textContent = data.error || 'Failed to store memory.';
                mvStatus.style.color = '#ff4444';
            }
        } catch (e) {
            mvStatus.textContent = 'Network error.';
            mvStatus.style.color = '#ff4444';
        }
        
        setTimeout(() => {
            if (mvStatus.textContent.includes('successfully')) {
                mvStatus.textContent = '';
            }
        }, 5000);
    });
}

// ============================================================
// INIT
// ============================================================
connectWebSocket();
pollTelemetry();
setInterval(pollTelemetry, 5000); // Poll every 5 seconds
loadSettings();
