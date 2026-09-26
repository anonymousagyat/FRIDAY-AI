// ==UserScript==
// @name         FRIDAY Autonomous Instagram Gatekeeper Bridge
// @namespace    http://tampermonkey.net/
// @version      3.5-native-dom
// @description  Connects Instagram Direct Web to local FRIDAY AI for autonomous gatekeeper chatting (100% Native DOM, Zero PyAutoGUI)
// @author       FRIDAY AI
// @match        https://*.instagram.com/direct/*
// @match        https://instagram.com/direct/*
// @match        https://www.instagram.com/direct/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==

(function() {
    'use strict';

    console.log("[FRIDAY Instagram Bridge v3.5] Initialized on:", window.location.href);

    let lastProcessedText = "";
    let lastProcessedElement = null;
    let isProcessing = false;
    let debounceTimer = null;
    let watchdogTimer = null;

    const recentSentReplies = [];
    const stampedFridayElements = new WeakSet();
    const sentByFridayCache = new Set([
        "i am friday. boss abhi busy hain, unhone mujhe baat karne ko kaha hai. kya kaam hai?",
        "boss thode busy hain, unki jagah main baat kar rahi hoon.",
        "boss busy hain, unhone pucha hai kya baat hai?",
        "namaste auntyji, main friday hoon. boss abhi focused work mein hain, unhone mujhe chat check karne ko kaha hai. koi zaroori kaam hai?"
    ]);

    // =========================================================================
    // METHOD 3: 100% BULLETPROOF DOM STAMPING ENGINE (dataset.fridaySent)
    // =========================================================================

    function isFridayElement(el) {
        if (!el) return false;
        try {
            if (stampedFridayElements.has(el)) return true;
            if (el.dataset && el.dataset.fridaySent === "true") return true;
            if (el.getAttribute && el.getAttribute('data-friday-sent') === "true") return true;
            if (typeof el.closest === "function") {
                const stampedParent = el.closest('[data-friday-sent="true"]');
                if (stampedParent) return true;
            }
        } catch (e) {}
        return false;
    }

    function stampFridayBubble(replyText) {
        if (!replyText) return false;
        const targetNorm = normalizeText(replyText);

        const candidates = Array.from(document.querySelectorAll(
            'div[role="row"] span[dir="auto"], div[role="row"] div[dir="auto"], span[dir="auto"], div.x1n2onr6 span'
        ));

        for (let i = candidates.length - 1; i >= 0; i--) {
            const el = candidates[i];
            if (el.children.length > 0) continue;

            const txt = normalizeText(el.innerText || "");
            if (!txt) continue;

            if (txt === targetNorm) {
                el.dataset.fridaySent = "true";
                el.setAttribute('data-friday-sent', 'true');
                stampedFridayElements.add(el);

                let p = el.parentElement;
                for (let d = 0; d < 5 && p && p !== document.body; d++) {
                    p.dataset.fridaySent = "true";
                    p.setAttribute('data-friday-sent', 'true');
                    stampedFridayElements.add(p);
                    p = p.parentElement;
                }
                console.log("[FRIDAY Instagram Bridge] Method 3 DOM Stamp applied to:", replyText);
                return true;
            }
        }
        return false;
    }

    // =========================================================================
    // OUTGOING MESSAGE DETECTION (Instagram Direct)
    // =========================================================================

    function isOutgoingInstagramRow(rowElement) {
        if (!rowElement) return false;
        try {
            // 1. Method 3 DOM Stamp check
            if (isFridayElement(rowElement)) return true;

            // 2. HTML content inspection
            const html = rowElement.outerHTML || "";
            if (html.includes('justify-content: flex-end') || 
                html.includes('justify-content:flex-end') ||
                html.includes('data-testid="outgoing-message"')) {
                return true;
            }

            // 3. Computed style inspection up parent chain
            let p = rowElement;
            for (let d = 0; d < 4 && p && p !== document.body; d++) {
                const st = window.getComputedStyle ? window.getComputedStyle(p) : null;
                if (st && (st.justifyContent === 'flex-end' || st.alignSelf === 'flex-end' || st.textAlign === 'right')) {
                    return true;
                }
                p = p.parentElement;
            }

            // 4. Bounding rect check (Instagram Direct outgoing bubbles are on the right side)
            const rect = rowElement.getBoundingClientRect();
            const winWidth = window.innerWidth || 1200;
            if (rect.width > 0 && rect.left > (winWidth * 0.48)) {
                return true;
            }
        } catch (e) {}
        return false;
    }

    function isFridayMessage(normText, rowElement) {
        if (!normText) return true;

        // 1. PRIMARY: Method 3 DOM Stamp
        if (rowElement && isFridayElement(rowElement)) {
            return true;
        }

        // 2. Exact match in Friday's sent cache
        if (sentByFridayCache.has(normText)) return true;

        // 3. Strict Exact match with recent sent replies (ZERO SUBSTRING MATCHING!)
        for (let i = 0; i < recentSentReplies.length; i++) {
            const rNorm = normalizeText(recentSentReplies[i]);
            if (rNorm && rNorm === normText) {
                return true;
            }
        }

        // 4. True FRIDAY identity intros (exact prefix only)
        if (normText.startsWith("i am friday") ||
            normText.startsWith("i'm friday") ||
            normText.startsWith("main friday") ||
            normText.startsWith("boss busy hai, main friday") ||
            normText.startsWith("boss busy hain") ||
            normText.startsWith("boss thode busy hain") ||
            normText.startsWith("namaste auntyji, main friday")) {
            return true;
        }

        // 5. Outgoing Instagram row detection (flex-end / right-side)
        if (rowElement && isOutgoingInstagramRow(rowElement)) {
            return true;
        }

        return false;
    }

    // =========================================================================
    // ON-SCREEN HUD BADGE
    // =========================================================================
    let badge = null;

    function createBadge() {
        if (badge || !document.body) return;
        badge = document.createElement('div');
        badge.id = 'friday-bridge-hud';
        badge.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;' +
                              'background:#0f172a;color:#10b981;font-family:system-ui,-apple-system,sans-serif;' +
                              'font-size:12px;font-weight:600;padding:8px 14px;border-radius:20px;' +
                              'border:1.5px solid #10b981;box-shadow:0 8px 24px rgba(0,0,0,0.5);' +
                              'pointer-events:none;transition:all 0.3s ease;display:flex;align-items:center;gap:6px;';
        badge.innerHTML = '<span style="font-size:10px;">🟢</span> <span>FRIDAY Instagram: Active</span>';
        document.body.appendChild(badge);
    }

    function updateBadge(statusText, color = "#10b981", icon = "🟢") {
        createBadge();
        if (badge) {
            badge.style.borderColor = color;
            badge.style.color = color;
            badge.innerHTML = `<span style="font-size:10px;">${icon}</span> <span>FRIDAY: ${statusText}</span>`;
        }
    }

    setTimeout(createBadge, 1000);

    function normalizeText(text) {
        return (text || "").trim().toLowerCase().replace(/\s+/g, ' ');
    }

    // =========================================================================
    // CHAT DOM INSPECTION (Leaf message extraction with bottom-up scan)
    // =========================================================================

    function checkAndProcess() {
        if (isProcessing) return;

        const rows = Array.from(document.querySelectorAll('div[role="row"], div.x1n2onr6'));
        if (!rows || rows.length === 0) return;

        let targetRow = null;
        let incomingText = "";
        let norm = "";

        for (let i = rows.length - 1; i >= Math.max(0, rows.length - 15); i--) {
            const r = rows[i];
            if (!r) continue;

            if (r.closest('div[role="textbox"]') || r.isContentEditable) continue;
            if (r.closest('header, nav, [role="navigation"]')) continue;

            const span = r.querySelector('span[dir="auto"]') || r.querySelector('div[dir="auto"]');
            if (!span) continue;

            const txt = (span.innerText || "").trim();
            if (!txt || txt.length < 1) continue;

            if (/^(seen|active now|delivered|sent|typing|\d+:\d+.*)$/i.test(txt)) continue;

            const n = normalizeText(txt);

            // If the latest message is an outgoing message or stamped Friday message, we already replied!
            if (isFridayMessage(n, r)) {
                return;
            }

            targetRow = r;
            incomingText = txt;
            norm = n;
            break;
        }

        if (!targetRow || !incomingText) return;

        if (targetRow === lastProcessedElement || norm === lastProcessedText) {
            return;
        }

        isProcessing = true;
        lastProcessedText = norm;
        lastProcessedElement = targetRow;

        console.log("[FRIDAY Instagram Bridge] >>> New incoming message from contact:", incomingText);
        updateBadge(`Thinking: "${incomingText.slice(0, 16)}..."`, "#f59e0b", "🟡");

        if (watchdogTimer) clearTimeout(watchdogTimer);
        watchdogTimer = setTimeout(() => {
            if (isProcessing) {
                console.warn("[FRIDAY Instagram Bridge] Watchdog timeout - unlocking");
                isProcessing = false;
                updateBadge("Watching Chat", "#10b981", "🟢");
            }
        }, 10000);

        notifyFriday(incomingText);
    }

    // =========================================================================
    // SAFE MUTATION OBSERVER
    // =========================================================================

    const observer = new MutationObserver((mutations) => {
        if (isProcessing) return;

        let hasRealDOMMutation = false;
        for (let i = 0; i < mutations.length; i++) {
            const t = mutations[i].target;
            if (!t) continue;
            const el = (t.nodeType === 1) ? t : t.parentElement;
            if (!el || (!el.id?.includes('friday-bridge-hud') && !el.closest?.('#friday-bridge-hud'))) {
                hasRealDOMMutation = true;
                break;
            }
        }
        if (!hasRealDOMMutation) return;

        // METHOD 3: If Friday recently sent a reply, ensure newly rendered bubble is stamped instantly
        if (recentSentReplies.length > 0) {
            stampFridayBubble(recentSentReplies[recentSentReplies.length - 1]);
        }

        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(checkAndProcess, 2000);
    });

    function startObserving() {
        const target = document.querySelector('div[role="main"]') || document.body;
        observer.observe(target, { childList: true, subtree: true });
        console.log("[FRIDAY Instagram Bridge v3.5] Watching chat for incoming messages...");
        updateBadge("Watching Chat", "#10b981", "🟢");
        setTimeout(checkAndProcess, 1000);
    }

    setTimeout(startObserving, 1500);

    // =========================================================================
    // SERVER IPC CALL (Single clean call to 127.0.0.1:8765)
    // =========================================================================

    function notifyFriday(text) {
        console.log("[FRIDAY Instagram Bridge] Calling 127.0.0.1:8765/incoming with:", text);

        const payload = JSON.stringify({
            url: window.location.href,
            text: text,
            timestamp: Date.now()
        });

        if (typeof GM_xmlhttpRequest === "function") {
            GM_xmlhttpRequest({
                method: "POST",
                url: "http://127.0.0.1:8765/incoming",
                headers: { "Content-Type": "application/json" },
                data: payload,
                timeout: 10000,
                onload: function(response) {
                    handleServerResponse(response.responseText);
                },
                onerror: function(err) {
                    console.error("[FRIDAY Instagram Bridge] Bridge offline on 127.0.0.1:8765", err);
                    updateBadge("Bridge Offline", "#ef4444", "🔴");
                    if (watchdogTimer) clearTimeout(watchdogTimer);
                    setTimeout(() => { isProcessing = false; }, 3000);
                },
                ontimeout: function() {
                    console.warn("[FRIDAY Instagram Bridge] Bridge request timed out");
                    updateBadge("Timeout", "#ef4444", "🔴");
                    if (watchdogTimer) clearTimeout(watchdogTimer);
                    setTimeout(() => { isProcessing = false; }, 2000);
                }
            });
        } else {
            fetch("http://127.0.0.1:8765/incoming", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: payload
            })
            .then(res => res.text())
            .then(txt => handleServerResponse(txt))
            .catch(err => {
                console.error("[FRIDAY Instagram Bridge] Fetch error:", err);
                updateBadge("Bridge Offline", "#ef4444", "🔴");
                if (watchdogTimer) clearTimeout(watchdogTimer);
                setTimeout(() => { isProcessing = false; }, 3000);
            });
        }
    }

    function handleServerResponse(responseText) {
        if (watchdogTimer) clearTimeout(watchdogTimer);
        try {
            console.log("[FRIDAY Instagram Bridge] Server raw response:", responseText);
            const data = JSON.parse(responseText);
            if (data && data.should_reply && data.reply) {
                console.log("[FRIDAY Instagram Bridge] Received reply:", data.reply);
                updateBadge(`Replying: "${data.reply.slice(0, 16)}..."`, "#3b82f6", "🔵");
                typeAndSend(data.reply);
            } else {
                console.log("[FRIDAY Instagram Bridge] Server opted not to reply:", data);
                updateBadge("Watching Chat", "#10b981", "🟢");
                setTimeout(() => {
                    isProcessing = false;
                    lastProcessedElement = null;
                    lastProcessedText = "";
                }, 1000);
            }
        } catch (e) {
            console.error("[FRIDAY Instagram Bridge] JSON parse error:", e);
            updateBadge("Parse Error", "#ef4444", "🔴");
            isProcessing = false;
            lastProcessedElement = null;
            lastProcessedText = "";
        }
    }

    // =========================================================================
    // PENDING OUTBOUND QUEUE CHECK (Initial Intro / Direct Dispatch)
    // =========================================================================

    function checkPendingOutbound() {
        if (isProcessing) return;

        const url = "http://127.0.0.1:8765/pending_outbound";

        const handleOutbound = (responseText) => {
            try {
                const data = JSON.parse(responseText);
                if (data && data.has_pending && data.message) {
                    console.log("[FRIDAY Instagram Bridge] Found pending outbound message to send:", data.message);
                    updateBadge(`Sending: "${data.message.slice(0, 14)}..."`, "#3b82f6", "🔵");
                    typeAndSend(data.message);
                }
            } catch (e) {}
        };

        if (typeof GM_xmlhttpRequest === "function") {
            GM_xmlhttpRequest({
                method: "GET",
                url: url,
                timeout: 3000,
                onload: (res) => handleOutbound(res.responseText),
                onerror: () => {}
            });
        } else {
            fetch(url).then(r => r.text()).then(handleOutbound).catch(() => {});
        }
    }

    setTimeout(checkPendingOutbound, 2000);
    setTimeout(checkPendingOutbound, 4000);
    setInterval(checkPendingOutbound, 4000);

    // =========================================================================
    // 100% NATIVE DOM SEND ENGINE FOR INSTAGRAM DIRECT
    // =========================================================================

    function typeAndSend(replyText) {
        if (!replyText || !replyText.trim()) return;

        isProcessing = true;
        const normReply = normalizeText(replyText);
        sentByFridayCache.add(normReply);
        recentSentReplies.push(replyText);
        if (recentSentReplies.length > 20) recentSentReplies.shift();

        replyText.split(/[.!?।\n]+/).forEach(s => {
            const sn = normalizeText(s);
            if (sn.length > 20) sentByFridayCache.add(sn);
        });

        const input = document.querySelector('div[contenteditable="true"][role="textbox"]') || 
                      document.querySelector('div[role="textbox"]') ||
                      document.querySelector('div[contenteditable="true"]');

        if (!input) {
            console.error("[FRIDAY Instagram Bridge] Text input not found.");
            updateBadge("Input Not Found", "#ef4444", "🔴");
            isProcessing = false;
            return;
        }

        // 1. Focus input and insert text natively
        input.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, replyText);
        input.dispatchEvent(new Event('input', { bubbles: true }));

        // 2. Verified 300ms delay for React state sync, then click send button or press Enter
        setTimeout(() => {
            let sendBtn = null;
            const buttons = Array.from(document.querySelectorAll('div[role="button"], button'));
            for (let b of buttons) {
                const bTxt = (b.innerText || "").trim().toLowerCase();
                const bAria = (b.getAttribute('aria-label') || "").toLowerCase();
                if (bTxt === 'send' || bAria === 'send' || bTxt === 'भेजें' || bAria === 'भेजें') {
                    sendBtn = b;
                    break;
                }
            }

            if (sendBtn) {
                sendBtn.click();
            } else {
                const enterDown = new KeyboardEvent('keydown', {
                    key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true
                });
                input.dispatchEvent(enterDown);
            }

            console.log("[FRIDAY Instagram Bridge] Reply sent successfully via DOM:", replyText);
            updateBadge("Reply Sent!", "#10b981", "🟢");

            // 3. METHOD 3: THE 100% BULLETPROOF DOM STAMP (dataset.fridaySent)
            const stampDelays = [80, 200, 400, 800, 1500, 2500];
            stampDelays.forEach(delay => {
                setTimeout(() => {
                    stampFridayBubble(replyText);
                }, delay);
            });

            setTimeout(() => {
                isProcessing = false;
                lastProcessedElement = null;
                lastProcessedText = "";
                updateBadge("Watching Chat", "#10b981", "🟢");
            }, 2000);
        }, 300);
    }
})();
