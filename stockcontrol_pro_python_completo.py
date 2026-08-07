import os
import csv
import json
import sqlite3
import webbrowser
from datetime import datetime
from io import StringIO
from flask import Flask, render_template_string, request, jsonify, Response

app = Flask(__name__)
app.secret_key = "stockcontrol_secret_key_python_full"
DB_FILE = "stockcontrol.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    # Tabela de Categorias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')

    # Tabela de Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            department TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            min_quantity INTEGER DEFAULT 2,
            has_serial INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'un'
        )
    ''')

    # Tabela de Números de Série (S/N)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS serials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT UNIQUE NOT NULL,
            product_id INTEGER,
            department TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DISPONIVEL',
            recipient TEXT,
            last_movement_date TEXT,
            operator TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabela de Movimentações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            department TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            transaction_type TEXT,
            recipient TEXT,
            purpose TEXT,
            operator TEXT NOT NULL,
            date_time TEXT NOT NULL,
            iso_date TEXT NOT NULL,
            reason TEXT
        )
    ''')
    
    # Inserção de Usuários padrão
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO users (username, password, role, department)
            VALUES (?, ?, ?, ?)
        ''', [
            ('admin', '123', 'Administrador', 'ALL'),
            ('operador_ti', '123', 'Operador', 'TI'),
            ('operador_adm', '123', 'Operador', 'ADM')
        ])
        
    # Inserção de Categorias padrão
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO categories (name, department)
            VALUES (?, ?)
        ''', [
            ('Hardware', 'TI'), ('Periféricos', 'TI'), ('Rede & Conectividade', 'TI'), ('Acessórios', 'TI'),
            ('Iluminação', 'ADM'), ('Mobiliário', 'ADM'), ('Limpeza & Copa', 'ADM'), ('Elétrica', 'ADM')
        ])

    # Inserção de Produtos padrão
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO products (id, sku, name, category, department, quantity, min_quantity, has_serial, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (1, 'NTB-DEL-15', 'Notebook Dell Latitude 3420', 'Hardware', 'TI', 6, 2, 1, 'un'),
            (2, 'MON-LG-29', 'Monitor LG UltraWide 29"', 'Hardware', 'TI', 4, 1, 1, 'un'),
            (3, 'MOU-LOG-M170', 'Mouse Sem Fio Logitech M170', 'Periféricos', 'TI', 15, 5, 0, 'un'),
            (4, 'LAM-LED-18W', 'Lâmpada LED Tubular 18W Bivolt', 'Iluminação', 'ADM', 30, 10, 0, 'un'),
            (5, 'PAP-A4-CHAM', 'Papel A4 Chamex 500 Folhas', 'Limpeza & Copa', 'ADM', 45, 15, 0, 'cx'),
            (6, 'DET-5L-CONC', 'Detergente Multiuso 5 Litros', 'Limpeza & Copa', 'ADM', 10, 4, 0, 'gl')
        ])

    # Inserção de Seriais padrão
    cursor.execute("SELECT COUNT(*) FROM serials")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
        cursor.executemany('''
            INSERT INTO serials (serial_number, product_id, department, status, recipient, last_movement_date, operator)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('SN-DEL-90001', 1, 'TI', 'DISPONIVEL', '-', now_str, 'admin'),
            ('SN-DEL-90002', 1, 'TI', 'EMPRESTADO', 'Carlos Eduardo - Vendas', now_str, 'admin'),
            ('SN-MON-88001', 2, 'TI', 'DISPONIVEL', '-', now_str, 'admin')
        ])
        
    conn.commit()
    conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "department": user['department']
            }
        })
    return jsonify({"success": False, "message": "Usuário ou senha incorretos!"}), 401

@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'GET':
        cursor.execute("SELECT id, username, password, role, department FROM users ORDER BY username ASC")
        users = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify(users)
    else:
        data = request.json or {}
        user_id = data.get('id')
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', 'Operador')
        department = data.get('department', 'TI')

        if user_id and int(user_id) > 0:
            cursor.execute("UPDATE users SET username=?, password=?, role=?, department=? WHERE id=?", 
                           (username, password, role, department, user_id))
        else:
            cursor.execute("INSERT INTO users (username, password, role, department) VALUES (?, ?, ?, ?)",
                           (username, password, role, department))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/user/password', methods=['POST'])
def api_change_password():
    data = request.json or {}
    username = data.get('username')
    new_password = data.get('new_password')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/workspace/<dept>', methods=['GET'])
def api_workspace_data(dept):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM categories WHERE department = ? OR department = 'ALL' ORDER BY name ASC", (dept,))
    categories = [r['name'] for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM products WHERE department = ? ORDER BY name ASC", (dept,))
    products = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM serials WHERE department = ? ORDER BY id DESC", (dept,))
    serials = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM movements WHERE department = ? ORDER BY id DESC", (dept,))
    movements = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        "categories": categories,
        "products": products,
        "serials": serials,
        "movements": movements
    })

@app.route('/api/products', methods=['POST'])
def api_save_product():
    data = request.json or {}
    prod_id = data.get('id')
    sku = data.get('sku', '').strip().upper()
    name = data.get('name', '').strip()
    category = data.get('category', 'Geral')
    department = data.get('department', 'TI')
    quantity = int(data.get('quantity', 0))
    min_quantity = int(data.get('min_quantity', 2))
    has_serial = 1 if data.get('has_serial') else 0
    unit = data.get('unit', 'un')
    initial_serials = data.get('initial_serials', [])
    operator = data.get('operator', 'admin')

    conn = get_db()
    cursor = conn.cursor()

    if prod_id and int(prod_id) > 0:
        cursor.execute('''
            UPDATE products 
            SET sku=?, name=?, category=?, quantity=?, min_quantity=?, has_serial=?, unit=?
            WHERE id=?
        ''', (sku, name, category, quantity, min_quantity, has_serial, unit, prod_id))
    else:
        cursor.execute('''
            INSERT INTO products (sku, name, category, department, quantity, min_quantity, has_serial, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sku, name, category, department, quantity, min_quantity, has_serial, unit))
        prod_id = cursor.lastrowid

        # Se tiver controle por número de série e houverem seriais inseridos
        if has_serial and initial_serials:
            now_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
            for sn in initial_serials:
                sn_clean = sn.strip()
                if sn_clean:
                    cursor.execute('''
                        INSERT OR IGNORE INTO serials (serial_number, product_id, department, status, recipient, last_movement_date, operator)
                        VALUES (?, ?, ?, 'DISPONIVEL', '-', ?, ?)
                    ''', (sn_clean, prod_id, department, now_str, operator))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/products/<int:prod_id>', methods=['DELETE'])
