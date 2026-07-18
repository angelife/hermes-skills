#!/usr/bin/env node
/**
 * ask-ai.js — Send prompts to Gemini/Claude/ChatGPT via OpenBridge browser control.
 *
 * Usage: node ask-ai.js <gemini|claude|chatgpt> "<prompt>"
 *
 * Talks to OpenBridge daemon on localhost:10088.
 * Output: AI response text to stdout. Debug logs to stderr.
 *
 * V3 (2026-07-16):
 *   - Falls back to browser_evaluate JS when browser_press not allowed
 *   - Reuses existing tabs instead of always opening new ones
 *   - Timeout fallback uses JS to read main element directly
 *   - Previous pitfalls preserved from V2
 *   - TIMEOUT 3 min (free WiFi is slow)
 *   - Waits for "is responding"/"is typing" indicators to clear
 *   - Filters out question echo (was capturing prompt text as "AI response")
 *   - Filters out UI chrome ("跳至内容", "升级", "生成图片", "mic", "Flash", etc.)
 *   - Only considers text >100 chars that doesn't match prompt
 *   - Requires 3 stable samples before confirming response complete
 *   - Click composer to focus before typing
 *   - Use browser_press('Enter') to submit (更可靠)  — user: "不提交别人怎么回答"
 *
 * Pitfalls from real use (2026-07-16 session):
 *   - On slow networks, the script can capture the question echo as a "response".
 *     If output looks like your question text repeated, the script exited too early.
 *     Fix: check if the user saw the actual response, ask them to share key points.
 *   - Only open ONE tab at a time. User explicitly forbids multiple windows.
 *   - Do NOT re-ask a question if the script failed to capture — check /tmp/ai-responses/
 *     first, or ask the user to relay what the AI said.
 */

const http = require('http');
const TIMEOUT = 180000;

