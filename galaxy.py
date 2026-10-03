import socketserver
import http.server
import threading
import webbrowser
import datetime
import random
import json
import urllib.request
import urllib.parse
import ast
import operator
import os

# =========================================================
# GALAXY SETTINGS
# =========================================================

HOST = "127.0.0.1"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

MEMORY_FILE = "galaxy_memory.json"

MONTHS = [
    "जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
    "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"
]

JOKES = [
    "प्रोग्रामर को चाय क्यों पसंद है? क्योंकि उसमें Java होता है!",
    "बग और प्रोग्रामर में दोस्ती क्यों है? क्योंकि बग कभी साथ नहीं छोड़ता।",
    "Python programmer सड़क क्यों पार करता है? क्योंकि दूसरी तरफ भी code था!"
]

# =========================================================
# MEMORY
# =========================================================

history = []

def load_memory():
    global history
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    history = data
    except Exception:
        history = []

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-50:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# =========================================================
# SAFE CALCULATOR
# =========================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos
}

def calculate_expression(expression):
    try:
        expression = expression.strip()
        tree = ast.parse(expression, mode="eval")

        def evaluate(node):
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError()
            if isinstance(node, ast.BinOp):
                left = evaluate(node.left)
                right = evaluate(node.right)
                op = OPERATORS.get(type(node.op))
                if op is None:
                    raise ValueError()
                return op(left, right)
            if isinstance(node, ast.UnaryOp):
                value = evaluate(node.operand)
                op = OPERATORS.get(type(node.op))
                if op is None:
                    raise ValueError()
                return op(value)
            raise ValueError()

        result = evaluate(tree)
        return str(result)
    except Exception:
        return None

# =========================================================
# BASIC GALAXY COMMANDS
# =========================================================

def basic_reply(text):
    t = text.lower().strip()

    if any(k in t for k in ["hello", "hi", "hey", "नमस्ते", "हेलो"]):
        return "नमस्ते बॉस! मैं GALAXY हूँ। बताइए क्या करना है?"

    if any(k in t for k in ["time", "समय", "टाइम", "samay"]):
        now = datetime.datetime.now()
        return "अभी समय है %d बजकर %d मिनट।" % (now.hour % 12 or 12, now.minute)

    if any(k in t for k in ["date", "तारीख", "डेट", "आज की तारीख"]):
        today = datetime.date.today()
        return "आज की तारीख है %d %s %d।" % (today.day, MONTHS[today.month - 1], today.year)

    if any(k in t for k in ["joke", "जोक", "चुटकुला"]):
        return random.choice(JOKES)

    if any(k in t for k in ["tumhara naam", "your name", "तुम्हारा नाम", "नाम क्या है"]):
        return "मेरा नाम GALAXY है।"

    calc_words = ["calculate", "calculator", "गणना", "हिसाब", "कितना होगा"]
    if any(k in t for k in calc_words):
        expression = t
        for word in ["calculate", "calculator", "गणना", "हिसाब", "कितना होगा", "what is"]:
            expression = expression.replace(word, "")
        result = calculate_expression(expression)
        if result is not None:
            return "जवाब है " + result

    return None

# =========================================================
# OLLAMA LOCAL AI
# =========================================================

