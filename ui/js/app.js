/**
 * JARVIS Holographic OS — Main Interface Controller
 * Full English UI, Real-Time Audio Oscilloscope Waveform, and Assistant Identity Manager
 */

// Global Subsystem Instances
let orb = null;
let particles = null;
let visualizer = null;
let currentAssistantName = 'JARVIS';

const elements = {
    // Header & Identity
    navAssistantName: document.getElementById('nav-assistant-name'),
    assistantName: document.getElementById('assistant-name'),
    renameTriggerBtn: document.getElementById('rename-trigger-btn'),
    identityBadgeBtn: document.getElementById('identity-badge-btn'),
    systemClock: document.getElementById('system-clock'),
    engineTag: document.getElementById('engine-tag'),
    voiceTag: document.getElementById('voice-tag'),
    voicePill: document.getElementById('voice-pill'),

    // Core & Status
    statusBadge: document.getElementById('status-badge'),
    statusText: document.getElementById('status-text'),
    graphStateLabel: document.getElementById('graph-state-label'),
    liveTranscript: document.getElementById('live-transcript'),
    liveTranscriptText: document.getElementById('live-transcript-text'),

    // Chat Drawer
    chatPanel: document.getElementById('chat-panel'),
    chatMessages: document.getElementById('chat-messages'),
    toggleChatBtn: document.getElementById('toggle-chat-btn'),
    closeChatBtn: document.getElementById('close-chat-btn'),
    floatingChatToggle: document.getElementById('floating-chat-toggle'),
    clearChatBtn: document.getElementById('clear-chat-btn'),

    // Bottom Controls
    micBtn: document.getElementById('mic-btn'),
    textInputForm: document.getElementById('text-input-form'),
    textInput: document.getElementById('text-input'),

    // Rename Modal
    renameModal: document.getElementById('rename-modal'),
    closeRenameBtn: document.getElementById('close-rename-btn'),
    cancelRenameBtn: document.getElementById('cancel-rename-btn'),
    confirmRenameBtn: document.getElementById('confirm-rename-btn'),
    newAssistantNameInput: document.getElementById('new-assistant-name'),

    // Settings Modal
    settingsBtn: document.getElementById('settings-btn'),
    settingsModal: document.getElementById('settings-modal'),
    closeSettingsBtn: document.getElementById('close-settings-btn'),
    saveSettingsBtn: document.getElementById('save-settings-btn'),
    groupGeminiVoice: document.getElementById('group-gemini-voice'),
    settingGeminiVoice: document.getElementById('setting-gemini-voice'),
    settingGeminiKey: document.getElementById('setting-gemini-key'),
    settingTavilyKey: document.getElementById('setting-tavily-key'),
    settingDictation: document.getElementById('setting-dictation'),

    toastContainer: document.getElementById('toast-container')
};

// Lifecycle Initialization
window.addEventListener('pywebviewready', function () {
    initializeSubsystems();
    setupEventListeners();
    fetchBackendConfiguration();
    updateAssistantState('idle');
});

// Fallback initialization for direct browser previews
if (!window.pywebview) {
    window.addEventListener('load', () => {
        initializeSubsystems();
        setupEventListeners();
        updateAssistantState('ready');
    });
}

function initializeSubsystems() {
    try {
        orb = new OrbAnimation('orb-canvas');
        particles = new ParticleSystem('particles-canvas');
        visualizer = new AudioWaveVisualizer('audio-wave-canvas');
    } catch (e) {
        console.error("[Init Error]", e);
    }

    // Start digital system clock
    updateSystemClock();
    setInterval(updateSystemClock, 1000);
}

function updateSystemClock() {
    const now = new Date();
    const hrs = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    const secs = String(now.getSeconds()).padStart(2, '0');
    if (elements.systemClock) {
        elements.systemClock.innerText = `${hrs}:${mins}:${secs}`;
    }
}