def api_delete_product(prod_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    cursor.execute("DELETE FROM serials WHERE product_id = ?", (prod_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/movement', methods=['POST'])
def api_add_movement():
    data = request.json or {}
    product_id = int(data.get('product_id'))
    move_type = data.get('type')  # 'IN' ou 'OUT'
    quantity = int(data.get('quantity', 1))
    transaction_type = data.get('transaction_type', 'Geral')
    recipient = data.get('recipient', 'Uso Interno')
    reason = data.get('reason', '')
    operator = data.get('operator', 'admin')
    department = data.get('department', 'TI')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()

    if not prod:
        conn.close()
        return jsonify({"success": False, "message": "Produto não encontrado!"}), 404

    current_qty = prod['quantity']
    if move_type == 'OUT' and quantity > current_qty:
        conn.close()
        return jsonify({"success": False, "message": "Estoque insuficiente para esta saída!"}), 400

    new_qty = current_qty + quantity if move_type == 'IN' else current_qty - quantity
    cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, product_id))

    now = datetime.now()
    now_str = now.strftime('%d/%m/%Y às %H:%M')
    iso_str = now.isoformat()

    cursor.execute('''
        INSERT INTO movements (product_id, product_name, department, type, quantity, transaction_type, recipient, purpose, operator, date_time, iso_date, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (product_id, prod['name'], department, move_type, quantity, transaction_type, recipient, transaction_type, operator, now_str, iso_str, reason))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/export/csv/<dept>', methods=['GET'])
def api_export_csv(dept):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, sku, category, quantity, min_quantity, has_serial, unit FROM products WHERE department = ?", (dept,))
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Produto', 'SKU', 'Categoria', 'Quantidade', 'Estoque Minimo', 'Tem Serial', 'Unidade'])
    for r in rows:
        cw.writerow([r['name'], r['sku'], r['category'], r['quantity'], r['min_quantity'], 'SIM' if r['has_serial'] else 'NAO', r['unit']])

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=estoque_{dept}_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.route('/api/import/csv/<dept>', methods=['POST'])
def api_import_csv(dept):
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nenhum arquivo CSV enviado"}), 400

    file = request.files['file']
    stream = StringIO(file.stream.read().decode("UTF-8"), newline=None)
    csv_input = csv.reader(stream)

    conn = get_db()
    cursor = conn.cursor()
    count = 0
    for idx, row in enumerate(csv_input):
        if idx == 0 or not row:
            continue
        name = row[0].strip().replace('"', '')
        qty = int(row[1].strip()) if len(row) > 1 and row[1].strip().isdigit() else 0
        if name:
            cursor.execute('''
                INSERT INTO products (sku, name, category, department, quantity, min_quantity, has_serial, unit)
                VALUES (?, ?, ?, ?, ?, 2, 0, 'un')
            ''', (f"SKU-{int(datetime.now().timestamp())}-{idx}", name, "Geral", dept, qty))
            count += 1

    conn.commit()
    conn.close()
    return jsonify({"success": True, "count": count})

@app.route('/api/export/json', methods=['GET'])
def api_export_json():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM movements")
    movements = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM serials")
    serials = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM users")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()

    data = {"products": products, "movements": movements, "serials": serials, "users": users}
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename=backup_stockcontrol_{datetime.now().strftime('%Y%m%d')}.json"}
    )

@app.route('/api/reset/<dept>', methods=['POST'])
def api_reset_dept(dept):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE department = ?", (dept,))
    cursor.execute("DELETE FROM movements WHERE department = ?", (dept,))
    cursor.execute("DELETE FROM serials WHERE department = ?", (dept,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR" class="h-full bg-purple-100">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StockControl Pro - Gestão Integrada de Estoque</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #c4b5fd; border-radius: 4px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #a78bfa; }

    .glass-card {
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(20px);
      box-shadow: 0 25px 50px -12px rgba(76, 29, 149, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.6);
    }
    .fun-bg { background: linear-gradient(135deg, #2e1065 0%, #4c1d95 35%, #581c87 70%, #3b0764 100%); }

    @keyframes float-slow {
      0%, 100% { transform: translateY(0px) rotate(0deg); }
      50% { transform: translateY(-12px) rotate(2deg); }
    }
    @keyframes float-reverse {
      0%, 100% { transform: translateY(0px) rotate(0deg); }
      50% { transform: translateY(10px) rotate(-2deg); }
    }
    .animate-float { animation: float-slow 6s ease-in-out infinite; }
    .animate-float-delayed { animation: float-reverse 7s ease-in-out infinite 1s; }
  </style>
</head>
<body class="h-full bg-purple-100 text-slate-800 flex flex-col antialiased selection:bg-purple-500 selection:text-white">

  <!-- NOTIFICAÇÕES TOAST -->
  <div id="toast-container" class="fixed top-5 right-5 z-50 space-y-2 pointer-events-none"></div>

  <!-- MODAL CONFIRMAÇÃO CUSTOMIZADO -->
  <div id="modal-confirm" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl text-center">
      <div class="w-12 h-12 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto text-xl">
        <i class="fa-solid fa-triangle-exclamation"></i>
      </div>
      <h3 id="confirm-title" class="font-extrabold text-slate-900 text-base">Confirmar Ação</h3>
      <p id="confirm-message" class="text-xs text-slate-600 font-semibold"></p>
      <div class="flex gap-2 pt-2">
        <button onclick="closeConfirmModal(false)" class="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl">Cancelar</button>
        <button id="btn-confirm-action" class="flex-1 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow">Confirmar</button>
      </div>
    </div>
  </div>

  <!-- TELA DE LOGIN COM ILUSTRAÇÃO DIVERTIDA -->
  <div id="login-view" class="fixed inset-0 z-50 flex items-center justify-center p-4 fun-bg overflow-hidden">
    <div class="absolute inset-0 pointer-events-none select-none overflow-hidden">
      <div class="absolute -top-32 -left-32 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 -right-32 w-[500px] h-[500px] bg-pink-500/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-32 left-1/3 w-96 h-96 bg-indigo-500/30 rounded-full blur-3xl"></div>

      <svg class="w-full h-full object-cover opacity-90" viewBox="0 0 1440 900" fill="none">
        <g class="animate-float">
          <path d="M-100 650 L600 850" stroke="#a855f7" stroke-width="32" stroke-linecap="round" stroke-dasharray="24 16"/>
          <path d="M-100 650 L600 850" stroke="#c084fc" stroke-width="8" stroke-linecap="round"/>
          <g transform="translate(120, 640) rotate(15)">
            <rect width="70" height="60" rx="12" fill="#fbbf24" stroke="#d97706" stroke-width="4"/>
            <path d="M0 25 L70 25" stroke="#d97706" stroke-width="3"/>
            <rect x="25" y="10" width="20" height="12" rx="3" fill="#fef3c7"/>
            <text x="35" y="19" font-size="8" font-weight="bold" fill="#b45309" text-anchor="middle">TI</text>
          </g>
        </g>
        <g class="animate-float-delayed">
          <path d="M800 200 L1550 400" stroke="#818cf8" stroke-width="28" stroke-linecap="round" stroke-dasharray="20 12"/>
          <g transform="translate(1050, 210) rotate(12)">
            <rect width="90" height="65" rx="10" fill="#38bdf8" stroke="#0284c7" stroke-width="4"/>
            <rect x="10" y="10" width="70" height="45" rx="6" fill="#0284c7"/>
          </g>
        </g>
      </svg>
    </div>

    <!-- CARD CENTRAL DE LOGIN -->
    <div class="glass-card relative z-10 w-full max-w-[420px] p-8 rounded-3xl text-center shadow-2xl">
      <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-tr from-purple-600 to-indigo-500 text-white rounded-2xl mb-4 shadow-lg shadow-purple-500/40 ring-4 ring-purple-100">
        <i class="fa-solid fa-boxes-stacked text-3xl"></i>
      </div>

      <h2 class="text-2xl font-black text-slate-900 tracking-tight">StockControl <span class="text-purple-600">Pro</span></h2>
      <p class="text-xs font-semibold text-slate-500 mt-1 mb-6">Controle de Ativos</p>

      <form id="form-login" onsubmit="handleLoginSubmit(event)" class="space-y-4 text-left">
        <div>
          <label class="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">USUÁRIO</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
              <i class="fa-solid fa-user text-xs"></i>
            </span>
            <input type="text" id="loginUsername" value="" required placeholder="Digite seu usuário" class="w-full pl-9 pr-4 py-2.5 text-xs font-semibold bg-slate-50/80 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-purple-600 outline-none transition-all">
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">SENHA</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
              <i class="fa-solid fa-lock text-xs"></i>
            </span>
            <input type="password" id="loginPassword" value="" required placeholder="••••••••" class="w-full pl-9 pr-4 py-2.5 text-xs font-semibold bg-slate-50/80 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-purple-600 outline-none transition-all">
          </div>
        </div>

        <button type="submit" class="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center gap-2">
          <span>Acessar Painel</span>
          <i class="fa-solid fa-arrow-right text-xs"></i>
        </button>
      </form>
    </div>

    <!-- ASSINATURA -->
    <div class="fixed bottom-3 left-4 z-20 text-[10px] font-bold text-purple-300/80 tracking-wider uppercase flex items-center gap-1.5 opacity-80 select-none">
      <i class="fa-solid fa-code text-purple-400 text-[9px]"></i>
      Powered by <span class="text-white font-extrabold">Wesley Duarte</span>
    </div>
  </div>

  <!-- APLICAÇÃO PRINCIPAL -->
  <div id="app-view" class="hidden flex-1 flex flex-col min-h-screen relative">
    <header class="bg-purple-950 text-white sticky top-0 z-30 shadow-md border-b border-purple-900/50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-14">
          <div class="flex items-center gap-3">
            <div class="bg-purple-600 p-1.5 rounded-lg text-white shadow-lg shadow-purple-600/30">
              <i class="fa-solid fa-boxes-stacked text-lg"></i>
            </div>
            <div>
              <h1 class="font-bold text-base leading-tight tracking-wide">StockControl <span class="text-[10px] bg-purple-600 text-white px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">Pro</span></h1>
              <p class="text-[10px] text-purple-300">Controle de Ativos</p>
            </div>
          </div>

          <nav class="hidden md:flex space-x-1">
            <button onclick="switchTab('dashboard')" id="nav-dashboard" class="nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1 bg-purple-600 text-white shadow-sm">
              <i class="fa-solid fa-chart-pie"></i> Painel Geral
            </button>
            <button onclick="switchTab('products')" id="nav-products" class="nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1 text-slate-300 hover:text-white hover:bg-purple-900/50">
              <i class="fa-solid fa-box-archive"></i> Produtos
            </button>
            <button onclick="switchTab('serials')" id="nav-serials" class="nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1 text-slate-300 hover:text-white hover:bg-purple-900/50">
              <i class="fa-solid fa-barcode"></i> Nº de Série (S/N)
            </button>
            <button onclick="switchTab('movements')" id="nav-movements" class="nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1 text-slate-300 hover:text-white hover:bg-purple-900/50">
              <i class="fa-solid fa-right-left"></i> Movimentações
            </button>
          </nav>

          <div class="hidden sm:flex items-center gap-1 bg-purple-950/80 border border-purple-800/60 p-1 rounded-xl">
            <button onclick="switchWorkspace('TI')" id="btn-ws-ti" class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1.5 bg-purple-600 text-white shadow-sm">
              <i class="fa-solid fa-laptop text-[10px]"></i> Estoque TI
            </button>
            <button onclick="switchWorkspace('ADM')" id="btn-ws-adm" class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all text-purple-300 hover:text-white hover:bg-purple-900/50">
              <i class="fa-solid fa-building text-[10px]"></i> Adm. Predial
            </button>
          </div>

          <div class="flex items-center gap-1.5">
            <div class="hidden sm:flex items-center gap-1 bg-purple-950/80 border border-purple-800/50 px-2 py-0.5 rounded-lg text-[11px]">
              <i class="fa-solid fa-circle-user text-purple-400 text-[10px]"></i>
              <span id="header-user-name" class="font-bold text-purple-100">admin</span>
              <span id="header-user-role" class="bg-purple-600/30 text-purple-300 border border-purple-500/30 text-[8px] px-1.5 py-0.2 rounded-full font-bold uppercase">Administrador</span>
            </div>

            <button onclick="openConfigModal()" title="Configurações & Central do Banco de Dados" class="bg-purple-800/90 hover:bg-purple-700 border border-purple-600 text-white px-2.5 py-1 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-sm">
              <i class="fa-solid fa-gear text-purple-300 text-[11px]"></i>
              <span>Configurações</span>
            </button>

            <button onclick="handleLogout()" title="Sair do sistema" class="bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 p-1.5 rounded-xl text-[11px] transition-all font-bold">
              <i class="fa-solid fa-right-from-bracket"></i>
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">

      <!-- TAB 1: PAINEL GERAL -->
      <section id="tab-dashboard" class="tab-content space-y-6">
        <div class="bg-gradient-to-r from-purple-900 via-purple-800 to-slate-900 rounded-2xl p-5 text-white shadow-md border border-purple-700/50 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <span id="active-ws-badge" class="bg-purple-500/30 text-purple-200 border border-purple-400/30 text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider inline-block mb-1">
              Estoque Ativo: TI
            </span>
            <h2 class="text-lg font-bold tracking-tight">Painel de Gestão</h2>
            <p class="text-xs text-purple-200">Acompanhe entradas, baixas, movimentações por número de série e alertas de reposição em tempo real.</p>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
            <button onclick="openStockMovementModal('IN')" class="flex-1 md:flex-none bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1 shadow-sm">
              <i class="fa-solid fa-arrow-down text-[10px]"></i> Nova Entrada
            </button>
            <button onclick="openStockMovementModal('OUT')" class="flex-1 md:flex-none bg-rose-600 hover:bg-rose-500 text-white px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1 shadow-sm">
              <i class="fa-solid fa-arrow-up text-[10px]"></i> Registrar Saída
            </button>
            <button onclick="openProductModal()" class="flex-1 md:flex-none bg-purple-600 hover:bg-purple-500 text-white px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1 shadow-sm">
              <i class="fa-solid fa-plus text-[10px]"></i> + Novo Item
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-white p-4 rounded-2xl border border-purple-100 shadow-sm flex items-center justify-between">
            <div>
              <p class="text-[11px] font-bold uppercase text-slate-500 tracking-wider">Variedade de Itens</p>
              <h3 id="dash-total-products" class="text-2xl font-black text-slate-900 mt-0.5">0</h3>
            </div>
            <div class="w-10 h-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center text-lg"><i class="fa-solid fa-boxes-stacked"></i></div>
          </div>

          <div class="bg-white p-4 rounded-2xl border border-purple-100 shadow-sm flex items-center justify-between">
            <div>
              <p class="text-[11px] font-bold uppercase text-slate-500 tracking-wider">Total em Unidades</p>
              <h3 id="dash-total-units" class="text-2xl font-black text-slate-900 mt-0.5">0 un</h3>
            </div>
            <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center text-lg"><i class="fa-solid fa-layer-group"></i></div>
          </div>

          <div onclick="switchTab('products')" class="bg-white p-4 rounded-2xl border border-purple-100 shadow-sm flex items-center justify-between cursor-pointer hover:border-amber-300 transition-colors">
            <div>
              <p class="text-[11px] font-bold uppercase text-amber-600 tracking-wider">Estoque Mínimo</p>
              <h3 id="dash-low-stock" class="text-2xl font-black text-amber-600 mt-0.5">0</h3>
            </div>
            <div class="w-10 h-10 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center text-lg"><i class="fa-solid fa-triangle-exclamation"></i></div>
          </div>

          <div class="bg-white p-4 rounded-2xl border border-purple-100 shadow-sm flex items-center justify-between">
            <div>
              <p class="text-[11px] font-bold uppercase text-purple-600 tracking-wider">S/N Rastreados</p>
              <h3 id="dash-serials-count" class="text-2xl font-black text-purple-600 mt-0.5">0</h3>
            </div>
            <div class="w-10 h-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center text-lg"><i class="fa-solid fa-barcode"></i></div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="bg-white p-5 rounded-2xl border border-purple-100 shadow-sm lg:col-span-2 flex flex-col justify-between">
            <div class="flex items-center justify-between mb-4">
              <h3 class="font-bold text-slate-800 text-sm uppercase flex items-center gap-2">
                <i class="fa-solid fa-chart-pie text-purple-600"></i> Distribuição por Categoria
              </h3>
              <span class="text-[11px] text-slate-400 font-bold">Unidades Físicas em SQLite</span>
            </div>
            <div class="h-64 relative flex items-center justify-center">
              <canvas id="chart-categories"></canvas>
            </div>
          </div>

          <div class="bg-white p-5 rounded-2xl border border-purple-100 shadow-sm flex flex-col justify-between space-y-4">
            <h3 class="font-bold text-slate-800 text-sm uppercase flex items-center gap-2">
              <i class="fa-solid fa-bell text-amber-500"></i> Alertas de Reposição
            </h3>
            <div id="dash-alerts-list" class="space-y-2 max-h-56 overflow-y-auto custom-scrollbar flex-1 pr-1"></div>
            <button onclick="switchTab('products')" class="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold py-1.5 rounded-xl text-xs transition-colors">
              Ver Todos os Produtos
            </button>
          </div>
        </div>
      </section>

      <!-- TAB 2: PRODUTOS DO ESTOQUE -->
      <section id="tab-products" class="tab-content hidden space-y-4">
        <div class="bg-white p-4 rounded-2xl shadow-sm border border-purple-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div class="relative">
              <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3 text-slate-400 text-xs"></i>
              <input type="text" id="search-product" oninput="renderProductsTable()" placeholder="Buscar por Nome ou SKU..." class="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none">
            </div>

            <select id="filter-category" onchange="renderProductsTable()" class="border border-slate-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-purple-500 outline-none bg-white font-bold">
              <option value="ALL">Todas as Categorias</option>
            </select>

            <select id="filter-status" onchange="renderProductsTable()" class="border border-slate-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-purple-500 outline-none bg-white font-bold">
              <option value="ALL">Todos os Status</option>
              <option value="OK">Estoque Normal</option>
              <option value="LOW">Estoque Mínimo</option>
              <option value="OUT">Esgotado (0 un)</option>
            </select>
          </div>

          <div class="flex items-center gap-2 flex-wrap">
            <button onclick="openProductModal()" class="bg-purple-600 hover:bg-purple-700 text-white font-bold px-3 py-2 rounded-xl text-xs transition-all shadow flex items-center gap-1.5">
              <i class="fa-solid fa-plus text-xs"></i> Novo Item
            </button>

            <!-- PERSONALIZAR COLUNAS E REORDENAÇÃO -->
            <div class="relative">
              <button onclick="toggleTableCustomizeMenu('prod-cols-menu')" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5">
                <i class="fa-solid fa-sliders text-purple-600"></i> Personalizar Colunas
              </button>
              <div id="prod-cols-menu" class="hidden absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-slate-200 p-3.5 z-30 space-y-2 text-xs font-bold">
                <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span class="text-[11px] text-slate-700 uppercase tracking-wider block font-extrabold">Organizar & Exibir Colunas</span>
                  <button onclick="resetColumnPreferences()" class="text-[10px] text-purple-600 hover:underline font-bold flex items-center gap-1">
                    <i class="fa-solid fa-rotate-left text-[9px]"></i> Padrão
                  </button>
                </div>
                <div id="customize-cols-list" class="space-y-1.5 my-2"></div>
                <hr class="border-slate-100">
                <button onclick="toggleTableDensity()" class="w-full text-left py-1 text-purple-600 hover:underline flex items-center justify-between font-bold">
                  <span>Modo Compacto</span>
                  <i id="density-icon" class="fa-solid fa-compress text-slate-400"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-purple-100 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr id="products-table-head-row" class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase text-slate-500 select-none"></tr>
              </thead>
              <tbody id="products-table-body" class="divide-y divide-slate-100 text-xs"></tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- TAB 3: CONTROLE DE NÚMEROS DE SÉRIE -->
      <section id="tab-serials" class="tab-content hidden space-y-4">
        <div class="bg-white p-4 rounded-2xl shadow-sm border border-purple-100 space-y-3">
          <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>
              <h3 class="font-bold text-slate-900 text-sm flex items-center gap-2">
                <i class="fa-solid fa-barcode text-purple-600"></i> Rastreamento Individual por Número de Série (S/N)
              </h3>
              <p class="text-xs text-slate-500">Consulte o histórico individual de equipamento cadastrado no SQLite.</p>
            </div>
            <div class="w-full sm:w-80 relative">
              <i class="fa-solid fa-search absolute left-3.5 top-3 text-slate-400 text-xs"></i>
              <input type="text" id="search-serial" oninput="renderSerialsTable()" placeholder="Pesquisar S/N ou Destinatário..." class="w-full pl-9 pr-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none">
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-purple-100 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase text-slate-500">
                  <th class="py-3 px-4">Número de Série (S/N)</th>
                  <th class="py-3 px-4">Produto</th>
                  <th class="py-3 px-4">Status</th>
                  <th class="py-3 px-4">Destinatário</th>
                  <th class="py-3 px-4">Último Operador</th>
                  <th class="py-3 px-4">Data Registro</th>
                </tr>
              </thead>
              <tbody id="serials-table-body" class="divide-y divide-slate-100 text-xs"></tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- TAB 4: HISTÓRICO DE MOVIMENTAÇÕES -->
      <section id="tab-movements" class="tab-content hidden space-y-4">
        <div class="bg-white p-4 rounded-2xl shadow-sm border border-purple-100 space-y-3">
          <div class="flex flex-col lg:flex-row items-center justify-between gap-3">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 w-full">
              <div>
                <label class="block text-[10px] font-bold text-slate-600 uppercase mb-1">Tipo de Operação</label>
                <select id="movement-type-filter" onchange="renderMovementsTable()" class="w-full border border-slate-300 rounded-xl px-2.5 py-1.5 text-xs font-bold focus:ring-2 focus:ring-purple-500">
                  <option value="ALL">Todas as Movimentações</option>
                  <option value="IN">Entradas / Devoluções (+)</option>
                  <option value="OUT">Baixas / Saídas (-)</option>
                </select>
              </div>
              <div class="col-span-2">
                <label class="block text-[10px] font-bold text-slate-600 uppercase mb-1">Busca Geral</label>
                <input type="text" id="move-filter-search" oninput="renderMovementsTable()" placeholder="Buscar por produto, beneficiário, operador..." class="w-full px-2.5 py-1.5 border border-slate-300 rounded-xl text-xs font-semibold outline-none focus:ring-2 focus:ring-purple-500">
              </div>
            </div>

            <button onclick="exportMovementsCSV()" class="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl text-xs transition-all shadow flex items-center gap-1.5 whitespace-nowrap">
              <i class="fa-solid fa-file-csv"></i> Exportar Histórico (CSV)
            </button>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-purple-100 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase text-slate-500">
                  <th class="py-3 px-4">Data e Hora</th>
                  <th class="py-3 px-4">Tipo</th>
                  <th class="py-3 px-4">Produto</th>
                  <th class="py-3 px-4 text-center">Quantidade</th>
                  <th class="py-3 px-4">Destinatário</th>
                  <th class="py-3 px-4">Responsável</th>
                  <th class="py-3 px-4">Finalidade</th>
                </tr>
              </thead>
              <tbody id="movements-table-body" class="divide-y divide-slate-100 text-xs"></tbody>
            </table>
          </div>
        </div>
      </section>
    </main>

    <!-- ASSINATURA NO CANTINHO INFERIOR ESQUERDO -->
    <div class="fixed bottom-3 left-4 z-20 pointer-events-none">
      <div class="bg-purple-950/80 backdrop-blur-md border border-purple-800/60 text-purple-200 px-2.5 py-1 rounded-lg text-[10px] font-bold shadow-lg flex items-center gap-1.5 pointer-events-auto">
        <i class="fa-solid fa-code text-purple-400 text-[9px]"></i>
        Powered by <span class="text-white font-extrabold">Wesley Duarte</span>
      </div>
    </div>
  </div>

  <!-- MODAL DE CONFIGURAÇÕES -->
  <div id="modal-config" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[92vh]">
      <div class="bg-purple-950 text-white px-6 py-4 flex items-center justify-between">
        <h3 class="font-bold text-base flex items-center gap-2">
          <i class="fa-solid fa-gear text-purple-400"></i> Configurações & Banco SQLite Python
        </h3>
        <button onclick="closeConfigModal()" class="text-slate-400 hover:text-white transition-colors">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <div class="p-6 space-y-6 overflow-y-auto custom-scrollbar">
        <div class="flex border-b border-slate-200 text-xs font-bold gap-4">
          <button onclick="switchConfigTab('database')" id="cfg-tab-database" class="pb-2 border-b-2 border-purple-600 text-purple-600 font-bold">Banco de Dados (CSV & JSON)</button>
          <button onclick="switchConfigTab('users')" id="cfg-tab-users" class="pb-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-bold">Gestão de Usuários</button>
          <button onclick="switchConfigTab('myaccount')" id="cfg-tab-myaccount" class="pb-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-bold">Minha Conta</button>
        </div>

        <div id="cfg-sec-database" class="space-y-5">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/80 flex flex-col justify-between space-y-2">
              <div>
                <h5 class="font-bold text-slate-800 text-xs uppercase flex items-center gap-1.5"><i class="fa-solid fa-file-csv text-emerald-600"></i> Exportar CSV</h5>
                <p class="text-slate-500 text-[11px]">Baixe a lista de produtos do setor ativo em formato Excel/CSV.</p>
              </div>
              <button onclick="exportProductsCSV()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl py-2 text-xs font-bold transition-all shadow flex items-center justify-center gap-2">
                <i class="fa-solid fa-file-arrow-down"></i> Baixar Produtos (CSV)
              </button>
            </div>

            <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/80 flex flex-col justify-between space-y-2">
              <div>
                <h5 class="font-bold text-slate-800 text-xs uppercase flex items-center gap-1.5"><i class="fa-solid fa-file-import text-teal-600"></i> Importar CSV</h5>
                <p class="text-slate-500 text-[11px]">Cadastre produtos via planilha CSV diretamente no banco SQLite.</p>
              </div>
              <label class="w-full bg-teal-600 hover:bg-teal-500 text-white rounded-xl py-2 text-xs font-bold transition-all shadow cursor-pointer flex items-center justify-center gap-2 text-center">
                <i class="fa-solid fa-file-circle-plus"></i> Importar Produtos (.csv)
                <input type="file" id="input-restore-csv" accept=".csv" onchange="importProductsCSV(event)" class="hidden">
              </label>
            </div>

            <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/80 flex flex-col justify-between space-y-2 col-span-2">
              <div>
                <h5 class="font-bold text-slate-800 text-xs uppercase flex items-center gap-1.5"><i class="fa-solid fa-file-code text-indigo-600"></i> Backup Completo (JSON)</h5>
                <p class="text-slate-500 text-[11px]">Gera uma cópia exata de segurança com todos os produtos e registros em JSON.</p>
              </div>
              <button onclick="exportFullJSONBackup()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl py-2 text-xs font-bold transition-all shadow flex items-center justify-center gap-2">
                <i class="fa-solid fa-download"></i> Baixar Backup Completo (.json)
              </button>
            </div>
          </div>

          <div class="pt-3 border-t border-slate-100">
            <button onclick="resetFullDatabase()" class="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold transition-colors shadow flex items-center justify-center gap-1.5">
              <i class="fa-solid fa-trash-can"></i> Zerar Banco do Setor
            </button>
          </div>
        </div>

        <div id="cfg-sec-users" class="hidden space-y-4">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-800 text-xs uppercase">Gestão de Usuários (<span id="user-count-badge">0</span>)</h4>
          </div>

          <div id="admin-users-list" class="space-y-1.5 max-h-36 overflow-y-auto custom-scrollbar pr-1"></div>

          <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
            <h5 id="admin-form-user-title" class="font-bold text-xs text-slate-800">Cadastrar Novo Usuário</h5>
            <form id="form-admin-user" onsubmit="handleAdminSaveUser(event)" class="space-y-2">
              <input type="hidden" id="admin-edit-user-id" value="0">
              <div class="grid grid-cols-3 gap-2">
                <input type="text" id="admin-user-name" required placeholder="Usuário" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs outline-none focus:ring-2 focus:ring-purple-500 font-semibold">
                <input type="password" id="admin-user-pass" required placeholder="Senha" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs outline-none focus:ring-2 focus:ring-purple-500 font-semibold">
                <select id="admin-user-role" class="px-2 py-1.5 border border-slate-300 rounded-lg text-xs outline-none focus:ring-2 focus:ring-purple-500 bg-white font-bold">
                  <option value="Operador">Operador</option>
                  <option value="Administrador">Administrador</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <select id="admin-user-dept" class="px-2 py-1.5 border border-slate-300 rounded-lg text-xs outline-none focus:ring-2 focus:ring-purple-500 bg-white col-span-2 font-bold">
                  <option value="ALL">Acesso Geral (TI + ADM)</option>
                  <option value="TI">Apenas Estoque TI</option>
                  <option value="ADM">Apenas Adm. Predial</option>
                </select>
              </div>
              <div class="flex gap-2">
                <button type="submit" id="btn-admin-save-user" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-1.5 text-xs font-bold transition-all shadow-sm">
                  Salvar Usuário
                </button>
                <button type="button" id="btn-admin-cancel-edit" onclick="resetAdminUserForm()" class="hidden bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg px-3 py-1.5 text-xs font-bold">
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>

        <div id="cfg-sec-myaccount" class="hidden space-y-3">
          <form onsubmit="handleSelfPasswordChange(event)" class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Nova Senha *</label>
              <input type="password" id="config-self-new-pass" required placeholder="Digite a nova senha" class="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none font-semibold">
            </div>
            <button type="submit" class="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-2 text-xs font-bold transition-all shadow">
              Atualizar Minha Senha
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL CADASTRO PRODUTO -->
  <div id="modal-product" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <h3 id="modal-product-title" class="font-bold text-base">Cadastrar Novo Produto</h3>
        <button onclick="closeProductModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <form id="form-product" onsubmit="handleProductSubmit(event)" class="p-6 space-y-4">
        <input type="hidden" id="prod-id">
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Nome do Produto *</label>
            <input type="text" id="prod-name" required placeholder="Ex: Notebook Dell Latitude" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none font-semibold">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Código / SKU *</label>
            <input type="text" id="prod-sku" required placeholder="Ex: NTB-DEL-15" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none uppercase font-bold">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Categoria *</label>
            <select id="prod-category" required class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none bg-white font-bold"></select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Qtd. Inicial *</label>
            <input type="number" id="prod-qty" min="0" required placeholder="0" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none font-bold">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Estoque Mínimo *</label>
            <input type="number" id="prod-min-qty" min="0" required placeholder="2" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none font-bold">
          </div>
          <div class="col-span-2 bg-purple-50 p-3.5 rounded-xl border border-purple-200">
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" id="prod-has-serial" class="w-4 h-4 text-purple-600 rounded accent-purple-600">
              <span class="text-xs font-bold text-purple-900">Exigir Controle por Número de Série (S/N)</span>
            </label>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
          <button type="button" onclick="closeProductModal()" class="px-3 py-1.5 border border-slate-300 rounded-xl text-xs font-bold">Cancelar</button>
          <button type="submit" class="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold shadow-sm">Salvar em Python</button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL MOVIMENTAÇÃO -->
  <div id="modal-movement" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
      <div id="movement-header" class="bg-emerald-600 text-white px-6 py-4 flex items-center justify-between">
        <h3 id="modal-movement-title" class="font-bold text-base">Registrar Movimentação</h3>
        <button onclick="closeMovementModal()" class="text-white/80 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <form id="form-movement" onsubmit="handleMovementSubmit(event)" class="p-6 space-y-4">
        <input type="hidden" id="move-type" value="IN">
        <div>
          <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Selecione o Produto *</label>
          <select id="move-prod-id" required class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none bg-white font-bold"></select>
        </div>
        <div>
          <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Tipo / Finalidade *</label>
          <select id="move-transaction-type" required class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 outline-none bg-white font-bold">
            <option value="Empréstimo (Uso Temporário)">Empréstimo (Uso Temporário)</option>
            <option value="Onboarding (Novo Colaborador)">Onboarding (Novo Colaborador)</option>
            <option value="Devolução de Equipamento">Devolução de Equipamento</option>
            <option value="Outros Motivos">Outros Motivos</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Beneficiário</label>
          <input type="text" id="move-recipient" placeholder="Ex: Carlos Eduardo - Vendas" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs font-semibold">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Quantidade *</label>
          <input type="number" id="move-qty" min="1" value="1" class="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs font-bold">
        </div>

        <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
          <button type="button" onclick="closeMovementModal()" class="px-3 py-1.5 border border-slate-300 rounded-xl text-xs font-bold">Cancelar</button>
          <button type="submit" id="btn-submit-movement" class="px-3.5 py-1.5 bg-emerald-600 text-white rounded-xl text-xs font-bold shadow-sm">Confirmar</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    let activeWorkspace = 'TI';
    let currentUser = { username: 'admin', role: 'Administrador', department: 'ALL' };
    let workspaceData = { categories: [], products: [], serials: [], movements: [] };

    let prodSortCol = 'name';
    let prodSortDir = 'asc';
    let isCompactMode = false;

    const COLUMN_DEFS = {
      name: { id: 'name', label: 'Produto', sortable: true, align: 'left' },
      sku: { id: 'sku', label: 'Código / SKU', sortable: true, align: 'left' },
      category: { id: 'category', label: 'Categoria', sortable: true, align: 'left' },
      quantity: { id: 'quantity', label: 'Quantidade', sortable: true, align: 'center' },
      serial: { id: 'serial', label: 'Controle S/N', sortable: false, align: 'center' },
      actions: { id: 'actions', label: 'Ações Rápidas', sortable: false, align: 'center' }
    };

    let prodColumnOrder = JSON.parse(localStorage.getItem('stock_prod_col_order_v2')) || ['name', 'sku', 'category', 'quantity', 'serial', 'actions'];
    let prodCols = JSON.parse(localStorage.getItem('stock_prod_cols_visibility_v2')) || { name: true, sku: true, category: true, quantity: true, serial: true, actions: true };

    function showToast(msg, type = 'success') {
      const container = document.getElementById('toast-container');
      const toast = document.createElement('div');
      toast.className = `p-3 rounded-xl shadow-xl text-xs font-bold text-white flex items-center gap-2 pointer-events-auto transition-all ${type === 'success' ? 'bg-emerald-600' : 'bg-rose-600'}`;
      toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i> <span>${msg}</span>`;
      container.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    }

    let confirmCallback = null;
    function showConfirm(title, msg, onConfirm) {
      document.getElementById('confirm-title').innerText = title;
      document.getElementById('confirm-message').innerText = msg;
      confirmCallback = onConfirm;
      document.getElementById('modal-confirm').classList.remove('hidden');
    }

    function closeConfirmModal(confirmed) {
      document.getElementById('modal-confirm').classList.add('hidden');
      if (confirmed && confirmCallback) confirmCallback();
      confirmCallback = null;
    }
    document.getElementById('btn-confirm-action').onclick = () => closeConfirmModal(true);

    async function loadWorkspaceData() {
      const res = await fetch(`/api/workspace/${activeWorkspace}`);
      workspaceData = await res.json();
      renderDashboard();
      renderProductsTable();
      renderSerialsTable();
      renderMovementsTable();
    }

    function switchWorkspace(ws) {
      activeWorkspace = ws;
      document.getElementById('btn-ws-ti').className = ws === 'TI' ? 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-purple-600 text-white shadow-sm' : 'px-2.5 py-1 rounded-lg text-[11px] font-bold text-purple-300 hover:text-white';
      document.getElementById('btn-ws-adm').className = ws === 'ADM' ? 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-purple-600 text-white shadow-sm' : 'px-2.5 py-1 rounded-lg text-[11px] font-bold text-purple-300 hover:text-white';
      document.getElementById('active-ws-badge').innerText = `Estoque Ativo: ${ws}`;
      loadWorkspaceData();
    }

    async function handleLoginSubmit(e) {
      e.preventDefault();
      const u = document.getElementById('loginUsername').value.trim();
      const p = document.getElementById('loginPassword').value.trim();

      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });

      const data = await res.json();
      if (data.success) {
        currentUser = data.user;
        document.getElementById('header-user-name').innerText = currentUser.username;
        document.getElementById('header-user-role').innerText = currentUser.role;
        document.getElementById('login-view').classList.add('hidden');
        document.getElementById('app-view').classList.remove('hidden');
        loadWorkspaceData();
      } else {
        showToast(data.message || 'Credenciais inválidas', 'error');
      }
    }

    function handleLogout() {
      document.getElementById('app-view').classList.add('hidden');
      document.getElementById('login-view').classList.remove('hidden');
    }

    let categoryChart = null;
    function renderDashboard() {
      const products = workspaceData.products || [];
      const serials = workspaceData.serials || [];

      document.getElementById('dash-total-products').innerText = products.length;
      document.getElementById('dash-total-units').innerText = `${products.reduce((acc, p) => acc + Number(p.quantity), 0)} un`;
      document.getElementById('dash-low-stock').innerText = products.filter(p => Number(p.quantity) <= Number(p.min_quantity)).length;
      document.getElementById('dash-serials-count').innerText = serials.length;

      const alertsList = document.getElementById('dash-alerts-list');
      alertsList.innerHTML = '';
      const lowStock = products.filter(p => Number(p.quantity) <= Number(p.min_quantity));
      if (lowStock.length === 0) {
        alertsList.innerHTML = `<div class="p-3 bg-emerald-50 text-emerald-700 font-bold text-xs rounded-xl">✨ Todos os itens estão com saldo normal no banco SQLite!</div>`;
      } else {
        lowStock.forEach(p => {
          alertsList.innerHTML += `
            <div class="p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs">
              <div>
                <p class="font-bold text-amber-900">${p.name}</p>
                <p class="text-[10px] text-amber-700">Mínimo: ${p.min_quantity} | Atual: <b>${p.quantity}</b></p>
              </div>
              <button onclick="openStockMovementModal('IN', ${p.id})" class="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white font-bold text-[10px] rounded-lg">Repor</button>
            </div>
          `;
        });
      }

      const ctx = document.getElementById('chart-categories');
      if (ctx && typeof Chart !== 'undefined') {
        const catTotals = {};
        (workspaceData.categories || []).forEach(c => catTotals[c] = 0);
        products.forEach(p => catTotals[p.category] = (catTotals[p.category] || 0) + Number(p.quantity));

        if (categoryChart) categoryChart.destroy();
        categoryChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: Object.keys(catTotals),
            datasets: [{ data: Object.values(catTotals), backgroundColor: ['#8b5cf6', '#38bdf8', '#34d399', '#fbbf24', '#f43f5e'] }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }
    }

    function toggleTableCustomizeMenu(menuId) {
      const menu = document.getElementById(menuId);
      menu.classList.toggle('hidden');
      if (!menu.classList.contains('hidden')) renderCustomizeMenu();
    }

    function renderCustomizeMenu() {
      const container = document.getElementById('customize-cols-list');
      container.innerHTML = '';
      prodColumnOrder.forEach((colKey, index) => {
        const colDef = COLUMN_DEFS[colKey];
        if (!colDef) return;
        const isChecked = prodCols[colKey] !== false;
        container.innerHTML += `
          <div class="flex items-center justify-between p-1.5 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <label class="flex items-center gap-2 cursor-pointer font-bold text-slate-800">
              <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleProdColumn('${colKey}', this.checked)" class="accent-purple-600">
              <span>${colDef.label}</span>
            </label>
            <div class="flex items-center gap-1">
              <button onclick="moveColumn(${index}, -1)" ${index === 0 ? 'disabled class="opacity-30"' : 'class="p-1 hover:text-purple-600"'}><i class="fa-solid fa-arrow-up text-[10px]"></i></button>
              <button onclick="moveColumn(${index}, 1)" ${index === prodColumnOrder.length - 1 ? 'disabled class="opacity-30"' : 'class="p-1 hover:text-purple-600"'}><i class="fa-solid fa-arrow-down text-[10px]"></i></button>
            </div>
          </div>
        `;
      });
    }

    function toggleProdColumn(colKey, isVisible) {
      prodCols[colKey] = isVisible;
      localStorage.setItem('stock_prod_cols_visibility_v2', JSON.stringify(prodCols));
      renderProductsTable();
    }

    function moveColumn(index, dir) {
      const newIdx = index + dir;
      if (newIdx < 0 || newIdx >= prodColumnOrder.length) return;
      const tmp = prodColumnOrder[index];
      prodColumnOrder[index] = prodColumnOrder[newIdx];
      prodColumnOrder[newIdx] = tmp;
      localStorage.setItem('stock_prod_col_order_v2', JSON.stringify(prodColumnOrder));
      renderCustomizeMenu();
      renderProductsTable();
    }

    function resetColumnPreferences() {
      prodColumnOrder = ['name', 'sku', 'category', 'quantity', 'serial', 'actions'];
      prodCols = { name: true, sku: true, category: true, quantity: true, serial: true, actions: true };
      localStorage.setItem('stock_prod_col_order_v2', JSON.stringify(prodColumnOrder));
      localStorage.setItem('stock_prod_cols_visibility_v2', JSON.stringify(prodCols));
      renderCustomizeMenu();
      renderProductsTable();
    }

    function toggleTableDensity() {
      isCompactMode = !isCompactMode;
      document.getElementById('density-icon').className = isCompactMode ? 'fa-solid fa-expand text-purple-600' : 'fa-solid fa-compress text-slate-400';
      renderProductsTable();
    }

    function renderProductsTable() {
      const headRow = document.getElementById('products-table-head-row');
      const tbody = document.getElementById('products-table-body');
      headRow.innerHTML = '';
      tbody.innerHTML = '';

      const search = document.getElementById('search-product').value.toLowerCase();
      const catFilter = document.getElementById('filter-category').value;
      const statusFilter = document.getElementById('filter-status').value;

      const catSelect = document.getElementById('filter-category');
      catSelect.innerHTML = '<option value="ALL">Todas as Categorias</option>';
      (workspaceData.categories || []).forEach(c => catSelect.innerHTML += `<option value="${c}">${c}</option>`);
      catSelect.value = catFilter;

      prodColumnOrder.forEach(colKey => {
        if (!prodCols[colKey]) return;
        const colDef = COLUMN_DEFS[colKey];
        const th = document.createElement('th');
        th.className = `py-3 px-4 ${colDef.align === 'center' ? 'text-center' : 'text-left'}`;
        th.innerText = colDef.label;
        headRow.appendChild(th);
      });

      let filtered = (workspaceData.products || []).filter(p => {
        const matchSearch = p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search);
        const matchCat = catFilter === 'ALL' || p.category === catCat;
        let matchStatus = true;
        if (statusFilter === 'LOW') matchStatus = Number(p.quantity) <= Number(p.min_quantity) && Number(p.quantity) > 0;
        if (statusFilter === 'OUT') matchStatus = Number(p.quantity) === 0;
        if (statusFilter === 'OK') matchStatus = Number(p.quantity) > Number(p.min_quantity);
        return matchSearch && matchCat && matchStatus;
      });

      const paddingClass = isCompactMode ? 'py-1.5 px-4' : 'py-3 px-4';
      filtered.forEach(p => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50 transition-colors";
        prodColumnOrder.forEach(colKey => {
          if (!prodCols[colKey]) return;
          const td = document.createElement('td');
          td.className = `${paddingClass} ${COLUMN_DEFS[colKey].align === 'center' ? 'text-center' : 'text-left'}`;

          if (colKey === 'name') td.innerHTML = `<span class="font-bold text-slate-900">${p.name}</span>`;
          if (colKey === 'sku') td.innerHTML = `<span class="font-mono font-bold text-purple-900">${p.sku}</span>`;
          if (colKey === 'category') td.innerHTML = `<span class="font-semibold text-slate-600">${p.category}</span>`;
          if (colKey === 'quantity') td.innerHTML = `<span class="font-black text-sm">${p.quantity} un</span>`;
          if (colKey === 'serial') td.innerHTML = p.has_serial ? `<span class="bg-purple-100 text-purple-700 font-bold text-[10px] px-2 py-0.5 rounded-md"><i class="fa-solid fa-barcode"></i> Sim (S/N)</span>` : `<span class="text-slate-400 text-[10px] font-bold">Flexível</span>`;
          if (colKey === 'actions') td.innerHTML = `
            <div class="flex items-center justify-center gap-1">
              <button onclick="openStockMovementModal('IN', ${p.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-0.5 rounded text-[10px] font-bold">+ Entrada</button>
              <button onclick="openStockMovementModal('OUT', ${p.id})" class="bg-rose-600 hover:bg-rose-500 text-white px-2 py-0.5 rounded text-[10px] font-bold">- Saída</button>
              <button onclick="deleteProduct(${p.id})" class="bg-rose-100 text-rose-700 hover:bg-rose-200 p-1 rounded text-[10px] font-bold"><i class="fa-solid fa-trash"></i></button>
            </div>
          `;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }

    function renderSerialsTable() {
      const tbody = document.getElementById('serials-table-body');
      tbody.innerHTML = '';
      const search = document.getElementById('search-serial').value.toLowerCase();
      const serials = (workspaceData.serials || []).filter(s => s.serial_number.toLowerCase().includes(search) || (s.recipient && s.recipient.toLowerCase().includes(search)));

      serials.forEach(s => {
        const prod = (workspaceData.products || []).find(p => p.id === s.product_id);
        tbody.innerHTML += `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="py-3 px-4 font-mono font-bold text-purple-900">${s.serial_number}</td>
            <td class="py-3 px-4 font-bold text-slate-800">${prod ? prod.name : 'Item'}</td>
            <td class="py-3 px-4"><span class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded-full font-bold">${s.status}</span></td>
            <td class="py-3 px-4 text-slate-600 font-bold">${s.recipient || '-'}</td>
            <td class="py-3 px-4 text-slate-500 font-bold">${s.operator || 'admin'}</td>
            <td class="py-3 px-4 text-slate-400 text-[11px] font-bold">${s.last_movement_date || '-'}</td>
          </tr>
        `;
      });
    }

    function renderMovementsTable() {
      const tbody = document.getElementById('movements-table-body');
      tbody.innerHTML = '';
      const typeFilter = document.getElementById('movement-type-filter').value;
      const search = document.getElementById('move-filter-search').value.toLowerCase();

      const movements = (workspaceData.movements || []).filter(m => {
        const matchType = typeFilter === 'ALL' || m.type === typeFilter;
        const matchSearch = m.product_name.toLowerCase().includes(search) || (m.recipient && m.recipient.toLowerCase().includes(search));
        return matchType && matchSearch;
      });

      movements.forEach(m => {
        const isIN = m.type === 'IN';
        tbody.innerHTML += `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="py-3 px-4 font-mono text-[11px] font-bold text-slate-600">${m.date_time}</td>
            <td class="py-3 px-4"><span class="${isIN ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'} text-[10px] px-2 py-0.5 rounded-full font-bold">${m.type}</span></td>
            <td class="py-3 px-4 font-bold text-slate-900">${m.product_name}</td>
            <td class="py-3 px-4 text-center font-black ${isIN ? 'text-emerald-600' : 'text-rose-600'}">${isIN ? '+' : '-'}${m.quantity}</td>
            <td class="py-3 px-4 font-bold text-slate-700">${m.recipient || '-'}</td>
            <td class="py-3 px-4 font-bold text-slate-600">${m.operator}</td>
            <td class="py-3 px-4 font-semibold text-slate-500">${m.purpose || '-'}</td>
          </tr>
        `;
      });
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
      document.querySelectorAll('.nav-tab').forEach(b => b.className = 'nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-300 hover:text-white hover:bg-purple-900/50');
      document.getElementById(`tab-${tabId}`).classList.remove('hidden');
      document.getElementById(`nav-${tabId}`).className = 'nav-tab px-2.5 py-1 rounded-lg text-[11px] font-bold bg-purple-600 text-white shadow-sm';
    }

    function openProductModal() {
      const catSelect = document.getElementById('prod-category');
      catSelect.innerHTML = '';
      (workspaceData.categories || []).forEach(c => catSelect.innerHTML += `<option value="${c}">${c}</option>`);
      document.getElementById('form-product').reset();
      document.getElementById('prod-id').value = '';
      document.getElementById('modal-product').classList.remove('hidden');
    }
    function closeProductModal() { document.getElementById('modal-product').classList.add('hidden'); }

    async function handleProductSubmit(e) {
      e.preventDefault();
      const payload = {
        id: document.getElementById('prod-id').value,
        sku: document.getElementById('prod-sku').value.trim(),
        name: document.getElementById('prod-name').value.trim(),
        category: document.getElementById('prod-category').value,
        quantity: document.getElementById('prod-qty').value,
        min_quantity: document.getElementById('prod-min-qty').value,
        has_serial: document.getElementById('prod-has-serial').checked,
        department: activeWorkspace,
        operator: currentUser.username
      };

      await fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      closeProductModal();
      showToast('Produto salvo no banco SQLite!');
      loadWorkspaceData();
    }

    function deleteProduct(id) {
      showConfirm('Excluir Produto', 'Deseja remover permanentemente este produto do banco SQLite?', async () => {
        await fetch(`/api/products/${id}`, { method: 'DELETE' });
        showToast('Produto excluído com sucesso!');
        loadWorkspaceData();
      });
    }

    function openStockMovementModal(type, prodId = null) {
      const select = document.getElementById('move-prod-id');
      select.innerHTML = '';
      (workspaceData.products || []).forEach(p => select.innerHTML += `<option value="${p.id}">${p.name} (${p.sku})</option>`);
      if (prodId) select.value = prodId;
      document.getElementById('move-type').value = type;
      document.getElementById('modal-movement').classList.remove('hidden');
    }
    function closeMovementModal() { document.getElementById('modal-movement').classList.add('hidden'); }

    async function handleMovementSubmit(e) {
      e.preventDefault();
      const payload = {
        product_id: document.getElementById('move-prod-id').value,
        type: document.getElementById('move-type').value,
        quantity: document.getElementById('move-qty').value,
        transaction_type: document.getElementById('move-transaction-type').value,
        recipient: document.getElementById('move-recipient').value.trim(),
        department: activeWorkspace,
        operator: currentUser.username
      };

      const res = await fetch('/api/movement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (data.success) {
        closeMovementModal();
        showToast('Movimentação registrada com sucesso!');
        loadWorkspaceData();
      } else {
        showToast(data.message || 'Erro ao movimentar', 'error');
      }
    }

    function openConfigModal() { document.getElementById('modal-config').classList.remove('hidden'); }
    function closeConfigModal() { document.getElementById('modal-config').classList.add('hidden'); }

    function switchConfigTab(tab) {
      ['database', 'users', 'myaccount'].forEach(t => {
        document.getElementById(`cfg-sec-${t}`).classList.add('hidden');
        document.getElementById(`cfg-tab-${t}`).className = 'pb-2 border-b-2 border-transparent text-slate-500 font-bold';
      });
      document.getElementById(`cfg-sec-${tab}`).classList.remove('hidden');
      document.getElementById(`cfg-tab-${tab}`).className = 'pb-2 border-b-2 border-purple-600 text-purple-600 font-bold';
      if (tab === 'users') loadAdminUsers();
    }

    let currentUsersList = [];

    async function loadAdminUsers() {
      try {
        const res = await fetch('/api/users');
        currentUsersList = await res.json();
        renderAdminUsersList();
      } catch (err) {
        showToast('Erro ao carregar usuários', 'error');
      }
    }

    function renderAdminUsersList() {
      const list = document.getElementById('admin-users-list');
      const badge = document.getElementById('user-count-badge');
      if (!list) return;

      if (badge) badge.innerText = currentUsersList.length;
      list.innerHTML = '';

      if (currentUsersList.length === 0) {
        list.innerHTML = '<p class="text-xs text-slate-400 font-bold text-center py-2">Nenhum usuário cadastrado.</p>';
        return;
      }

      currentUsersList.forEach(u => {
        list.innerHTML += `
          <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold text-slate-800">
            <div>
              <span class="font-extrabold text-purple-900">${u.username}</span>
              <span class="text-[9px] bg-purple-100 text-purple-700 border border-purple-200 px-1.5 py-0.2 rounded-full font-bold ml-1">${u.role}</span>
              <span class="text-[9px] text-slate-400 block font-bold">Acesso: ${u.department}</span>
            </div>
            <div class="flex gap-1">
              <button onclick='editAdminUser(${JSON.stringify(u)})' class="p-1.5 bg-slate-200 text-slate-700 hover:bg-slate-300 rounded-lg font-bold transition-colors" title="Editar">
                <i class="fa-solid fa-pen text-[10px]"></i>
              </button>
              <button onclick="deleteAdminUser(${u.id})" class="p-1.5 bg-rose-100 text-rose-700 hover:bg-rose-200 rounded-lg font-bold transition-colors" title="Excluir">
                <i class="fa-solid fa-trash text-[10px]"></i>
              </button>
            </div>
          </div>
        `;
      });
    }

    function editAdminUser(user) {
      document.getElementById('admin-edit-user-id').value = user.id;
      document.getElementById('admin-user-name').value = user.username;
      document.getElementById('admin-user-pass').value = user.password;
      document.getElementById('admin-user-role').value = user.role;
      document.getElementById('admin-user-dept').value = user.department;

      document.getElementById('admin-form-user-title').innerText = 'Editar Usuário';
      document.getElementById('btn-admin-cancel-edit').classList.remove('hidden');
    }

    function resetAdminUserForm() {
      document.getElementById('form-admin-user').reset();
      document.getElementById('admin-edit-user-id').value = '0';
      document.getElementById('admin-form-user-title').innerText = 'Cadastrar Novo Usuário';
      document.getElementById('btn-admin-cancel-edit').classList.add('hidden');
    }

    async function handleAdminSaveUser(e) {
      e.preventDefault();
      const payload = {
        id: document.getElementById('admin-edit-user-id').value,
        username: document.getElementById('admin-user-name').value.trim(),
        password: document.getElementById('admin-user-pass').value.trim(),
        role: document.getElementById('admin-user-role').value,
        department: document.getElementById('admin-user-dept').value
      };

      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (data.success) {
        showToast('Usuário salvo no banco SQLite!');
        resetAdminUserForm();
        loadAdminUsers();
      } else {
        showToast(data.message || 'Erro ao salvar usuário', 'error');
      }
    }

    function deleteAdminUser(userId) {
      showConfirm('Excluir Usuário', 'Deseja remover permanentemente este usuário do banco de dados?', async () => {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
          showToast('Usuário excluído!');
          loadAdminUsers();
        }
      });
    }

    function exportProductsCSV() { window.location.href = `/api/export/csv/${activeWorkspace}`; }
    function exportFullJSONBackup() { window.location.href = '/api/export/json'; }

    async function importProductsCSV(e) {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`/api/import/csv/${activeWorkspace}`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.success) {
        showToast(`${data.count} produtos importados para o SQLite!`);
        closeConfigModal();
        loadWorkspaceData();
      }
    }

    function resetFullDatabase() {
      showConfirm('Zerar Banco de Dados', `Deseja apagar permanentemente todos os dados do departamento ${activeWorkspace}?`, async () => {
        await fetch(`/api/reset/${activeWorkspace}`, { method: 'POST' });
        showToast('Banco de dados zerado com sucesso!');
        closeConfigModal();
        loadWorkspaceData();
      });
    }

    async function handleSelfPasswordChange(e) {
      e.preventDefault();
      const newPass = document.getElementById('config-self-new-pass').value.trim();
      if (!newPass) return;
      await fetch('/api/user/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: currentUser.username, new_password: newPass })
      });
      showToast('Sua senha foi alterada com sucesso!');
      closeConfigModal();
    }
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print(" 🚀 Servidor StockControl Pro em Python iniciado com sucesso!")
    print(" 📍 Acesse no seu navegador: http://127.0.0.1:5000")
    print("=" * 60)
    
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)