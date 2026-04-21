import os, psycopg2, time, json, http.cookies, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB = {
    "host": os.getenv("DB_HOST", "db"),
    "user": os.getenv("DB_USER", "emdr_user"),
    "password": os.getenv("DB_PASS", "senha123"),
    "dbname": os.getenv("DB_NAME", "emdr_db")
}
def get_conn(): return psycopg2.connect(**DB)

def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id SERIAL PRIMARY KEY, nome_completo VARCHAR(150), data_nascimento DATE, cpf VARCHAR(14),
            genero VARCHAR(20), telefone VARCHAR(20), email VARCHAR(100), endereco TEXT, 
            cidade VARCHAR(100), estado VARCHAR(2),
            queixa_principal TEXT, medicacoes TEXT, alergias TEXT, historico_substancias TEXT,
            tcle_assinado BOOLEAN DEFAULT FALSE, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessoes (
            id SERIAL PRIMARY KEY, paciente_id INT REFERENCES pacientes(id),
            profissional_registro VARCHAR(50), profissional_nome VARCHAR(150),
            fase_atual INT DEFAULT 2, protocolo VARCHAR(20), imagem TEXT, nc TEXT, pc TEXT, 
            emocao TEXT, local_corporal TEXT, suds INT, voc INT, insights TEXT,
            concluida BOOLEAN DEFAULT FALSE, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS medidas (
            id SERIAL PRIMARY KEY, sessao_id INT REFERENCES sessoes(id),
            fase VARCHAR(20), suds INT, voc INT, notas TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    try:
        cur.execute("ALTER TABLE sessoes ADD COLUMN IF NOT EXISTS profissional_registro VARCHAR(50);")
        cur.execute("ALTER TABLE sessoes ADD COLUMN IF NOT EXISTS profissional_nome VARCHAR(150);")
    except: pass
    conn.commit(); cur.close(); conn.close()
    print("✅ Estrutura alinhada ao Protocolo EMDR Padrão 8 Fases (Shapiro).")

class Handler(BaseHTTPRequestHandler):
    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def get_professional(self):
        raw_cookie = self.headers.get("Cookie", "")
        if not raw_cookie: return None
        cookie = http.cookies.SimpleCookie(raw_cookie)
        nome_c = cookie.get("prof_nome")
        reg_c = cookie.get("prof_registro")
        if nome_c and reg_c:
            return {"nome": urllib.parse.unquote(nome_c.value), "registro": urllib.parse.unquote(reg_c.value)}
        return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        p = lambda k: params.get(k, [""])[0]

        prof = self.get_professional()
        if path not in ["/login", "/autenticar", "/favicon.ico"] and not prof:
            return self.send_redirect("/login")

        css = """<style>
            body{font-family:sans-serif;max-width:1100px;margin:30px auto;padding:20px;background:#f1f5f9;color:#0f172a}
            h1,h2,h3{color:#1e293b}
            table{width:100%;border-collapse:collapse;background:white;margin:15px 0}
            th,td{padding:10px;border-bottom:1px solid #e2e8f0;text-align:center}
            input,select,textarea{padding:10px;border:1px solid #cbd5e1;border-radius:6px;width:100%;margin:6px 0}
            textarea{height:60px;resize:vertical}
            .btn{padding:10px 16px;color:white;text-decoration:none;border-radius:6px;display:inline-block;font-size:14px;border:none;cursor:pointer;margin:4px;font-weight:500}
            .btn-g{background:#10b981}.btn-b{background:#3b82f6}.btn-r{background:#ef4444}.btn-y{background:#f59e0b;color:#000}.btn-p{background:#8b5cf6}
            .card{background:white;padding:20px;border-radius:10px;border:1px solid #e2e8f0;margin:15px 0}
            .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}
            .tracker{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap}
            .f{padding:6px 10px;background:#e2e8f0;border-radius:20px;font-size:12px;font-weight:600}
            .f.active{background:#3b82f6;color:white}.f.done{background:#10b981;color:white}
            .script{background:#e0f2fe;border-left:4px solid #0284c7;padding:12px;margin:15px 0;border-radius:4px}
            input::placeholder, textarea::placeholder{color:#94a3b8}
            .search-box{display:flex;gap:10px;margin:15px 0;flex-wrap:wrap}
            .search-box input{flex:1;min-width:200px}
            .chart-container{background:white;padding:15px;border-radius:10px;margin:15px 0;border:1px solid #e2e8f0}
            .login-box{max-width:450px;margin:60px auto;background:white;padding:30px;border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 4px 6px rgba(0,0,0,0.05)}
            .alert{padding:10px;border-radius:6px;margin:10px 0;font-size:13px}
            .alert-w{background:#fef3c7;color:#92400e}.alert-d{background:#fef2f2;color:#991b1b}.alert-s{background:#f0fdf4;color:#166534}
            @media print {
                body{background:white;padding:0;margin:0;max-width:100%}
                .no-print{display:none!important}
                .card,.chart-container{border:none;box-shadow:none}
                table{font-size:11px}
                h1{font-size:18px}
            }
        </style>"""

        # 🔐 TELA DE LOGIN COM CABEÇALHO NEURO CRAVE
        if path == "/login":
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Login - NEURO CRAVE</title>{css}</head><body>"
            html += "<div class='login-box'>"
            html += "<h1 style='text-align:center;font-size:20px;margin-bottom:4px;color:#1e293b'>🧠 Programa de Apoio a Reabilitação</h1>"
            html += "<h2 style='text-align:center;font-size:18px;margin-bottom:16px;color:#2563eb;font-weight:700'>NEURO CRAVE</h2>"
            html += "<form action='/autenticar' method='get'>"
            html += "<label>Nome Completo *</label><input name='nome' placeholder='Ex: Dr(a). Maria Silva' required>"
            html += "<label>Nº Conselho (CRM/CRP/COREN/etc) *</label><input name='registro' placeholder='Ex: CRM/SP 123456' required>"
            html += "<button type='submit' class='btn btn-g' style='width:100%;margin-top:15px'>🚪 Entrar</button></form>"
            html += "</div></body></html>"
            return self.send_html(html)

        elif path == "/autenticar":
            nome, reg = p('nome').strip(), p('registro').strip()
            if nome and reg:
                self.send_response(302); self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"prof_nome={urllib.parse.quote(nome, safe='')}; Path=/; Max-Age=86400; SameSite=Lax")
                self.send_header("Set-Cookie", f"prof_registro={urllib.parse.quote(reg, safe='')}; Path=/; Max-Age=86400; SameSite=Lax")
                self.end_headers(); return
            return self.send_html("<p>❌ Preencha todos os campos. <a href='/login'>Voltar</a></p>")

        if path == "/":
            search = p('q').strip()
            conn = get_conn(); cur = conn.cursor()
            if search:
                cur.execute("SELECT id, nome_completo, telefone, cidade, estado, cpf FROM pacientes WHERE nome_completo ILIKE %s OR telefone ILIKE %s OR cidade ILIKE %s OR cpf ILIKE %s ORDER BY id DESC;", (f'%{search}%',)*4)
            else:
                cur.execute("SELECT id, nome_completo, telefone, cidade, estado, cpf FROM pacientes ORDER BY id DESC;")
            pacientes = cur.fetchall(); cur.close(); conn.close()
            rows = ""
            for pt in pacientes:
                loc = f"{pt[3] or ''}/{pt[4] or ''}".strip("/")
                rows += f"<tr><td>{pt[0]}</td><td>{pt[1]}</td><td>{pt[2] or '-'}</td><td>{loc or '-'}</td><td>"
                rows += f"<a href='/editar?id={pt[0]}' class='btn btn-y'>✏️ Editar</a> "
                rows += f"<a href='/ficha?id={pt[0]}' class='btn btn-b'>📄 Ficha</a> "
                rows += f"<a href='/sessao?id={pt[0]}' class='btn btn-g'>📝 Sessão</a> "
                rows += f"<a href='/historico?id={pt[0]}' class='btn btn-b'>📜 Histórico</a> "
                rows += f"<a href='/parecer?id={pt[0]}' class='btn btn-p'>📋 Parecer</a> "
                rows += f"<a href='/delete?id={pt[0]}' class='btn btn-r' onclick='return confirm(\"⚠️ Deletar paciente e TODAS as sessões?\");'>🗑️ Excluir</a></td></tr>"
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>EMDR TUS</title>{css}"
            html += "<script>function filtrar(){const q=document.getElementById('busca').value.trim();window.location.href='/?q='+encodeURIComponent(q);}</script></head><body>"
            html += f"<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:15px'>"
            # ✅ ALTERAÇÃO SOLICITADA: TÍTULO SEPARADO EM DUAS LINHAS
            html += f"<div style='flex:1;'><h1 style='margin:0'>🧠 Prontuário Clínico</h1><h2 style='margin:5px 0 0;font-size:16px;color:#475569'>Programa de Apoio a Reabilitação (NEURO CRAVE)</h2></div>"
            html += f"<div style='text-align:right;min-width:200px'><div style='font-size:14px;color:#475569;margin-bottom:8px'><b>Profissional:</b> {prof['nome']}<br><b>Registro:</b> {prof['registro']}</div>"
            html += f"<a href='/logout' class='btn btn-r' style='padding:12px 24px;font-size:15px;border-radius:8px'>🚪 Sair do Sistema</a></div></div><br>"
            html += "<a href='/cadastro' class='btn btn-g'>➕ Novo Cadastro</a>"
            html += f"<div class='search-box no-print'><input type='text' id='busca' placeholder='Buscar por nome, telefone, cidade ou CPF...' value='{search}' onkeypress='if(event.key===\"Enter\")filtrar()'><button onclick='filtrar()' class='btn btn-b'>🔍 Buscar</button><a href='/' class='btn btn-y'>🔄 Limpar</a></div>"
            html += f"<h2>📋 Pacientes {f'({len(pacientes)} encontrado(s))' if search else ''}</h2><table><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Cidade/UF</th><th>Ações</th></tr>{rows}</table></body></html>"
            self.send_html(html)

        elif path in ["/cadastro", "/editar"]:
            is_edit = path == "/editar"; pid = p('id') if is_edit else None
            pt = [None]*16
            if is_edit:
                conn = get_conn(); cur = conn.cursor(); cur.execute("SELECT * FROM pacientes WHERE id=%s;", (pid,)); res = cur.fetchone(); cur.close(); conn.close()
                if res: pt = list(res)
            title = "Editar Ficha Clínica" if is_edit else "Nova Ficha de Admissão"
            estados = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
            opts_est = "".join([f"<option value='{uf}' {'selected' if uf==str(pt[9]) else ''}>{uf}</option>" for uf in estados])
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body><h1>📝 {title}</h1><form action='/salvar_cadastro' method='get'>"
            if is_edit: html += f"<input type='hidden' name='id' value='{pid}'>"
            html += "<div class='card'><h3>👤 Dados</h3><div class='grid'>"
            html += f"<div><label>Nome Completo *</label><input name='nome_completo' value='{pt[1] or ''}' required></div>"
            html += f"<div><label>Data Nascimento</label><input type='date' name='data_nascimento' value='{str(pt[2])[:10] if pt[2] else ''}'></div>"
            html += f"<div><label>CPF</label><input name='cpf' value='{pt[3] or ''}'></div>"
            html += f"<div><label>Gênero</label><select name='genero'><option>Selecione</option><option {'selected' if pt[4]=='Masculino' else ''}>Masculino</option><option {'selected' if pt[4]=='Feminino' else ''}>Feminino</option></select></div>"
            html += f"<div><label>Telefone *</label><input name='telefone' value='{pt[5] or ''}' required></div>"
            html += f"<div><label>Email</label><input name='email' value='{pt[6] or ''}'></div>"
            html += f"<div style='grid-column:span 2'><label>Endereço</label><input name='endereco' value='{pt[7] or ''}'></div>"
            html += f"<div><label>Cidade</label><input name='cidade' value='{pt[8] or ''}'></div>"
            html += f"<div><label>Estado</label><select name='estado'>{opts_est}</select></div></div></div>"
            html += "<div class='card'><h3>🏥 Anamnese</h3>"
            html += f"<label>Queixa Principal</label><textarea name='queixa_principal'>{pt[10] or ''}</textarea>"
            html += f"<label>Medicações</label><textarea name='medicacoes'>{pt[11] or ''}</textarea>"
            html += f"<label>Alergias</label><input name='alergias' value='{pt[12] or ''}'>"
            html += f"<label>Hist. Substâncias</label><textarea name='historico_substancias'>{pt[13] or ''}</textarea></div>"
            html += f"<div class='card'><label><input type='checkbox' name='tcle' value='true' style='width:auto' {'checked' if pt[14] else ''}> TCLE Aceito.</label></div>"
            html += "<button type='submit' class='btn btn-g' style='width:100%;margin-top:10px'>💾 Salvar Ficha</button></form><br><a href='/' class='btn btn-r'>← Voltar</a></body></html>"
            self.send_html(html)

        elif path == "/salvar_cadastro":
            pid = p('id'); tcle = True if p('tcle')=='true' else False
            conn = get_conn(); cur = conn.cursor()
            data = (p('nome_completo'), p('data_nascimento') or None, p('cpf'), p('genero'), p('telefone'), p('email'), p('endereco'), p('cidade'), p('estado'), p('queixa_principal'), p('medicacoes'), p('alergias'), p('historico_substancias'), tcle)
            if pid:
                cur.execute("""UPDATE pacientes SET nome_completo=%s,data_nascimento=%s,cpf=%s,genero=%s,telefone=%s,email=%s,endereco=%s,cidade=%s,estado=%s,queixa_principal=%s,medicacoes=%s,alergias=%s,historico_substancias=%s,tcle_assinado=%s WHERE id=%s;""", data + (pid,))
            else:
                cur.execute("""INSERT INTO pacientes (nome_completo,data_nascimento,cpf,genero,telefone,email,endereco,cidade,estado,queixa_principal,medicacoes,alergias,historico_substancias,tcle_assinado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);""", data)
            conn.commit(); cur.close(); conn.close()
            self.send_html("<meta http-equiv='refresh' content='0;url=/'>")

        elif path == "/ficha":
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT * FROM pacientes WHERE id=%s;", (p('id'),)); pt = cur.fetchone(); cur.close(); conn.close()
            if not pt: return self.send_html("<p>❌ Paciente não encontrado.</p>")
            labels = ["ID","Nome","Nasc.","CPF","Gênero","Tel","Email","Endereço","Cidade","UF","Queixa","Medic.","Alergias","Hist. Subs.","TCLE","Cadastro"]
            rows = "".join([f"<tr><td style='text-align:left;font-weight:bold;background:#f8fafc'>{labels[i]}</td><td style='text-align:left'>{pt[i] or '-'}</td></tr>" for i in range(len(labels))])
            self.send_html(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Ficha</title>{css}</head><body><h1>📄 {pt[1]}</h1><table>{rows}</table><a href='/editar?id={pt[0]}' class='btn btn-y'>✏️ Editar</a> <a href='/sessao?id={pt[0]}' class='btn btn-g'>📝 Sessão</a> <a href='/historico?id={pt[0]}' class='btn btn-b'>📜 Histórico</a> <a href='/' class='btn btn-r'>← Voltar</a></body></html>")

        elif path == "/sessao":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT nome_completo FROM pacientes WHERE id=%s;", (pid,)); nome = cur.fetchone()[0]
            cur.execute("SELECT id, fase_atual, concluida FROM sessoes WHERE paciente_id=%s ORDER BY criado_em DESC LIMIT 1;", (pid,)); sessao = cur.fetchone()
            cur.execute("SELECT count(*) FROM sessoes WHERE paciente_id=%s AND concluida=TRUE;", (pid,)); concluidas = cur.fetchone()[0]
            cur.close(); conn.close()
            
            if concluidas > 0:
                return self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase8?id={pid}'>")
            if sessao and not sessao[2]:
                return self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase{sessao[1]}?id={pid}&sessao={sessao[0]}'>")
            
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 2</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f active'>2. Preparação</span><span class='f'>3. Avaliação</span><span class='f'>4. Dessens.</span><span class='f'>5. Instalação</span><span class='f'>6. Body Scan</span><span class='f'>7. Fechamento</span></div>"
            html += f"<h2>🛡️ Fase 2: Preparação ({nome})</h2>"
            html += "<div class='script'>💬 'Vou explicar como o EMDR funciona. Você terá controle total e pode parar a qualquer momento com um sinal combinado.'</div>"
            html += "<form action='/criar_sessao'><input type='hidden' name='id' value='"+pid+"'>"
            html += "<label>Recursos instalados?</label><select name='recursos'><option value='sim'>✅ Sim</option><option value='parcial'>⚠️ Parcialmente</option></select>"
            html += "<label>Sinal de parada combinado?</label><select name='parada'><option value='sim'>✅ Sim</option><option value='nao'>❌ Não</option></select>"
            html += "<button type='submit' class='btn btn-b' style='margin-top:15px;width:100%'>✅ Preparado → Fase 3</button></form>"
            html += "<br><a href='/' class='btn btn-r'>← Cancelar</a></div></body></html>"
            self.send_html(html)

        elif path == "/criar_sessao":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO sessoes (paciente_id, profissional_registro, profissional_nome, fase_atual) VALUES (%s, %s, %s, 3) RETURNING id;", (pid, prof['registro'], prof['nome']))
            sid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase3?id={pid}&sessao={sid}'>")

        elif path == "/fase3":
            pid, sid = p('id'), p('sessao')
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 3</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f done'>2</span><span class='f active'>3. Avaliação</span><span class='f'>4</span><span class='f'>5</span><span class='f'>6</span><span class='f'>7</span></div>"
            html += "<h2>🎯 Fase 3: Avaliação do Alvo</h2>"
            html += "<div class='script'>💬 Imagem, NC, PC, Emoção, Local Corporal, SUDS (0-10), VOC (1-7)</div>"
            html += "<form action='/salvar_fase3'><input type='hidden' name='id' value='"+pid+"'><input type='hidden' name='sessao' value='"+sid+"'><div class='grid'>"
            html += "<div><label>Protocolo</label><select name='protocolo'><option>CravEx</option><option>DeTUR</option><option>FSAP</option></select></div>"
            html += "<div><label>Imagem Alvo</label><input name='imagem'></div>"
            html += "<div><label>Cognição Negativa (NC)</label><input name='nc'></div>"
            html += "<div><label>Cognição Positiva (PC)</label><input name='pc'></div>"
            html += "<div><label>Emoção</label><input name='emocao'></div>"
            html += "<div><label>Local Corporal</label><input name='local'></div>"
            html += "<div><label>SUDS (0-10)</label><input type='number' name='suds' min='0' max='10' required></div>"
            html += "<div><label>VOC (1-7)</label><input type='number' name='voc' min='1' max='7' required></div></div>"
            html += "<button type='submit' class='btn btn-b' style='margin-top:15px;width:100%'>▶ Confirmar → Fase 4</button></form><br><a href='/' class='btn btn-r'>← Voltar</a></div></body></html>"
            self.send_html(html)

        elif path == "/salvar_fase3":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("UPDATE sessoes SET fase_atual=4, protocolo=%s, imagem=%s, nc=%s, pc=%s, emocao=%s, local_corporal=%s, suds=%s, voc=%s WHERE id=%s;", (p('protocolo'), p('imagem'), p('nc'), p('pc'), p('emocao'), p('local'), p('suds'), p('voc'), sid))
            cur.execute("INSERT INTO medidas (sessao_id, fase, suds, voc, notas) VALUES (%s,'Fase 3',%s,%s,'Avaliação inicial');", (sid, p('suds'), p('voc')))
            conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase4?id={pid}&sessao={sid}'>")

        elif path == "/fase4":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT protocolo, suds, voc FROM sessoes WHERE id=%s;", (sid,)); row = cur.fetchone(); cur.close(); conn.close()
            proto, suds, voc = row or ("CravEx", 5, 3)
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 4</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f done'>2-3</span><span class='f active'>4. Dessensibilização</span><span class='f'>5</span><span class='f'>6</span><span class='f'>7</span></div>"
            html += f"<h2>🔄 Fase 4: Dessensibilização (SUDS: {suds}/10)</h2>"
            html += f"<div class='script'>💬 Aplique BLS até SUDS ≤ 1 ou platô ecológico. Registre após cada série.</div>"
            aviso = "⚠️ SUDS > 1. Continue BLS." if suds > 1 else "✅ SUDS ≤ 1. Pronto para Fase 5."
            html += f"<div class='alert alert-w'>{aviso}</div>"
            html += "<div id='timer' style='background:#1e293b;color:white;padding:20px;border-radius:8px;text-align:center;font-size:32px;font-weight:bold;margin:15px 0'>30</div>"
            html += "<button onclick='let t=30;const iv=setInterval(()=>{document.getElementById(\"timer\").textContent=--t;if(t<=0)clearInterval(iv)},1000)' class='btn btn-y' style='width:100%;margin-bottom:15px'>▶ BLS (30s)</button>"
            html += "<form action='/salvar_fase4'><input type='hidden' name='id' value='"+pid+"'><input type='hidden' name='sessao' value='"+sid+"'>"
            html += "<div class='grid'><div><label>SUDS Pós-BLS</label><input type='number' name='suds' min='0' max='10' required></div><div><label>VOC Pós-BLS</label><input type='number' name='voc' min='1' max='7' required></div></div>"
            html += "<label>Insights</label><input name='notas'>"
            html += "<button type='submit' class='btn btn-b' style='margin-top:10px;width:100%'>➕ Registrar Série</button></form>"
            html += f"<br><a href='/fase3?id={pid}&sessao={sid}' class='btn btn-r'>← Voltar</a> <a href='/fase5?id={pid}&sessao={sid}' class='btn btn-g'>✅ Avançar → Fase 5</a></div></body></html>"
            self.send_html(html)

        elif path == "/salvar_fase4":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("UPDATE sessoes SET suds=%s, voc=%s WHERE id=%s;", (p('suds'), p('voc'), sid))
            cur.execute("INSERT INTO medidas (sessao_id, fase, suds, voc, notas) VALUES (%s,'Fase 4',%s,%s,%s);", (sid, p('suds'), p('voc'), p('notas')))
            conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase4?id={pid}&sessao={sid}'>")

        elif path == "/fase5":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT pc, voc FROM sessoes WHERE id=%s;", (sid,)); row = cur.fetchone(); cur.close(); conn.close()
            pc, voc = row or ("Consigo lidar", 4)
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 5</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f done'>2-4</span><span class='f active'>5. Instalação</span><span class='f'>6</span><span class='f'>7</span></div>"
            html += f"<h2>🔗 Fase 5: Instalação da PC (VOC: {voc}/7)</h2>"
            html += f"<div class='script'>💬 Fortaleça a PC com BLS até VOC = 6 ou 7.</div>"
            html += "<form action='/salvar_fase5'><input type='hidden' name='id' value='"+pid+"'><input type='hidden' name='sessao' value='"+sid+"'>"
            html += "<label>VOC Atual (1-7)</label><input type='number' name='voc' min='1' max='7' value='"+str(voc)+"' required>"
            html += "<label>Validação/Insight</label><input name='notas'>"
            html += "<button type='submit' class='btn btn-b' style='margin-top:10px;width:100%'>➕ Registrar VOC</button></form>"
            
            if voc >= 6:
                html += f"<br><a href='/fase6?id={pid}&sessao={sid}' class='btn btn-g' style='margin-top:10px;width:100%'>✅ VOC ≥6 → Avançar para Fase 6 (Body Scan)</a>"
            else:
                html += f"<div class='alert alert-d'>⚠️ VOC {voc} < 6. Shapiro exige VOC ≥ 6 antes do Body Scan. Continue BLS ou reavalie a PC.</div>"
                html += f"<button onclick=\"if(confirm('⚠️ Decisão Clínica: Avançar mesmo com VOC < 6?'))window.location.href='/fase6?id={pid}&sessao={sid}'\" class='btn btn-y' style='margin-top:10px;width:100%'>⚠️ Decisão Clínica → Fase 6</button>"
            html += f"<br><a href='/fase4?id={pid}&sessao={sid}' class='btn btn-r' style='margin-top:10px;width:100%;display:block;text-align:center'>← Voltar para Fase 4</a></div></body></html>"
            self.send_html(html)

        elif path == "/salvar_fase5":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("UPDATE sessoes SET voc=%s WHERE id=%s;", (p('voc'), sid))
            cur.execute("INSERT INTO medidas (sessao_id, fase, voc, notas) VALUES (%s,'Fase 5',%s,%s);", (sid, p('voc'), p('notas')))
            conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase5?id={pid}&sessao={sid}'>")

        elif path == "/fase6":
            pid, sid = p('id'), p('sessao')
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 6</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f done'>2-5</span><span class='f active'>6. Body Scan</span><span class='f'>7</span></div>"
            html += "<h2>🧘 Fase 6: Varredura Corporal</h2>"
            html += "<div class='script'>💬 Percorra o corpo mentalmente. Registre tensão residual (0-10). Aplique BLS se houver.</div>"
            html += "<form action='/salvar_fase6'><input type='hidden' name='id' value='"+pid+"'><input type='hidden' name='sessao' value='"+sid+"'>"
            html += "<div class='grid'><div><label>Tensão Residual (0-10)</label><input type='number' name='suds' min='0' max='10' required></div><div><label>Local</label><input name='notas'></div></div>"
            html += "<button type='submit' class='btn btn-b' style='margin-top:10px;width:100%'>➕ Registrar</button></form>"
            html += f"<br><a href='/fase5?id={pid}&sessao={sid}' class='btn btn-r' style='margin-top:10px;width:100%;display:block;text-align:center'>← Voltar</a>"
            html += f"<button onclick=\"if(confirm('Concluir Body Scan e ir para Fechamento?'))window.location.href='/fase7?id={pid}&sessao={sid}'\" class='btn btn-g' style='margin-top:10px;width:100%;display:block;text-align:center'>✅ Concluir → Fase 7</button></div></body></html>"
            self.send_html(html)

        elif path == "/salvar_fase6":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO medidas (sessao_id, fase, suds, notas) VALUES (%s,'Fase 6',%s,%s);", (sid, p('suds'), p('notas')))
            conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/fase6?id={pid}&sessao={sid}'>")

        elif path == "/fase7":
            pid, sid = p('id'), p('sessao')
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 7</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f done'>2-6</span><span class='f active'>7. Fechamento</span></div>"
            html += "<h2>🔒 Fase 7: Fechamento & Psicoeducação</h2>"
            html += "<div class='script'>💬 Estabilize, oriente sobre processamento contínuo, registre insights. Não deixe alvo aberto.</div>"
            html += "<form action='/concluir_sessao'><input type='hidden' name='id' value='"+pid+"'><input type='hidden' name='sessao' value='"+sid+"'>"
            html += "<label>Estado Final</label><select name='estado'><option>Estável/Regulado</option><option>Levemente Ativado</option><option>Necessita Contenção</option></select>"
            html += "<label>Orientações</label><textarea name='notas'></textarea>"
            html += "<button type='submit' class='btn btn-g' style='margin-top:10px;width:100%'>💾 Concluir Sessão</button></form>"
            html += f"<br><a href='/fase6?id={pid}&sessao={sid}' class='btn btn-r' style='margin-top:10px;width:100%;display:block;text-align:center'>← Voltar</a></div></body></html>"
            self.send_html(html)

        elif path == "/concluir_sessao":
            pid, sid = p('id'), p('sessao')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO medidas (sessao_id, fase, notas) VALUES (%s,'Fase 7',%s);", (sid, p('notas')))
            cur.execute("UPDATE sessoes SET concluida=TRUE WHERE id=%s;", (sid,))
            conn.commit(); cur.close(); conn.close()
            self.send_html(f"<meta http-equiv='refresh' content='0;url=/historico?id={pid}'>")

        elif path == "/fase8":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT nome_completo FROM pacientes WHERE id=%s;", (pid,)); nome = cur.fetchone()[0]
            cur.execute("SELECT id, imagem, nc, pc, emocao, suds, voc, concluida FROM sessoes WHERE paciente_id=%s AND concluida=TRUE ORDER BY criado_em DESC;", (pid,))
            sessoes = cur.fetchall(); cur.close(); conn.close()
            
            rows = ""
            for s in sessoes:
                rows += f"<tr><td>{s[1] or '-'}</td><td>{s[2] or '-'}</td><td>{s[3] or '-'}</td><td>{s[4] or '-'}</td><td>{s[5]}</td><td>{s[6]}</td></tr>"
            
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fase 8</title>{css}</head><body><div class='card'>"
            html += "<div class='tracker'><span class='f active'>8. Reavaliação</span></div>"
            html += f"<h2>🔍 Fase 8: Reavaliação ({nome})</h2>"
            html += "<div class='alert alert-s'>✅ Segundo Shapiro, toda nova sessão inicia com reavaliação dos alvos anteriores.</div>"
            html += f"<h3>📋 Alvos Processados</h3><table><tr><th>Imagem</th><th>NC</th><th>PC</th><th>Emoção</th><th>SUDS Final</th><th>VOC Final</th></tr>{rows}</table>"
            html += "<form action='/sessao'><input type='hidden' name='id' value='"+pid+"'>"
            html += "<label>Alvo anterior completamente resolvido?</label><select name='resolvido'><option value='sim'>✅ Sim</option><option value='parcial'>⚠️ Parcialmente (continuar)</option><option value='novo'>🆕 Novo alvo</option></select>"
            html += "<button type='submit' class='btn btn-g' style='margin-top:15px;width:100%'>▶ Prosseguir para Sessão Atual</button></form>"
            html += "<br><a href='/' class='btn btn-r'>← Voltar</a></div></body></html>"
            self.send_html(html)

        elif path == "/historico":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT nome_completo FROM pacientes WHERE id=%s;", (pid,)); nome = cur.fetchone()[0]
            cur.execute("SELECT id, fase_atual, protocolo, imagem, nc, pc, emocao, suds, voc, concluida, criado_em FROM sessoes WHERE paciente_id=%s ORDER BY criado_em DESC;", (pid,))
            sessoes = cur.fetchall()
            cur.execute("""SELECT m.criado_em::date, m.suds, m.voc FROM medidas m JOIN sessoes s ON m.sessao_id = s.id WHERE s.paciente_id = %s AND (m.suds IS NOT NULL OR m.voc IS NOT NULL) ORDER BY m.criado_em;""", (pid,))
            medidas = cur.fetchall(); cur.close(); conn.close()
            
            datas, suds_vals, voc_vals = [], [], []
            for m in medidas:
                datas.append(str(m[0]))
                suds_vals.append(m[1] if m[1] is not None else None)
                voc_vals.append(m[2] if m[2] is not None else None)
            chart_data = json.dumps({"labels": datas, "suds": suds_vals, "voc": voc_vals})
            
            rows = "".join([f"<tr><td>{str(s[10])[:10]}</td><td>{s[2] or '-'}</td><td>{s[3] or '-'}</td><td>{s[4] or '-'}</td><td>{s[5] or '-'}</td><td>{s[6] or '-'}</td><td>{s[7] or '-'}</td><td>{s[8] or '-'}</td><td>{'✅' if s[9] else '⏸'}</td></tr>" for s in sessoes])
            
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Evolução</title>{css}"
            html += "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script><script>const chartData = "+chart_data+";"
            html += "window.onload=function(){if(chartData.labels.length){new Chart(document.getElementById('sudsChart'),{type:'line',data:{labels:chartData.labels,datasets:[{label:'SUDS',data:chartData.suds,borderColor:'#ef4444',tension:0.3}]},options:{responsive:true,scales:{y:{beginAtZero:true,max:10}}}});new Chart(document.getElementById('vocChart'),{type:'line',data:{labels:chartData.labels,datasets:[{label:'VOC',data:chartData.voc,borderColor:'#10b981',tension:0.3}]},options:{responsive:true,scales:{y:{beginAtZero:true,max:7}}}});}}</script></head><body>"
            html += f"<h1>📈 Evolução: {nome}</h1>"
            html += f"<div class='no-print'><a href='/' class='btn btn-b'>← Início</a> <a href='/sessao?id={pid}' class='btn btn-g'>📝 Nova Sessão</a> <a href='/parecer?id={pid}' class='btn btn-p'>📋 Gerar Parecer</a></div>"
            if datas:
                html += "<div class='grid'><div class='chart-container'><canvas id='sudsChart'></canvas></div><div class='chart-container'><canvas id='vocChart'></canvas></div></div>"
            html += f"<h2>📋 Histórico</h2><table><tr><th>Data</th><th>Proto.</th><th>Imagem</th><th>NC</th><th>PC</th><th>Emoção</th><th>SUDS</th><th>VOC</th><th>Status</th></tr>{rows}</table></body></html>"
            self.send_html(html)

        elif path == "/parecer":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT * FROM pacientes WHERE id=%s;", (pid,)); pt = cur.fetchone()
            if not pt: return self.send_html("<p>❌ Paciente não encontrado.</p>")
            
            cur.execute("""SELECT s.profissional_registro, s.profissional_nome, s.protocolo, s.imagem, s.nc, s.pc, s.emocao, s.suds, s.voc, s.concluida, s.criado_em::date
                           FROM sessoes s WHERE s.paciente_id=%s ORDER BY s.criado_em;""", (pid,))
            sessoes = cur.fetchall(); cur.close(); conn.close()
            
            if not sessoes:
                return self.send_html("<p>📊 Sem sessões registradas para gerar parecer.</p>")
            
            prof_reg, prof_nome = sessoes[0][0] or prof['registro'], sessoes[0][1] or prof['nome']
            suds_ini, suds_fin = sessoes[0][7], sessoes[-1][7]
            voc_ini, voc_fin = sessoes[0][8], sessoes[-1][8]
            total_sessoes = len(sessoes)
            concluidas = sum(1 for s in sessoes if s[9])
            alvos = list(set(s[3] for s in sessoes if s[3]))
            
            resolvido = suds_fin <= 1 and voc_fin >= 6 if suds_fin is not None and voc_fin is not None else False
            recomendacao = "Alvo(s) resolvido(s). Manter acompanhamento preventivo." if resolvido else "Alvo(s) parcialmente processado(s). Recomenda-se continuar protocolo EMDR nas próximas sessões."
            if concluidas < total_sessoes: recomendacao += " Há sessão em andamento. Verificar fechamento seguro."
            
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Parecer Clínico</title>{css}</head><body>"
            html += f"<h1>📋 Parecer Clínico EMDR - {pt[1]}</h1>"
            html += f"<div style='display:flex;justify-content:space-between;margin-bottom:20px'><div><b>Profissional:</b> {prof_nome} ({prof_reg})<br><b>Data:</b> {time.strftime('%d/%m/%Y')}</div><div><b>Sessões:</b> {total_sessoes} ({concluidas} concluídas)<br><b>Alvos:</b> {', '.join(alvos) if alvos else 'N/I'}</div></div>"
            html += f"<table><tr><th>Métrica</th><th>Inicial</th><th>Final</th><th>Variação</th></tr>"
            html += f"<tr><td>SUDS</td><td>{suds_ini or '-'}</td><td>{suds_fin or '-'}</td><td>{(suds_fin or 0) - (suds_ini or 0) if suds_fin and suds_ini else '-'}</td></tr>"
            html += f"<tr><td>VOC</td><td>{voc_ini or '-'}</td><td>{voc_fin or '-'}</td><td>{(voc_fin or 0) - (voc_ini or 0) if voc_fin and voc_ini else '-'}</td></tr></table>"
            html += f"<div class='alert alert-s'><b>Conclusão Clínica (Padrão Shapiro):</b><br>{recomendacao}<br><em>Resolução do alvo: {'✅ Sim' if resolvido else '⏳ Em processamento'}</em></div>"
            html += "<div class='no-print' style='margin-top:20px'><a href='/historico?id="+pid+"' class='btn btn-b'>← Histórico</a> <button onclick='window.print()' class='btn btn-p'>🖨️ Imprimir Parecer</button></div>"
            html += "</body></html>"
            self.send_html(html)

        elif path == "/exportar_pdf":
            pid = p('id')
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT * FROM pacientes WHERE id=%s;", (pid,)); pt = cur.fetchone()
            if not pt: return self.send_html("<p>❌ Paciente não encontrado.</p>")
            cur.execute("""SELECT s.criado_em::date, s.fase_atual, s.protocolo, s.imagem, s.nc, s.pc, s.emocao, s.suds, s.voc, s.concluida, s.profissional_registro, s.profissional_nome FROM sessoes s WHERE s.paciente_id=%s ORDER BY s.criado_em DESC;""", (pid,))
            sessoes = cur.fetchall(); cur.close(); conn.close()
            
            rows = ""
            for s in sessoes:
                status = "✅" if s[9] else "⏸"
                rows += f"<tr><td>{s[0]}</td><td>{s[2] or '-'}</td><td>{s[3] or '-'}</td><td>{s[4] or '-'}/{s[5] or '-'}</td><td>{s[6] or '-'}</td><td>{s[7] or '-'}/{s[8] or '-'}</td><td>{status}</td></tr>"
            
            prof_reg = prof['registro'] if prof else (sessoes[0][10] if sessoes else "N/I")
            prof_nome = prof['nome'] if prof else (sessoes[0][11] if sessoes else "N/I")
            
            css_print = """<style>body{font-family:Arial;font-size:11px;color:#000;background:white;padding:20px}h1{font-size:16px;border-bottom:2px solid #000;padding-bottom:5px}table{width:100%;border-collapse:collapse;font-size:10px}th,td{border:1px solid #000;padding:4px;text-align:left}th{background:#f0f0f0}.header{display:flex;justify-content:space-between;margin-bottom:20px}.footer{margin-top:30px;font-size:9px;color:#666;border-top:1px solid #ccc;padding-top:10px}@media print{.no-print{display:none}}</style>"""
            
            html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Relatório</title>{css_print}<script>window.onload=()=>setTimeout(()=>window.print(),300)</script></head><body>"
            html += f"<div class='header'><h1>📄 Relatório Clínico</h1><div><b>Paciente:</b> {pt[1]}<br><b>Profissional:</b> {prof_nome} ({prof_reg})<br><b>Data:</b> {time.strftime('%d/%m/%Y')}</div></div>"
            html += f"<table><tr><th>Data</th><th>Proto.</th><th>Alvo</th><th>NC/PC</th><th>Emoção</th><th>SUDS/VOC</th><th>Status</th></tr>{rows}</table>"
            html += f"<div class='footer'>Sistema NEURO CRAVE • Protocolo EMDR Padrão 8 Fases • {prof_nome} ({prof_reg})</div>"
            html += "<div class='no-print' style='margin-top:20px;text-align:center'><a href='/historico?id="+pid+"' style='padding:10px;background:#3b82f6;color:white;text-decoration:none;border-radius:6px'>← Voltar</a></div></body></html>"
            self.send_html(html)

        elif path == "/delete":
            conn = get_conn(); cur = conn.cursor()
            cur.execute("DELETE FROM medidas WHERE sessao_id IN (SELECT id FROM sessoes WHERE paciente_id=%s);", (p('id'),))
            cur.execute("DELETE FROM sessoes WHERE paciente_id=%s;", (p('id'),))
            cur.execute("DELETE FROM pacientes WHERE id=%s;", (p('id'),)); conn.commit(); cur.close(); conn.close()
            self.send_html("<meta http-equiv='refresh' content='0;url=/'>")

        elif path == "/logout":
            self.send_response(302); self.send_header("Location", "/login")
            self.send_header("Set-Cookie", "prof_nome=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax")
            self.send_header("Set-Cookie", "prof_registro=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax")
            self.end_headers()

if __name__ == "__main__":
    print("⏳ Conectando ao banco...")
    for t in range(10):
        try: conn = psycopg2.connect(**DB); conn.close(); break
        except: print(f"⏳ Tentativa {t+1}/10..."); time.sleep(3)
    init_db()
    print("🌐 Sistema EMDR NEURO CRAVE pronto! Acesse http://localhost")
    HTTPServer(("0.0.0.0", 80), Handler).serve_forever()