function api(method, args = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ toolName: method, args });
    const req = http.request({
      hostname: '127.0.0.1', port: 10088,
      path: '/command', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error('JSON: ' + body.substring(0, 200))); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function findComposer(snap) {
  const nodes = snap?.data?.nodes || [];
  for (const n of nodes) {
    if (n.editable && n.ref) return n.ref;
    if ((n.role === 'textbox' || n.role === 'searchbox' || n.role === 'edit' || n.role === 'textarea') && n.ref) return n.ref;
  }
  return null;
}

/**
 * Try submitting via browser_evaluate JS when browser_press is not allowed.
 */
async function submitViaJS(tabId) {
  const js = `
    (function() {
      const e = document.querySelector('[contenteditable="true"]');
      if (e && e.innerText.trim().length > 0) {
        e.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
        return 'sent-via-js-keydown';
      }
      // Try send button
      const btn = document.querySelector('[data-testid="send-button"]');
      if (btn) { btn.click(); return 'clicked-send-btn'; }
      return 'no-submit-method-found';
    })()
  `;
  return await api('browser_evaluate', { tabId, expression: js });
}

async function main() {
  const target = process.argv[2];
  const prompt = process.argv[3];
  if (!target || !prompt) {
    console.error('Usage: node ask-ai.js <gemini|claude|chatgpt> "<prompt>"');
    process.exit(1);
  }
  const urls = {
    gemini: 'https://gemini.google.com/app',
    claude: 'https://claude.ai/new',
    chatgpt: 'https://chatgpt.com',
  };
  const url = urls[target];
  if (!url) { console.error('Unknown target:', target); process.exit(1); }

  // Step 1: Reuse existing tab if available, otherwise open new
  console.error(`[ob] Checking existing tabs for ${target}...`);
  const tabsRes = await api('browser_list_tabs');
  const tabs = tabsRes?.data?.tabs || [];
  let tabId = null;
  const matchStr = target === 'chatgpt' ? 'chatgpt.com' : (target === 'gemini' ? 'gemini.google.com' : target + '.ai');
  for (const t of tabs) {
    if (t.url && t.url.includes(matchStr)) {
      tabId = t.tabId;
      console.error(`[ob] Reusing tab ${tabId}: ${t.url}`);
      break;
    }
  }
  if (!tabId) {
    console.error(`[ob] Opening ${target}...`);
    const r = await api('browser_new_tab', { url });
    tabId = r?.data?.tabId;
    if (!tabId) { console.error('Failed to open tab'); process.exit(1); }
    await sleep(8000);
  } else {
    await api('browser_select_tab', { tabId });
    await sleep(3000);
  }

  // Find composer
  let ref = null;
  for (let attempt = 0; attempt < 10; attempt++) {
    await api('browser_select_tab', { tabId });
    await sleep(2000);
    const snap = await api('browser_snapshot');
    ref = await findComposer(snap);
    if (ref) break;
    console.error(`[ob] Attempt ${attempt+1}/10`);
  }
  if (!ref) { console.error('No composer found'); process.exit(1); }

  console.error(`[ob] Composer: ${ref}`);
  // Click to focus, type
  await api('browser_click', { ref });
  await sleep(500);
  await api('browser_type', { ref, text: prompt });
  await sleep(1500);

  // Submit: try browser_press, fall back to JS evaluate
  const pressResult = await api('browser_press', { keys: 'Enter' });
  if (pressResult?.error?.code === 'INVALID_PARAMS') {
    console.error(`[ob] browser_press not allowed, trying JS fallback...`);
    await submitViaJS(tabId);
  }
  console.error(`[ob] Sent! (${prompt.length} chars)`);

  // Wait for response — filter out question echo and UI chrome
  const start = Date.now();
  let lastLen = 0;
  let stableCount = 0;
  const promptPrefix = prompt.split(' ').slice(0, 3).join(' ').substring(0, 30);
  const uiChrome = /Flash|mic|plus|跳至内容|升级|生成图片|撰写或编辑|查找资料|Say something|Write a message|Send a message|准备好了|随时开始|有问题，尽管问|也可能会犯错|请核查重要信息/i;

  while (Date.now() - start < TIMEOUT) {
    await sleep(3000);
    const snap = await api('browser_snapshot');
    const nodes = snap?.data?.nodes || [];
    const allText = nodes.map(n => n.name || '').join('\n');

    // Skip if still loading
    if (/is responding|is typing|正在输入|正在思考|Gemini is|正在生成|thinking/i.test(allText)) {
      console.error(`[ob] waiting... ${Math.round((Date.now()-start)/1000)}s`);
      continue;
    }

    // Filter: keep only substantial text that isn't prompt echo or UI chrome
    const respLines = nodes
      .filter(n => n.role === 'StaticText' && n.name && n.name.length > 20)
      .map(n => n.name)
      .filter(l => !l.includes(promptPrefix))
      .filter(l => !uiChrome.test(l));
    const resp = respLines.join('\n').trim();
    const respLen = resp.length;

    if (respLen > 100) {
      if (respLen !== lastLen) {
        lastLen = respLen;
        stableCount = 0;
        console.error(`[ob] ${respLen} chars... ${Math.round((Date.now()-start)/1000)}s`);
      } else {
        stableCount++;
        if (stableCount >= 3 || respLen > 2000) {
          console.error(`[ob] ✓ ${respLen} chars (${Math.round((Date.now()-start)/1000)}s)`);
          console.log(resp);
          return;
        }
      }
    } else {
      console.error(`[ob] ${Math.round((Date.now()-start)/1000)}s content=${respLen}chars`);
    }
  }

  // Timeout fallback — try reading main element directly via JS
  console.error('[ob] Timeout, trying JS fallback...');
  const jsResult = await api('browser_evaluate', {
    tabId,
    expression: "document.querySelector('main')?.innerText || document.body.innerText"
  });
  const fallbackText = jsResult?.data?.result || '';
  const filtered = fallbackText.split('\n').filter(l => !uiChrome.test(l) && l.length > 30).join('\n\n');
  if (filtered.length > 100) {
    console.log(filtered);
  } else {
    console.error('[ob] No substantial response captured via snapshot or JS');
  }
}

main().catch(e => { console.error('[ob] Error:', e.message); process.exit(1); });
