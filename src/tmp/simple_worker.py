"""Minimal MiniMax worker — uses the EXACT browser flow proven to work in 71s.

No subprocess. No run_minimax_motion_coach. Direct Playwright.

Usage: cd /Users/achzod/clawd/src && python3 tmp/simple_worker.py
"""
import json
import os
import sys
import time
import tempfile
import threading

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = "https://formcheck-bot.onrender.com"
TOKEN = "S1PRkPJOIpFS7nOXkBiW7GH7pS3NIBs5T_GiPUD4bgU2eg0_"
WORKER_ID = "srv-local-worker"
HEADERS = {"X-Formcheck-Internal-Token": TOKEN}
POLL_INTERVAL = 5
EXPERT_URL = "https://agent.minimax.io/expert/chat/362683345551702"

LOCAL_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "manual_minimax_local_storage_achzod.json")
SESSION_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "manual_minimax_session_storage_achzod.json")

with open(LOCAL_STORAGE_PATH) as f:
    LOCAL_STORAGE = json.load(f)
with open(SESSION_STORAGE_PATH) as f:
    SESSION_STORAGE = json.load(f)

# Import the prompt from the main module
os.environ["MINIMAX_BROWSER_ONLY"] = "true"
os.environ["MINIMAX_BROWSER_EMAIL"] = "achzodyt@gmail.com"
os.environ["MINIMAX_BROWSER_LOCAL_STORAGE_JSON"] = json.dumps(LOCAL_STORAGE)
os.environ["MINIMAX_BROWSER_SESSION_STORAGE_JSON"] = json.dumps(SESSION_STORAGE)
os.environ["MINIMAX_MOTION_COACH_EXPERT_URL"] = EXPERT_URL

from analysis.minimax_motion_coach import (
    _DEFAULT_ANALYSIS_PROMPT, _REPORT_START_TAG, _REPORT_END_TAG,
    _parse_analysis_payload, _analysis_to_payload,
)


PROMPT = _DEFAULT_ANALYSIS_PROMPT.format(start=_REPORT_START_TAG, end=_REPORT_END_TAG)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def claim_job(client):
    try:
        r = client.post(f"{BASE_URL}/internal/minimax/jobs/claim", headers=HEADERS, json={"worker_id": WORKER_ID})
        if r.status_code != 200:
            return None
        return r.json().get("job")
    except Exception as e:
        log(f"claim error: {e}")
        return None


def download_video(client, job):
    r = client.get(job["video_url"], headers=HEADERS)
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.write(r.content)
    tmp.close()
    log(f"video: {tmp.name} ({len(r.content)//1024}KB)")
    return tmp.name


def heartbeat(client, job_id):
    try:
        client.post(f"{BASE_URL}/internal/minimax/jobs/{job_id}/heartbeat", headers=HEADERS)
    except Exception:
        pass


def complete_job(client, job_id, payload):
    r = client.post(
        f"{BASE_URL}/internal/minimax/jobs/{job_id}/complete",
        headers=HEADERS,
        json={"analysis_payload": payload},
    )
    r.raise_for_status()


def fail_job(client, job_id, error):
    try:
        client.post(f"{BASE_URL}/internal/minimax/jobs/{job_id}/fail", headers=HEADERS, json={"error": str(error)[:500]})
    except Exception:
        pass