function fetchBackendConfiguration() {
    if (!window.pywebview || !window.pywebview.api) return;

    window.pywebview.api.get_config().then(config => {
        if (!config) return;

        if (config.assistant_name) {
            setAssistantName(config.assistant_name);
        }

        // Gemini Live Voice
        const gv = config.gemini_voice || 'Aoede';
        if (elements.settingGeminiVoice) {
            elements.settingGeminiVoice.value = gv;
        }
        updateVoiceBadge(gv);

        // Keys & automation
        if (config.gemini_api_key && elements.settingGeminiKey) {
            elements.settingGeminiKey.value = config.gemini_api_key;
        }
        if (config.tavily_api_key && elements.settingTavilyKey) {
            elements.settingTavilyKey.value = config.tavily_api_key;
        }
        if (config.dictation_mode !== undefined && elements.settingDictation) {
            elements.settingDictation.checked = config.dictation_mode;
        }
    }).catch(err => console.error("[Config Load Error]", err));

    window.pywebview.api.get_chat_history().then(history => {
        if (history && Array.isArray(history)) {
            loadChatHistory(history);
        }
    }).catch(err => console.error("[History Load Error]", err));
}

function updateVoiceBadge(voiceStr) {
    if (!elements.voiceTag) return;
    const v = (voiceStr || 'Aoede').toUpperCase();
    elements.voiceTag.innerText = `GEMINI (${v})`;
}
window.updateVoiceBadge = updateVoiceBadge;

// Safe backwards-compatibility stubs
function updateBrainBadge() {}
window.updateBrainBadge = updateBrainBadge;
function updateVoiceBadgeWithEngine(eng, config) {
    updateVoiceBadge((config && config.gemini_voice) || (elements.settingGeminiVoice ? elements.settingGeminiVoice.value : 'Aoede'));
}
window.updateVoiceBadgeWithEngine = updateVoiceBadgeWithEngine;
function updateVoiceEngineFields() {}
window.updateVoiceEngineFields = updateVoiceEngineFields;
function fetchTtsQuota() {}
window.fetchTtsQuota = fetchTtsQuota;
function setWakeWordDisplay() {}
window.setWakeWordDisplay = setWakeWordDisplay;

