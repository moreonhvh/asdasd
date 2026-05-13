import os
import time
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

INVITE_CODES = set(
    c.strip().upper()
    for c in os.environ.get('INVITE_CODES', 'TEST').split(',')
    if c.strip()
)

REGISTER_SECRET = os.environ.get('REGISTER_SECRET', '')
MIRROR_TTL = 14 * 3600  # 14 часов в секундах
colab_urls = []  # [{'url': '...', 'expires': timestamp}]



def active_mirrors():
    now = time.time()
    return [m for m in colab_urls if m['expires'] > now]

HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HDMN — Тестовый доступ</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f2f5; min-height: 100vh;
      display: flex; align-items: center; justify-content: center; padding: 16px;
    }
    .card {
      background: white; border-radius: 16px; padding: 32px 28px;
      width: 100%; max-width: 400px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    h1 { font-size: 20px; font-weight: 600; color: #1a1a2e; margin-bottom: 24px; text-align: center; }
    .field { margin-bottom: 16px; }
    label { display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 6px; }
    .email-row { display: flex; gap: 8px; }
    .email-row input { flex: 1; }
    input {
      width: 100%; padding: 12px 14px;
      border: 1.5px solid #ddd; border-radius: 10px;
      font-size: 15px; outline: none; transition: border-color 0.2s;
    }
    input:focus { border-color: #6c63ff; }
    button {
      width: 100%; padding: 14px; background: #6c63ff;
      color: white; border: none; border-radius: 10px;
      font-size: 16px; font-weight: 600; cursor: pointer;
      margin-top: 8px; transition: background 0.2s;
    }
    button:hover { background: #5a52d5; }
    button:disabled { background: #b0abf0; cursor: not-allowed; }
    .btn-tmp {
      width: auto; margin: 0; padding: 12px 14px;
      font-size: 13px; background: #e0e7ff; color: #4338ca;
      border-radius: 10px; white-space: nowrap;
    }
    .btn-tmp:hover { background: #c7d2fe; }
    .btn-check {
      background: #059669; margin-top: 10px; font-size: 15px;
    }
    .btn-check:hover { background: #047857; }
    .status {
      margin-top: 20px; padding: 14px 16px;
      border-radius: 10px; font-size: 15px; display: none;
    }
    .success { background: #f0fdf4; border: 1.5px solid #86efac; color: #166534; display: block; }
    .error   { background: #fef2f2; border: 1.5px solid #fca5a5; color: #991b1b; display: block; }
    .mail-body {
      margin-top: 16px; padding: 14px; background: #f8fafc;
      border-radius: 10px; font-size: 14px; color: #334155;
      border: 1.5px solid #e2e8f0; display: none; white-space: pre-wrap; word-break: break-word;
    }
    .mirrors-badge {
      text-align: center; font-size: 12px; color: #888;
      margin-bottom: 20px;
    }
    .mirrors-badge span {
      display: inline-block; padding: 3px 10px;
      border-radius: 20px; font-weight: 600;
    }
    .mirrors-ok { background: #f0fdf4; color: #166534; }
    .mirrors-none { background: #fef2f2; color: #991b1b; }
    .spinner {
      display: inline-block; width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,0.4); border-top-color: white;
      border-radius: 50%; animation: spin 0.7s linear infinite;
      vertical-align: middle; margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="card">
    <h1>HDMN — Тестовый доступ</h1>
    <div class="mirrors-badge">
      <span id="mirrorsLabel">⏳ проверяем...</span>
    </div>
    <div class="field">
      <label>Инвайт-код</label>
      <input type="text" id="code" placeholder="HDMN-XXXX" autocomplete="off" autocapitalize="characters">
    </div>
    <div class="field">
      <label>Электронная почта</label>
      <div class="email-row">
        <input type="email" id="email" placeholder="example@mail.com" autocomplete="off">
        <button class="btn-tmp" onclick="getTempMail()" id="tmpBtn">📧 Temp</button>
      </div>
    </div>
    <button id="btn" onclick="submitDemo()">Получить тестовый период</button>
    <button class="btn-check" id="checkBtn" onclick="checkMail()" style="display:none">📬 Проверить почту</button>
    <div class="status" id="status"></div>
    <div class="mail-body" id="mailBody"></div>
  </div>
  <script>
    let tmpToken = '';

    async function updateMirrors() {
      try {
        const r = await fetch('/status');
        const d = await r.json();
        const el = document.getElementById('mirrorsLabel');
        if (d.mirrors > 0) {
          el.textContent = `🟢 Зеркал активно: ${d.mirrors}`;
          el.className = 'mirrors-ok';
        } else {
          el.textContent = '🔴 Нет активных зеркал';
          el.className = 'mirrors-none';
        }
      } catch { }
    }

    window.onload = () => {
      const saved = localStorage.getItem('invite_code');
      if (saved) document.getElementById('code').value = saved;
      updateMirrors();
      setInterval(updateMirrors, 30000);
    };

    async function getTempMail() {
      const btn = document.getElementById('tmpBtn');
      btn.disabled = true;
      btn.textContent = '⏳';
      try {
        const res = await fetch('/tempmail/create');
        const data = await res.json();
        if (data.status === 'ok') {
          document.getElementById('email').value = data.email;
          tmpToken = data.mailbox_id || data.token;
          btn.textContent = '🔄 Новый';
        } else {
          btn.textContent = '❌ ' + (data.message || '');
        }
      } catch {
        btn.textContent = '❌';
      } finally {
        btn.disabled = false;
      }
    }

    async function checkMail() {
      const mailBody = document.getElementById('mailBody');
      mailBody.style.display = 'block';
      mailBody.textContent = '⏳ Проверяем...';
      try {
        const res = await fetch('/tempmail/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mailbox_id: tmpToken })
        });
        const data = await res.json();
        if (data.status === 'empty') {
          mailBody.textContent = '📭 Писем пока нет. Подожди немного и попробуй снова.';
        } else if (data.status === 'ok') {
          mailBody.textContent = data.body || '(письмо пустое)';
        } else {
          mailBody.textContent = '❌ ' + data.message;
        }
      } catch {
        mailBody.textContent = '❌ Ошибка соединения';
      }
    }

    async function submitDemo() {
      const code = document.getElementById('code').value.trim();
      const email = document.getElementById('email').value.trim();
      const btn = document.getElementById('btn');

      if (!code) { show('Введите инвайт-код', false); return; }
      if (!email) { show('Введите email', false); return; }

      localStorage.setItem('invite_code', code);
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>Отправляем...';
      document.getElementById('status').className = 'status';
      document.getElementById('checkBtn').style.display = 'none';
      document.getElementById('mailBody').style.display = 'none';

      try {
        const res = await fetch('/demo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, email })
        });
        const data = await res.json();
        show(data.message, data.status === 'success');
        if (data.status === 'success' && tmpLogin) {
          document.getElementById('checkBtn').style.display = 'block';
        }
      } catch {
        show('Ошибка соединения. Попробуй ещё раз.', false);
      } finally {
        btn.disabled = false;
        btn.innerHTML = 'Получить тестовый период';
      }
    }

    function show(msg, ok) {
      const el = document.getElementById('status');
      el.textContent = msg;
      el.className = 'status ' + (ok ? 'success' : 'error');
    }

    document.getElementById('email').addEventListener('keydown', e => {
      if (e.key === 'Enter') submitDemo();
    });
  </script>
</body>
</html>'''


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})


@app.route('/status')
def status():
    mirrors = active_mirrors()
    now = time.time()
    return jsonify({
        'mirrors': len(mirrors),
        'list': [{'url': m['url'], 'expires_in_min': int((m['expires'] - now) / 60)} for m in mirrors]
    })


@app.route('/clear', methods=['POST'])
def clear():
    global colab_urls
    data = request.get_json()
    if data.get('secret', '') != REGISTER_SECRET:
        return jsonify({'status': 'error'}), 401
    colab_urls = []
    return jsonify({'status': 'ok', 'message': 'Список зеркал очищен'})


@app.route('/deregister', methods=['POST'])
def deregister():
    global colab_urls
    data = request.get_json()
    if data.get('secret', '') != REGISTER_SECRET:
        return jsonify({'status': 'error'}), 401
    url = data.get('url', '').strip()
    colab_urls = [m for m in colab_urls if m['url'] != url]
    return jsonify({'status': 'ok', 'mirrors': len(active_mirrors())})


@app.route('/register', methods=['POST'])
def register():
    global colab_urls
    data = request.get_json()
    if data.get('secret', '') != REGISTER_SECRET:
        return jsonify({'status': 'error'}), 401
    url = data.get('url', '').strip()
    if url:
        colab_urls = [m for m in colab_urls if m['url'] != url]  # убираем дубли
        colab_urls.append({'url': url, 'expires': time.time() + MIRROR_TTL})
    mirrors = active_mirrors()
    return jsonify({'status': 'ok', 'mirrors': len(mirrors)})


@app.route('/demo', methods=['POST'])
def demo():
    global colab_urls
    import random
    data = request.get_json()
    code = (data.get('code') or '').strip().upper()
    email = (data.get('email') or '').strip()

    if code not in INVITE_CODES:
        return jsonify({'status': 'error', 'message': 'Неверный инвайт-код'})

    if not email:
        return jsonify({'status': 'error', 'message': 'Email не указан'})

    PAGE_UNAVAILABLE = 'Страница демо недоступна. Попробуй позже.'
    mirrors = active_mirrors()
    if not mirrors:
        return jsonify({'status': 'error', 'message': 'Сервис временно недоступен. Попробуйте позже.'})

    for m in random.sample(mirrors, len(mirrors)):
        url = m['url']
        try:
            r = requests.post(f'{url}/demo', json={'email': email}, timeout=60)
            result = r.json()
            if result.get('message') == PAGE_UNAVAILABLE:
                continue
            return jsonify(result)
        except requests.RequestException:
            colab_urls[:] = [x for x in colab_urls if x['url'] != url]
            continue

    return jsonify({'status': 'error', 'message': PAGE_UNAVAILABLE})


def _pick_mirror():
    import random
    mirrors = active_mirrors()
    return random.choice(mirrors)['url'] if mirrors else None


@app.route('/tempmail/create')
def tempmail_create():
    url = _pick_mirror()
    if not url:
        return jsonify({'status': 'error', 'message': 'Сервис недоступен'})
    try:
        r = requests.get(f'{url}/tempmail/create', timeout=120)
        return jsonify(r.json())
    except requests.RequestException:
        return jsonify({'status': 'error', 'message': 'Ошибка соединения'})


@app.route('/tempmail/check', methods=['POST'])
def tempmail_check():
    url = _pick_mirror()
    if not url:
        return jsonify({'status': 'error', 'message': 'Сервис недоступен'})
    try:
        r = requests.post(f'{url}/tempmail/check', json=request.get_json(), timeout=30)
        return jsonify(r.json())
    except requests.RequestException:
        return jsonify({'status': 'error', 'message': 'Ошибка соединения'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