def run_browser_analysis(video_path):
    """Run the EXACT flow proven to work in browser_flow_test.py."""
    from playwright.sync_api import sync_playwright

    T0 = time.monotonic()

    def dt():
        return f"{time.monotonic()-T0:.1f}s"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            "",
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            viewport={"width": 1728, "height": 1117},
            locale="en-US",
            timezone_id="Asia/Dubai",
        )
        log(f"[{dt()}] browser launched")
        page = context.pages[0] if context.pages else context.new_page()

        state = {"responses": 0, "sent_chat_id": ""}

        def on_response(resp):
            url = str(getattr(resp, "url", "") or "")
            if "/matrix/api/v1/chat/get_chat_detail" in url:
                state["responses"] += 1
            if "/matrix/api/v1/chat/send_msg" in url:
                try:
                    cid = str(resp.json().get("chat_id", "")).strip()
                    if cid:
                        state["sent_chat_id"] = cid
                except Exception:
                    pass

        page.on("response", on_response)

        # Inject auth
        page.goto("https://agent.minimax.io", wait_until="commit", timeout=15000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        for k, v in LOCAL_STORAGE.items():
            page.evaluate(f"window.localStorage.setItem({json.dumps(k)}, {json.dumps(v)})")
        for k, v in SESSION_STORAGE.items():
            page.evaluate(f"window.sessionStorage.setItem({json.dumps(k)}, {json.dumps(v)})")
        log(f"[{dt()}] auth injected")

        # Navigate to expert
        page.goto(EXPERT_URL, wait_until="commit", timeout=30000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        log(f"[{dt()}] page loaded")

        # Wait for composer
        for _ in range(20):
            try:
                if page.locator(".tiptap-editor").first.is_visible(timeout=800):
                    break
            except Exception:
                pass
            page.wait_for_timeout(500)

        # Dismiss overlay
        try:
            overlay = page.locator("[class*='bg-utility_blanket']").first
            if overlay.is_visible(timeout=1500):
                page.evaluate("""() => {
                    document.querySelectorAll('[class*="bg-utility_blanket"], div.fixed.inset-0').forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('pointer-events', 'none', 'important');
                    });
                    document.body.style.removeProperty('overflow');
                    document.body.style.removeProperty('pointer-events');
                    document.documentElement.style.removeProperty('overflow');
                }""")
                log(f"[{dt()}] overlay dismissed")
                page.wait_for_timeout(500)
        except Exception:
            pass

        # Set prompt
        editor = page.locator(".tiptap-editor").first
        editor.click(timeout=3000, force=True)
        editor.evaluate(
            """(el, text) => {
                el.focus(); el.textContent = text;
                el.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
            }""",
            PROMPT,
        )
        log(f"[{dt()}] prompt set")

        # Upload video
        upload_input = page.locator("input[type='file']").last
        upload_input.set_input_files(video_path, timeout=30000)
        log(f"[{dt()}] file attached")

        # Wait for attachment
        fname = os.path.basename(video_path)
        try:
            page.locator(f"text={fname}").first.wait_for(timeout=15000)
        except Exception:
            page.wait_for_timeout(3000)

        # Wait for send button
        for _ in range(30):
            try:
                enabled = page.evaluate("""() => {
                    const root = document.querySelector('#input-send-icon');
                    if (!root) return false;
                    const target = root.firstElementChild || root;
                    const cn = String(target.className || '');
                    return !cn.includes('cursor-not-allowed') && !cn.includes('bg-bg_interaction_primary_inactive');
                }""")
                if enabled:
                    break
            except Exception:
                pass
            page.wait_for_timeout(500)

        # Click send
        try:
            page.locator("#input-send-icon").first.click(timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        log(f"[{dt()}] sent")
        run_browser_analysis._last_body_len = 0
        run_browser_analysis._stable_count = 0

        # Wait for response — up to 5 min
        deadline = time.monotonic() + 300
        result_text = ""
        while time.monotonic() < deadline:
            page.wait_for_timeout(3000)
            try:
                texts = page.locator("[class*='markdown']").all_inner_texts()
                total = " ".join(texts)
                if not total:
                    texts = page.locator("[class*='message']").all_inner_texts()
                    total = " ".join(texts)
            except Exception:
                total = ""

            # Use body text instead of selectors - captures everything
            try:
                total = page.locator("body").inner_text(timeout=3000)
            except Exception:
                total = ""
            import re
            has_completed_vu = (
                "Completed Video Understanding" in total
                or "</FORMCHECK_REPORT_MD>" in total
                or ("FORMCHECK_REPORT_MD" in total and "PLAN ACTION" in total.upper())
            )
            # Track body stability
            if not hasattr(run_browser_analysis, '_last_body_len'):
                run_browser_analysis._last_body_len = 0
                run_browser_analysis._stable_count = 0
            if len(total) == run_browser_analysis._last_body_len and len(total) > 3000:
                run_browser_analysis._stable_count += 1
            else:
                run_browser_analysis._stable_count = 0
            run_browser_analysis._last_body_len = len(total)
            body_stable = run_browser_analysis._stable_count >= 3  # stable for 9s
            # Done when: video understanding completed + body stable + substantial content
            is_final = has_completed_vu and body_stable and len(total) > 5000

            if int(time.monotonic() - T0) % 15 < 4:
                log(f"[{dt()}] waiting... dom={len(total)} responses={state['responses']} final={is_final}")
                try:
                    body = page.locator("body").inner_text(timeout=2000)
                    if len(body) > 500:
                        log(f"[{dt()}] body_tail: {repr(body[-400:])}")
                except Exception:
                    pass

            # If MiniMax is stuck in skills/MaxClaw mode, click End Takeover
            try:
                end_btn = page.locator("text=End Takeover").first
                if end_btn.is_visible(timeout=500) and time.monotonic() - T0 > 90:
                    end_btn.click(timeout=2000)
                    log(f"[{dt()}] clicked End Takeover")
                    page.wait_for_timeout(3000)
            except Exception:
                pass

            if is_final:
                result_text = total
                log(f"[{dt()}] REPORT DETECTED ({len(total)} chars)")
                break

        context.close()
        return result_text


def extract_minimax_response(body_text):
    """Extract only MiniMax's actual response from the full page body text.

    The body contains: nav menu + chat history + prompt + thinking + response + footer.
    The response is the last meaningful block after 'Completed Video Understanding'.
    """
    # Strategy 1: Extract tagged report
    if _REPORT_START_TAG in body_text and _REPORT_END_TAG in body_text:
        parts = body_text.split(_REPORT_START_TAG)
        # Take the LAST occurrence (the response, not the prompt echo)
        for part in reversed(parts[1:]):
            if _REPORT_END_TAG in part:
                report = part.split(_REPORT_END_TAG, 1)[0].strip()
                if len(report) > 200 and "Score global" in report:
                    return report

    # Strategy 2: Extract from "Current Process / Files" section
    # MiniMax puts the detailed response in the skills panel
    if "Description:" in body_text:
        after_desc = body_text.split("Description:")[-1]
        # Cut at footer markers
        for marker in ["You have control of the AI window", "End Takeover", "Skills are all you need"]:
            if marker in after_desc:
                after_desc = after_desc.split(marker)[0]
        if len(after_desc.strip()) > 200:
            return after_desc.strip()

    # Strategy 3: Extract after the last "Completed Video Understanding" + thinking
    if "Completed Video Understanding" in body_text:
        parts = body_text.split("Completed Video Understanding")
        last_part = parts[-1]
        # Skip thinking process header
        if "Thinking Process" in last_part:
            # Get text after the last thinking block
            think_parts = last_part.split("Thinking Process")
            for tp in reversed(think_parts):
                # Skip short thinking duration markers like "2.43s"
                clean = tp.strip()
                if len(clean) > 200:
                    # Cut footer
                    for marker in ["Skills\nMAX", "You have control", "End Takeover"]:
                        if marker in clean:
                            clean = clean.split(marker)[0]
                    if len(clean.strip()) > 200:
                        return clean.strip()

    # Strategy 4: Just find Score global pattern and take surrounding context
    import re
    match = re.search(r'(Score global[:\s]*\d+/100)', body_text)
    if match:
        pos = match.start()
        # Take 200 chars before and everything after until footer
        start = max(0, pos - 200)
        chunk = body_text[start:]
        for marker in ["Skills\nMAX", "You have control", "End Takeover", "Skills are all you need"]:
            if marker in chunk:
                chunk = chunk.split(marker)[0]
        return chunk.strip()

    return body_text


def text_to_payload(text):
    """Extract MiniMax response from body text and parse into proper payload."""
    response = extract_minimax_response(text)
    log(f"extracted response: {len(response)} chars, preview: {repr(response[:150])}")

    # Ensure the response has the FORMCHECK header so the parser finds it
    clean = response.replace('\xa0', ' ').strip()
    if 'FORMCHECK' in clean and '# FORMCHECK' not in clean:
        clean = '# ' + clean
    if _REPORT_START_TAG not in clean:
        clean = _REPORT_START_TAG + '\n' + clean + '\n' + _REPORT_END_TAG

    # Also store the full raw text as raw_response
    analysis = _parse_analysis_payload(clean)
    if not analysis.report_text or len(analysis.report_text) < len(response) // 2:
        # Parser lost content — use the full extracted response as report_text
        analysis.report_text = response.replace('\xa0', ' ')
    log(f"parsed: exercise={analysis.exercise_slug} score={analysis.score} report_len={len(analysis.report_text)}")
    return _analysis_to_payload(analysis)


def process_job(client, job):
    job_id = job["id"]
    log(f"=== JOB {job_id} START ===")

    stop = threading.Event()
    def hb():
        while not stop.is_set():
            heartbeat(client, job_id)
            stop.wait(25)
    threading.Thread(target=hb, daemon=True).start()

    video_path = None
    try:
        video_path = download_video(client, job)
        result_text = run_browser_analysis(video_path)
        if not result_text:
            raise RuntimeError("MiniMax returned empty analysis")
        payload = text_to_payload(result_text)
        complete_job(client, job_id, payload)
        log(f"=== JOB {job_id} COMPLETED ===")
    except Exception as e:
        log(f"=== JOB {job_id} FAILED: {e} ===")
        fail_job(client, job_id, str(e))
    finally:
        stop.set()
        if video_path:
            try:
                os.unlink(video_path)
            except Exception:
                pass


def main():
    log("Simple MiniMax worker started")
    log(f"Polling: {BASE_URL}")
    client = httpx.Client(timeout=120)
    while True:
        job = claim_job(client)
        if job:
            process_job(client, job)
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