def ask_ollama(user_text):
    recent = history[-12:]
    conversation = ""
    for item in recent:
        role = item.get("role", "user")
        content = item.get("content", "")
        conversation += role + ": " + content + "\n"

    prompt = f"""
You are GALAXY, a helpful personal AI assistant.

Instructions:
- Understand Hindi, Hinglish and English.
- Reply in the same language as the user when possible.
- Be helpful and clear.
- Do not claim to know information you do not know.
- Keep normal answers reasonably concise.

Conversation:
{conversation}

user: {user_text}

GALAXY:
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        answer = data.get("response", "").strip()
        if answer:
            return answer
    except Exception:
        return None

    return None

# =========================================================
# MAIN AI FUNCTION
# =========================================================

def galaxy_reply(text):
    text = text.strip()
    if not text:
        return "कुछ बोलिए बॉस।"

    history.append({"role": "user", "content": text})

    simple = basic_reply(text)
    if simple:
        history.append({"role": "assistant", "content": simple})
        save_memory()
        return simple

    ai_answer = ask_ollama(text)
    if ai_answer:
        history.append({"role": "assistant", "content": ai_answer})
        save_memory()
        return ai_answer

    fallback = (
        "मैंने आपका सवाल समझ लिया, लेकिन अभी local AI model उपलब्ध नहीं है।\n\n"
        "Pydroid में basic GALAXY commands चल रहे हैं।\n"
        "Full AI के लिए local model server connect करना होगा।"
    )
    history.append({"role": "assistant", "content": fallback})
    save_memory()
    return fallback

# =========================================================
# WEB PAGE
# =========================================================

PAGE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GALAXY AI</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #03030d; color: white; font-family: Arial, sans-serif; text-align: center; }
.header { padding: 20px; font-size: 28px; font-weight: bold; color: #00c8ff; }
.ring { width: 210px; height: 210px; border: 7px solid #008cff; border-radius: 50%; margin: 35px auto 20px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px #008cff, inset 0 0 20px #008cff; transition: 0.25s; }
.ring.on { border-color: #ffb400; box-shadow: 0 0 40px #ffb400, inset 0 0 30px #ffb400; }
.core { width: 95px; height: 95px; background: #00c8ff; border-radius: 50%; box-shadow: 0 0 40px #00c8ff; }
#you { min-height: 28px; color: #8193ad; padding: 5px 15px; }
#answer { min-height: 100px; padding: 20px; font-size: 21px; color: #b8ecff; }
button { border: 0; border-radius: 14px; padding: 14px 20px; margin: 6px; font-size: 17px; background: #087edf; color: white; }
button:active { transform: scale(0.95); }
input { width: 88%; padding: 15px; border-radius: 14px; border: 1px solid #168cff; background: #111827; color: white; font-size: 17px; outline: none; }
.status { min-height: 25px; color: #ff7c7c; padding: 10px; }
.small { color: #65748a; font-size: 13px; padding: 15px; }
</style>
</head>
<body>
<div class="header">🌌 GALAXY AI</div>
<div class="ring" id="ring"><div class="core"></div></div>
<div id="you">GALAXY तैयार है</div>
<div id="answer">Mic दबाओ और बोलो</div>
<div>
<button onclick="listen('hi-IN')">🎤 Hindi</button>
<button onclick="listen('en-IN')">🎤 English</button>
</div>
<br>
<input id="textBox" type="text" placeholder="अपना सवाल लिखो..." onkeydown="if(event.key==='Enter') sendText()">
<br>
<button onclick="sendText()">🚀 Send</button>
<div class="status" id="status"></div>
<div class="small">GALAXY • Local Assistant</div>

<script>
var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function get(id) { return document.getElementById(id); }

function speak(text) {
    if (!window.speechSynthesis) return;
    speechSynthesis.cancel();
    var voice = new SpeechSynthesisUtterance(text);
    voice.lang = "hi-IN";
    voice.rate = 1;
    voice.pitch = 1;
    voice.onstart = function() { get("ring").className = "ring on"; };
    voice.onend = function() { get("ring").className = "ring"; };
    speechSynthesis.speak(voice);
}

function ask(text) {
    get("answer").textContent = "GALAXY सोच रहा है...";
    fetch("/cmd?q=" + encodeURIComponent(text))
    .then(function(response) { return response.text(); })
    .then(function(result) {
        get("answer").textContent = result;
        speak(result);
    })
    .catch(function(error) { get("status").textContent = "Error: " + error; });
}

function sendText() {
    var box = get("textBox");
    var text = box.value.trim();
    if (!text) return;
    get("you").textContent = "Aap: " + text;
    box.value = "";
    ask(text);
}

function listen(language) {
    if (!SpeechRecognition) {
        get("status").textContent = "Speech Recognition available नहीं है। Chrome use करो।";
        return;
    }
    var recognition = new SpeechRecognition();
    recognition.lang = language;
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = function() {
        get("ring").className = "ring on";
        get("answer").textContent = "🎤 सुन रहा हूँ...";
        get("status").textContent = "";
    };

    recognition.onresult = function(event) {
        var text = event.results[0][0].transcript;
        get("you").textContent = "Aap: " + text;
        ask(text);
    };

    recognition.onerror = function(event) {
        get("status").textContent = "Voice Error: " + event.error;
    };

    recognition.onend = function() {
        get("ring").className = "ring";
    };

    try { recognition.start(); } 
    catch (error) { get("status").textContent = "Mic start नहीं हुआ: " + error; }
}
</script>
</body>
</html>
"""

# =========================================================
# HTTP SERVER
# =========================================================

class GalaxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/cmd":
            params = urllib.parse.parse_qs(parsed.query)
            text = params.get("q", [""])[0]
            answer = galaxy_reply(text)
            body = answer.encode("utf-8")
            content_type = "text/plain; charset=utf-8"
        else:
            body = PAGE.encode("utf-8")
            content_type = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        pass

# =========================================================
# START SERVER
# =========================================================

def start_galaxy():
    load_memory()
    socketserver.TCPServer.allow_reuse_address = True
    server = None
    selected_port = None

    for port in range(8000, 8010):
        try:
            server = socketserver.ThreadingTCPServer((HOST, port), GalaxyHandler)
            selected_port = port
            break
        except OSError:
            continue

    if server is None:
        print("\n❌ 8000-8009 में कोई port available नहीं है.")
        return

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = "http://localhost:%d" % selected_port

    print("\n================================")
    print("       🌌 GALAXY AI")
    print("================================\n")
    print("✅ GALAXY चालू हो गया!\n")
    print("🌐 URL:\n" + url + "\n")
    print("Browser खुलने का इंतजार करें...\n")
    print("बंद करने के लिए इस window में Enter दबाएँ.")
    print("================================\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        input("GALAXY बंद करने के लिए Enter दबाएँ...")
    except KeyboardInterrupt:
        pass

    print("\nGALAXY बंद हो रहा है...")
    server.shutdown()
    server.server_close()

if __name__ == "__main__":
    start_galaxy()
