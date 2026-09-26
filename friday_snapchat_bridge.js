// ==UserScript==
// @name         FRIDAY Autonomous Snapchat Gatekeeper Bridge
// @namespace    http://tampermonkey.net/
// @version      2.0-native-dom
// @description  Connects Snapchat Web to local FRIDAY AI for autonomous gatekeeper chatting (100% Native DOM, Zero PyAutoGUI)
// @author       FRIDAY AI
// @match        https://*.snapchat.com/web/*
// @match        https://web.snapchat.com/*
// @match        https://www.snapchat.com/web/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==

(function() {
    'use strict';

    console.log("[FRIDAY Snapchat Bridge v2.0] Initialized on:", window.location.href);

    let lastProcessedText = "";
    let lastProcessedElement = null;
    let isProcessing = false;
    let debounceTimer = null;
    let watchdogTimer = null;

    const recentSentReplies = [];
    const stampedFridayElements = new WeakSet();
    const sentByFridayCache = new Set([
        "boss busy hai, main friday. unhone mujhe baat karne ko kaha hai, batao kya kaam hai.",
        "boss abhi busy hain, unhone mujhe baat karne ko kaha hai. kya kaam hai?",
        "i am friday. boss abhi busy hain, unhone mujhe baat karne ko kaha hai. kya kaam hai?"
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

        const candidates = Array.from(document.querySelectorAll('span.ogn1z.nonIntl, span.ogn1z, div.p8r1z span.nonIntl, span.nonIntl, p.nonIntl, div[role="row"] span'));

        for (let i = candidates.length - 1; i >= 0; i--) {
            const el = candidates[i];
            if (el.children.length > 0) continue;

            const txt = normalizeText(el.innerText || "");
            if (!txt) continue;

            if (txt === targetNorm) {
                // Apply Method 3 bulletproof DOM stamp to the message leaf element
                el.dataset.fridaySent = "true";
                el.setAttribute('data-friday-sent', 'true');
                stampedFridayElements.add(el);

                // Also stamp parent containers up to 4 levels so any wrapper or child lookup succeeds
                let p = el.parentElement;
                for (let d = 0; d < 4 && p && p !== document.body; d++) {
                    p.dataset.fridaySent = "true";
                    p.setAttribute('data-friday-sent', 'true');
                    stampedFridayElements.add(p);
                    p = p.parentElement;
                }
                console.log("[FRIDAY Snapchat Bridge] Method 3 DOM Stamp applied to:", replyText);
                return true;
            }
        }
        return false;
    }

    function isOutgoingStack(el) {
        if (!el) return false;
        try {
            let row = el.closest('[role="row"], li, div[class*="message"], div[class*="chat"]');
            if (!row) row = el.parentElement;

            let curr = row;
            for (let step = 0; step < 8 && curr; step++) {
                const header = curr.querySelector?.('[class*="fCmUn"], [class*="EQJi_"], [class*="author"], [data-testid*="author"]');
                if (header) {
                    const hText = normalizeText(header.innerText || "");
                    if (hText === "me" || hText === "you") {
                        return true;
                    }
                    if (hText.length > 0) {
                        return false;
                    }
                }
                curr = curr.previousElementSibling;
            }
        } catch (e) {}
        return false;
    }

    // =========================================================================
    // ON-SCREEN HUD BADGE (Zero freeze, pointer-events none)
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
        badge.innerHTML = '<span style="font-size:10px;">🟢</span> <span>FRIDAY Snapchat: Active</span>';
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
    // OUTGOING MESSAGE DETECTION (Snapchat Web)
    // =========================================================================

    function isFridayMessage(normText, rowElement) {
        if (!normText) return true;

        // 1. PRIMARY CHECK: Method 3 Bulletproof DOM Stamp (dataset.fridaySent)
        if (rowElement && isFridayElement(rowElement)) {
            return true;
        }

        // 2. Strict Exact match in Friday's sent cache
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
            normText.startsWith("boss busy hain, main friday")) {
            return true;
        }

        // 5. Stack Author Header / Outgoing DOM inspection
        if (rowElement) {
            if (isOutgoingStack(rowElement)) {
                return true;
            }
            const html = rowElement.outerHTML || "";
            if (html.includes('flex-end') || 
                rowElement.querySelector('[data-testid="outgoing-message"]') !== null) {
                return true;
            }
        }

        return false;
    }

    // =========================================================================
    // SNAPCHAT DOM INSPECTION (Leaf message extraction with bottom-up scan)
    // =========================================================================

    function checkAndProcess() {
        if (isProcessing) return;

        // Query leaf message elements, prioritizing verified message class 'span.ogn1z'
        let rawElements = Array.from(document.querySelectorAll('span.ogn1z.nonIntl, span.ogn1z'));
        if (rawElements.length === 0) {
            rawElements = Array.from(document.querySelectorAll('div.p8r1z span.nonIntl, span.nonIntl, p.nonIntl'));
        }

        const candidates = rawElements.filter(el => {
            if (el.children.length > 0) return false;

            // Skip composer, file dropzones, upload areas, headers, navigation, and forms
            if (el.closest('div[contenteditable="true"]') || el.isContentEditable) return false;
            if (el.closest('[class*="fCmUn"], [class*="NTYUz"], [class*="EQJi_"], [class*="dropzone"], [class*="upload"]')) return false;
            if (el.closest('header, nav, [role="navigation"], form')) return false;

            const txt = (el.innerText || "").trim();
            if (!txt || txt.length < 1) return false;

            // Unanchored rejection of system UI text, tooltips, and file drop hints
            if (/(drag\s*(&|and)\s*drop|upload|snapchat for web|you are using|no longer present|type a message|send a chat|press enter|delivered|opened|received)/i.test(txt)) return false;

            // Skip pure dates and timestamps
            if (/^(january|february|march|april|may|june|july|august|september|october|november|december)\b/i.test(txt)) return false;
            if (/^\d+\s*(m|h|d|s|min|hr|day|sec)s?$/i.test(txt)) return false;
            if (/^(today|yesterday|now|just now)$/i.test(txt)) return false;

            return true;
        });

        if (candidates.length === 0) return;

        // Bottom-up scan: Find the most recent message bubble in the conversation
        let targetRow = null;
        let incomingText = "";
        let norm = "";

        for (let i = candidates.length - 1; i >= 0; i--) {
            const el = candidates[i];
            const txt = (el.innerText || "").trim();
            if (!txt || txt.length < 1) continue;

            const n = normalizeText(txt);

            // If the latest message in chat is an outgoing Friday message, we have already replied!
            if (isFridayMessage(n, el)) {
                return;
            }

            // Found the latest genuine incoming message from contact!
            targetRow = el;
            incomingText = txt;
            norm = n;
            break;
        }

        if (!targetRow || !incomingText) return;

        // B. Have we already processed this EXACT bubble or exact text?
        if (targetRow === lastProcessedElement || norm === lastProcessedText) {
            return;
        }

        // C. Legitimate new incoming message detected! Lock processing immediately!
        isProcessing = true;
        lastProcessedText = norm;
        lastProcessedElement = targetRow;

        console.log("[FRIDAY Snapchat Bridge] >>> New incoming message from contact:", incomingText);
        updateBadge(`Thinking: "${incomingText.slice(0, 16)}..."`, "#f59e0b", "🟡");

        // 10-second safety watchdog
        if (watchdogTimer) clearTimeout(watchdogTimer);
        watchdogTimer = setTimeout(() => {
            if (isProcessing) {
                console.warn("[FRIDAY Snapchat Bridge] Watchdog timeout - unlocking");
                isProcessing = false;
                updateBadge("Watching Chat", "#10b981", "🟢");
            }
        }, 10000);

        notifyFriday(incomingText);
    }

    // =========================================================================
    // SAFE MUTATION OBSERVER (Zero freeze - completely ignores HUD mutations)
    // =========================================================================

    const observer = new MutationObserver((mutations) => {
        if (isProcessing) return;

        // Skip mutation batches that only affect Friday's own badge
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

        // METHOD 3: If Friday recently sent a reply, ensure newly inserted bubble is stamped instantly
        if (recentSentReplies.length > 0) {
            stampFridayBubble(recentSentReplies[recentSentReplies.length - 1]);
        }

        if (debounceTimer) clearTimeout(debounceTimer);
        // 2.0 second human debounce gives contact time to complete thoughts
        debounceTimer = setTimeout(checkAndProcess, 2000);
    });

    function startObserving() {
        observer.observe(document.body, { childList: true, subtree: true });
        console.log("[FRIDAY Snapchat Bridge v2.0] Watching chat for incoming messages...");
        updateBadge("Watching Chat", "#10b981", "🟢");
        setTimeout(checkAndProcess, 1000);
    }

    setTimeout(startObserving, 1500);

    // =========================================================================
    // SERVER IPC CALL (Single clean call to 127.0.0.1:8765)
    // =========================================================================

    function notifyFriday(text) {
        console.log("[FRIDAY Snapchat Bridge] Calling 127.0.0.1:8765/incoming with:", text);
        
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
                    console.error("[FRIDAY Snapchat Bridge] Bridge offline on 127.0.0.1:8765", err);
                    updateBadge("Bridge Offline", "#ef4444", "🔴");
                    if (watchdogTimer) clearTimeout(watchdogTimer);
                    setTimeout(() => { isProcessing = false; }, 3000);
                },
                ontimeout: function() {
                    console.warn("[FRIDAY Snapchat Bridge] Bridge request timed out");
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
                console.error("[FRIDAY Snapchat Bridge] Fetch error:", err);
                updateBadge("Bridge Offline", "#ef4444", "🔴");
                if (watchdogTimer) clearTimeout(watchdogTimer);
                setTimeout(() => { isProcessing = false; }, 3000);
            });
        }
    }

    function handleServerResponse(responseText) {
        if (watchdogTimer) clearTimeout(watchdogTimer);
        try {
            console.log("[FRIDAY Snapchat Bridge] Server raw response:", responseText);
            const data = JSON.parse(responseText);
            if (data && data.should_reply && data.reply) {
                console.log("[FRIDAY Snapchat Bridge] Received reply:", data.reply);
                updateBadge(`Replying: "${data.reply.slice(0, 16)}..."`, "#3b82f6", "🔵");
                typeAndSend(data.reply);
            } else {
                console.log("[FRIDAY Snapchat Bridge] Server opted not to reply:", data);
                updateBadge("Watching Chat", "#10b981", "🟢");
                setTimeout(() => {
                    isProcessing = false;
                    lastProcessedElement = null;
                    lastProcessedText = "";
                }, 1000);
            }
        } catch (e) {
            console.error("[FRIDAY Snapchat Bridge] JSON parse error:", e);
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
                    console.log("[FRIDAY Snapchat Bridge] Found pending outbound message to send:", data.message);
                    updateBadge(`Sending: "${data.message.slice(0, 14)}..."`, "#3b82f6", "🔵");
                    typeAndSend(data.message);
                }
            } catch (e) {
                // Ignore silent JSON error
            }
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

    // Check for pending intro dispatch shortly after loading and periodically
    setTimeout(checkPendingOutbound, 2000);
    setTimeout(checkPendingOutbound, 4000);
    setInterval(checkPendingOutbound, 4000);

    // =========================================================================
    // 100% NATIVE DOM SEND ENGINE (VERIFIED 250MS DELAY - ZERO PYAUTOGUI)
    // =========================================================================

    function typeAndSend(replyText) {
        if (!replyText || !replyText.trim()) return;

        isProcessing = true;
        const normReply = normalizeText(replyText);
        sentByFridayCache.add(normReply);
        recentSentReplies.push(replyText);
        if (recentSentReplies.length > 20) recentSentReplies.shift();

        // Only add distinct full sentences (>20 chars) to cache to prevent collision with short human replies
        replyText.split(/[.!?।\n]+/).forEach(s => {
            const sn = normalizeText(s);
            if (sn.length > 20) sentByFridayCache.add(sn);
        });

        // Find Snapchat's contenteditable input box (div.euylb / div.nonIntl)
        const input = document.querySelector('div.euylb') || 
                      document.querySelector('div.nonIntl[contenteditable="true"]') ||
                      document.querySelector('div[contenteditable="true"]');

        if (!input) {
            console.error("[FRIDAY Snapchat Bridge] Text input not found.");
            updateBadge("Input Not Found", "#ef4444", "🔴");
            isProcessing = false;
            return;
        }

        // 1. Focus the exact element and insert text natively
        input.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, replyText);
        input.dispatchEvent(new Event('input', { bubbles: true }));

        // 2. Verified 250ms delay for React editor state sync, then fire Enter strictly on input
        setTimeout(() => {
            const enterDown = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            input.dispatchEvent(enterDown);

            console.log("[FRIDAY Snapchat Bridge] Reply sent successfully via DOM:", replyText);
            updateBadge("Reply Sent!", "#10b981", "🟢");

            // 3. METHOD 3: THE 100% BULLETPROOF DOM STAMP (dataset.fridaySent)
            // Schedule progressive stamping to tag newly rendered bubble in React DOM
            const stampDelays = [80, 200, 400, 800, 1500, 2500];
            stampDelays.forEach(delay => {
                setTimeout(() => {
                    stampFridayBubble(replyText);
                }, delay);
            });

            // Release processing lock after 2 seconds and reset tracking
            setTimeout(() => {
                isProcessing = false;
                lastProcessedElement = null;
                lastProcessedText = "";
                updateBadge("Watching Chat", "#10b981", "🟢");
            }, 2000);
        }, 250);
    }
})();