// Event Listeners & Control Bindings
function setupEventListeners() {
    // 1. Chat Drawer Toggles
    const toggleChat = () => {
        elements.chatPanel.classList.toggle('collapsed');
        if (!elements.chatPanel.classList.contains('collapsed')) {
            const pip = document.querySelector('.unread-pip');
            if (pip) pip.classList.remove('visible');
        }
    };
    if (elements.toggleChatBtn) elements.toggleChatBtn.addEventListener('click', toggleChat);
    if (elements.closeChatBtn) elements.closeChatBtn.addEventListener('click', toggleChat);
    if (elements.floatingChatToggle) elements.floatingChatToggle.addEventListener('click', toggleChat);

    if (elements.clearChatBtn) {
        elements.clearChatBtn.addEventListener('click', () => {
            elements.chatMessages.innerHTML = '';
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.clear_chat_history();
                showNotification('Activity history cleared.', 'info');
            }
        });
    }

    // 2. Microphone Trigger
    if (elements.micBtn) {
        elements.micBtn.addEventListener('click', () => {
            if (visualizer) visualizer.initMicStream();

            if (window.pywebview && window.pywebview.api) {
                if (elements.micBtn.classList.contains('active')) {
                    window.pywebview.api.stop_listening();
                } else {
                    window.pywebview.api.start_listening();
                }
            } else {
                // Mock toggle for browser preview
                const isListening = elements.micBtn.classList.contains('active');
                updateAssistantState(isListening ? 'ready' : 'listening');
            }
        });
    }

    // 3. Text Command Submission
    if (elements.textInputForm) {
        elements.textInputForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const cmd = elements.textInput.value.trim();
            if (!cmd) return;

            addChatMessage('user', cmd);
            elements.textInput.value = '';

            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.send_text_message(cmd);
                updateAssistantState('processing');
            } else {
                updateAssistantState('processing');
                setTimeout(() => {
                    updateAssistantState('speaking');
                    addChatMessage('assistant', 'Command received. Simulating response.');
                    setTimeout(() => updateAssistantState('ready'), 2500);
                }, 1200);
            }
        });
    }

    // 4. Quick Action Chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const cmd = btn.getAttribute('data-cmd');
            if (!cmd) return;
            addChatMessage('user', cmd);
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.send_text_message(cmd);
                updateAssistantState('processing');
            }
        });
    });

    // 5. RENAME ASSISTANT MODAL
    const openRenameModal = () => {
        if (elements.newAssistantNameInput) {
            elements.newAssistantNameInput.value = currentAssistantName;
        }
        if (elements.renameModal) {
            elements.renameModal.classList.remove('hidden');
            if (elements.newAssistantNameInput) elements.newAssistantNameInput.focus();
        }
    };

    if (elements.renameTriggerBtn) elements.renameTriggerBtn.addEventListener('click', openRenameModal);
    if (elements.identityBadgeBtn) elements.identityBadgeBtn.addEventListener('click', openRenameModal);

    const closeRenameModal = () => {
        if (elements.renameModal) elements.renameModal.classList.add('hidden');
    };
    if (elements.closeRenameBtn) elements.closeRenameBtn.addEventListener('click', closeRenameModal);
    if (elements.cancelRenameBtn) elements.cancelRenameBtn.addEventListener('click', closeRenameModal);

    // Preset chips in rename modal
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const name = btn.getAttribute('data-name');
            if (name && elements.newAssistantNameInput) {
                elements.newAssistantNameInput.value = name;
            }
        });
    });

    // Confirm Rename
    if (elements.confirmRenameBtn) {
        elements.confirmRenameBtn.addEventListener('click', () => {
            const newName = elements.newAssistantNameInput ? elements.newAssistantNameInput.value.trim() : '';
            if (!newName) {
                showNotification('Please enter a valid name.', 'error');
                return;
            }

            setAssistantName(newName);

            if (window.pywebview && window.pywebview.api) {
                if (window.pywebview.api.set_assistant_name) {
                    window.pywebview.api.set_assistant_name(newName);
                } else {
                    window.pywebview.api.update_config('assistant_name', newName);
                }
            }

            closeRenameModal();
            showNotification(`Assistant identity updated to ${newName.toUpperCase()}.`, 'success');
        });
    }

    // 6. SETTINGS MODAL & VOICE CONTROLS
    if (elements.settingsBtn) {
        elements.settingsBtn.addEventListener('click', () => {
            if (elements.settingsModal) elements.settingsModal.classList.remove('hidden');
        });
    }

    if (elements.voicePill) {
        elements.voicePill.addEventListener('click', () => {
            if (elements.settingsModal) elements.settingsModal.classList.remove('hidden');
            if (elements.settingGeminiVoice) {
                elements.settingGeminiVoice.focus();
                elements.settingGeminiVoice.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    if (elements.settingGeminiVoice) {
        elements.settingGeminiVoice.addEventListener('change', (e) => {
            const newVoice = e.target.value;
            updateVoiceBadge(newVoice);
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.update_config('gemini_voice', newVoice);
            }
            showNotification(`Gemini Live Voice switched to ${newVoice}`, 'success');
        });
    }

    const closeSettingsModal = () => {
        if (elements.settingsModal) elements.settingsModal.classList.add('hidden');
    };
    if (elements.closeSettingsBtn) elements.closeSettingsBtn.addEventListener('click', closeSettingsModal);

    if (elements.saveSettingsBtn) {
        elements.saveSettingsBtn.addEventListener('click', () => {
            const geminiVoice = elements.settingGeminiVoice ? elements.settingGeminiVoice.value : 'Aoede';
            const geminiKey = elements.settingGeminiKey ? elements.settingGeminiKey.value.trim() : '';
            const tavilyKey = elements.settingTavilyKey ? elements.settingTavilyKey.value.trim() : '';
            const dictation = elements.settingDictation ? elements.settingDictation.checked : false;

            if (window.pywebview && window.pywebview.api) {
                if (geminiVoice) window.pywebview.api.update_config('gemini_voice', geminiVoice);
                if (geminiKey) window.pywebview.api.update_config('gemini_api_key', geminiKey);
                if (tavilyKey) window.pywebview.api.update_config('tavily_api_key', tavilyKey);
                window.pywebview.api.toggle_dictation(dictation);
            }

            updateVoiceBadge(geminiVoice);
            closeSettingsModal();
            showNotification('Settings saved successfully.', 'success');
        });
    }
}

// Global API Callbacks (Invoked from Python Engine)

function updateAssistantState(state) {
    if (orb) orb.setState(state);
    if (particles) particles.setState(state);
    if (visualizer) visualizer.setState(state);

    const isMicActive = (state === 'listening' || state === 'ready');
    if (elements.micBtn) {
        elements.micBtn.classList.toggle('active', isMicActive);
        elements.micBtn.classList.toggle('muted', !isMicActive);
        elements.micBtn.title = isMicActive ? 'Friday is listening (Mic ON)' : 'Mic OFF (Processing / Speaking)';
    }

    if (elements.statusBadge) {
        elements.statusBadge.className = 'status-badge state-' + state;
    }

    if (!elements.statusText) return;

    switch (state) {
        case 'idle':
            elements.statusText.innerText = 'STANDBY // MIC MUTED';
            if (elements.graphStateLabel) elements.graphStateLabel.innerText = 'MIC MUTED';
            clearLiveTranscript();
            break;

        case 'ready':
        case 'listening':
            elements.statusText.innerText = 'FRIDAY IS LISTENING (MIC ON)';
            if (elements.graphStateLabel) elements.graphStateLabel.innerText = 'MIC ON';
            if (visualizer && state === 'listening') visualizer.initMicStream();
            break;

        case 'processing':
            elements.statusText.innerText = 'FRIDAY IS THINKING (MIC OFF)';
            if (elements.graphStateLabel) elements.graphStateLabel.innerText = 'THINKING';
            clearLiveTranscript();
            break;

        case 'speaking':
            elements.statusText.innerText = 'FRIDAY IS SPEAKING (MIC OFF)';
            if (elements.graphStateLabel) elements.graphStateLabel.innerText = 'SPEAKING';
            clearLiveTranscript();
            break;

        case 'executing':
            elements.statusText.innerText = 'EXECUTING ACTION (MIC OFF)';
            if (elements.graphStateLabel) elements.graphStateLabel.innerText = 'EXECUTING';
            break;
    }
}

function setAudioLevel(level) {
    if (orb) orb.setAudioLevel(level);
    if (visualizer) visualizer.setAudioLevel(level);
}

function setAssistantName(name) {
    if (!name) return;
    currentAssistantName = name.trim();
    const upper = currentAssistantName.toUpperCase();

    if (elements.assistantName) elements.assistantName.innerText = upper;
    if (elements.navAssistantName) elements.navAssistantName.innerText = upper;
}

function setWakeWordStatus(enabled) {}

function addChatMessage(role, text, timestamp = null) {
    if (!elements.chatMessages || !text) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    // Message text with line formatting
    const contentSpan = document.createElement('div');
    contentSpan.className = 'msg-body';
    contentSpan.innerText = text;
    msgDiv.appendChild(contentSpan);

    // Timestamp
    const timeSpan = document.createElement('span');
    timeSpan.className = 'msg-time';
    if (!timestamp) {
        const now = new Date();
        timestamp = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
    timeSpan.innerText = timestamp;
    msgDiv.appendChild(timeSpan);

    elements.chatMessages.appendChild(msgDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

    // Signal unread activity if drawer is collapsed
    if (elements.chatPanel && elements.chatPanel.classList.contains('collapsed')) {
        const pip = document.querySelector('.unread-pip');
        if (pip) pip.classList.add('visible');
    }
}

function loadChatHistory(messages) {
    if (!elements.chatMessages) return;
    elements.chatMessages.innerHTML = '';
    messages.forEach(msg => {
        addChatMessage(msg.role, msg.text || msg.content || '', msg.timestamp);
    });
}

function setLiveTranscript(text) {
    if (!text || !text.trim()) {
        clearLiveTranscript();
        return;
    }
    if (elements.liveTranscriptText) {
        elements.liveTranscriptText.innerText = text;
    }
    if (elements.liveTranscript) {
        elements.liveTranscript.classList.remove('hidden');
    }
}

function clearLiveTranscript() {
    if (elements.liveTranscriptText) {
        elements.liveTranscriptText.innerText = '';
    }
    if (elements.liveTranscript) {
        elements.liveTranscript.classList.add('hidden');
    }
}

function showNotification(text, type = 'info') {
    if (!elements.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = text;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3200);
}

// Window Global Expose for PyWebView Bridge Execution
window.updateAssistantState = updateAssistantState;
window.setAudioLevel = setAudioLevel;
window.setAssistantName = setAssistantName;
window.setWakeWordStatus = setWakeWordStatus;
window.addChatMessage = addChatMessage;
window.loadChatHistory = loadChatHistory;
window.setLiveTranscript = setLiveTranscript;
window.clearLiveTranscript = clearLiveTranscript;
window.showNotification = showNotification;
