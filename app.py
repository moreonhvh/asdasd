import os
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
colab_urls = []

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
      background: #f0f2f5;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }
    .card {
      background: white;
      border-radius: 16px;
      padding: 32px 28px;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    h1 { font-size: 20px; font-weight: 600; color: #1a1a2e; margin-bottom: 24px; text-align: center; }
    .field { margin-bottom: 16px; }
    label { display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 6px; }
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
    .status {
      margin-top: 20px; padding: 14px 16px;
      border-radius: 10px; font-size: 15px; display: none;
    }
    .success { background: #f0fdf4; border: 1.5px solid #86efac; color: #166534; display: block; }
    .error   { background: #fef2f2; border: 1.5px solid #fca5a5; color: #991b1b; display: block; }
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
    <div class="field">
      <label>Инвайт-код</label>
      <input type="text" id="code" placeholder="HDMN-XXXX" autocomplete="off" autocapitalize="characters">
    </div>
    <div class="field">
      <label>Электронная почта</label>
      <input type="email" id="email" placeholder="example@mail.com" autocomplete="off">
    </div>
    <button id="btn" onclick="submit()">Получить тестовый период</button>
    <div class="status" id="status"></div>
  </div>
  <script>
    // Сохраняем код чтобы не вводить каждый раз
    window.onload = () => {
      const saved = localStorage.getItem('invite_code');
      if (saved) document.getElementById('code').value = saved;
    };

    async function submit() {
      const code = document.getElementById('code').value.trim();
      const email = document.getElementById('email').value.trim();
      const btn = document.getElementById('btn');
      const status = document.getElementById('status');

      if (!code) { show('Введите инвайт-код', false); return; }
      if (!email) { show('Введите email', false); return; }

      localStorage.setItem('invite_code', code);
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>Отправляем...';
      status.className = 'status';

      try {
        const res = await fetch('/demo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, email })
        });
        const data = await res.json();
        show(data.message, data.status === 'success');
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
      if (e.key === 'Enter') submit();
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


@app.route('/register', methods=['POST'])
def register():
    global colab_urls
    data = request.get_json()
    if data.get('secret', '') != REGISTER_SECRET:
        return jsonify({'status': 'error'}), 401
    url = data.get('url', '').strip()
    if url and url not in colab_urls:
        colab_urls.append(url)
    return jsonify({'status': 'ok', 'mirrors': len(colab_urls)})


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

    if not colab_urls:
        return jsonify({'status': 'error', 'message': 'Сервис временно недоступен. Попробуйте позже.'})

    url = random.choice(colab_urls)
    try:
        r = requests.post(f'{url}/demo', json={'email': email}, timeout=20)
        return jsonify(r.json())
    except requests.RequestException:
        colab_urls.remove(url)
        return jsonify({'status': 'error', 'message': 'Ошибка соединения. Попробуй ещё раз.'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
