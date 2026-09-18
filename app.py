import json
import random
import re

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

from auth import conecta_supabase

st.set_page_config(page_title="Giga+ Fibra | Cadastro e Sorteio", page_icon="📶", layout="centered")

VERDE, AZUL, NOITE = "#1FE36B", "#0A2BD6", "#070B24"
SENHA_ADMIN = "gigaeventoftta"

# ---------- visual Giga+ ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Montserrat', sans-serif; }}
.stApp {{ background: radial-gradient(circle at 80% 0%, #0f2a8a33 0%, {NOITE} 55%); }}
#MainMenu, footer, header {{ visibility: hidden; }}
.hero {{ background: linear-gradient(120deg, {AZUL} 0%, #1245C8 45%, #11B76B 100%);
        border-radius: 18px; padding: 28px 28px 22px; margin-bottom: 16px; }}
.hero .logo {{ font-size: 34px; font-weight: 800; letter-spacing: -1px; color: #fff; }}
.hero .logo span {{ color: {VERDE}; }}
.hero h1 {{ font-size: 22px; font-weight: 800; color: #fff; margin: 10px 0 4px; }}
.hero p {{ color: #dfe7ff; font-size: 14px; margin: 0; }}
.card-title {{ background: #111842; border: 1px solid #22307a; border-left: 4px solid {VERDE};
              border-radius: 12px; padding: 12px 16px; margin: 18px 0 10px; }}
.card-title b {{ color: #fff; }} .card-title small {{ color: #9fb0e8; display:block; }}
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea {{
    background: #0d1437 !important; border-color: #22307a !important; border-radius: 10px !important; }}
.stButton > button {{ background: {VERDE}; color: {NOITE}; font-weight: 800; border: 0;
    border-radius: 999px; padding: 10px 30px; width: 100%; }}
.stButton > button:hover {{ background: #3cf583; color: {NOITE}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
.stTabs [data-baseweb="tab"] {{ background: #111842; border-radius: 999px; padding: 8px 20px; }}
.stTabs [aria-selected="true"] {{ background: {VERDE} !important; color: {NOITE} !important; font-weight: 800; }}
</style>
<div class="hero">
  <div class="logo">GIGA<span>+</span></div>
  <h1>Cadastre-se e concorra!</h1>
  <p>Síndicos, administradores, parceiros e leads dos condomínios.</p>
</div>
""", unsafe_allow_html=True)


def titulo(t, s=""):
    st.markdown(f'<div class="card-title"><b>{t}</b><small>{s}</small></div>', unsafe_allow_html=True)


# ---------- banco ----------
def conectar():
    return conecta_supabase()


def consulta(sql, params=None):
    with conectar() as conn:
        return pd.read_sql(sql, conn, params=params)


def executar(sql, params=None, retorno=False):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone() if retorno else None


@st.cache_data(ttl=600)
def carregar_condominios():
    df = consulta("""
        SELECT id, nome, bairro, cidade, sigla_estado AS uf
        FROM tb_condominio
        WHERE sigla_estado = 'CE'
          AND status ILIKE '11 - Liberado para venda'
        ORDER BY nome
    """).fillna("")
    df["label"] = df["nome"].str.strip() + " — " + df["bairro"] + ", " + df["cidade"] + "/" + df["uf"]
    return df


def buscar_cep(cep):
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5).json()
        return None if r.get("erro") else r
    except Exception:
        return None


def preencher_cep(n):
    """Ao digitar o CEP, joga o endereço do ViaCEP direto nos campos."""
    cep = re.sub(r"\D", "", st.session_state.get(f"cep_{n}", ""))
    via = buscar_cep(cep) if len(cep) == 8 else None
    if via:
        st.session_state[f"logr_{n}"] = via.get("logradouro", "")
        st.session_state[f"bairro_{n}"] = via.get("bairro", "")
        st.session_state[f"cidade_{n}"] = via.get("localidade", "")
        st.session_state[f"uf_{n}"] = via.get("uf", "")
    elif len(cep) == 8:
        st.toast("CEP não encontrado, preencha o endereço manualmente.")


def sortear():
    """Sorteia um prêmio ativo pelos pesos."""
    premios = consulta("SELECT nome, peso FROM tb_premio WHERE ativo ORDER BY id")
    if premios.empty:
        raise ValueError("Nenhum prêmio cadastrado. Cadastre na aba Prêmios.")
    nome = random.choices(premios["nome"].tolist(), weights=premios["peso"].tolist())[0]
    return nome, premios["nome"].tolist()


# ---------- jogos (HTML) ----------
def raspadinha(premio):
    p = json.dumps(premio)
    components.html(f"""
<div style="font-family:Montserrat,sans-serif;text-align:center;color:#fff">
  <p style="color:#9fb0e8;margin:0 0 10px">Passe o dedo para raspar 👇</p>
  <div id="box" style="position:relative;width:320px;height:180px;margin:auto;border-radius:18px;overflow:hidden;
       background:linear-gradient(120deg,#0A2BD6,#11B76B);box-shadow:0 0 30px #1FE36B55">
    <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
      <div style="font-size:13px;letter-spacing:2px;color:#dfe7ff">VOCÊ GANHOU</div>
      <div id="premio" style="font-size:26px;font-weight:800;padding:0 14px"></div>
    </div>
    <canvas id="c" width="320" height="180" style="position:absolute;inset:0;touch-action:none;cursor:pointer"></canvas>
  </div>
  <div id="msg" style="margin-top:14px;font-weight:800;color:#1FE36B;opacity:0;transition:.5s">🎉 Parabéns!</div>
</div>
<script>
document.getElementById('premio').textContent = {p};
const c=document.getElementById('c'),x=c.getContext('2d');
const g=x.createLinearGradient(0,0,320,180);g.addColorStop(0,'#aab4d6');g.addColorStop(1,'#6b7699');
x.fillStyle=g;x.fillRect(0,0,320,180);
x.fillStyle='#070B24';x.font='800 30px Montserrat';x.textAlign='center';x.fillText('GIGA+',160,85);
x.font='600 13px Montserrat';x.fillText('RASPE AQUI',160,112);
x.globalCompositeOperation='destination-out';
let down=false,done=false;
function pos(e){{const r=c.getBoundingClientRect(),t=e.touches?e.touches[0]:e;return[t.clientX-r.left,t.clientY-r.top]}}
function scratch(e){{if(!down||done)return;e.preventDefault();const[a,b]=pos(e);x.beginPath();x.arc(a,b,22,0,7);x.fill();check()}}
function check(){{const d=x.getImageData(0,0,320,180).data;let n=0;for(let i=3;i<d.length;i+=16)if(d[i]===0)n++;
  if(n/(d.length/16)>0.5){{done=true;c.style.transition='opacity .6s';c.style.opacity=0;document.getElementById('msg').style.opacity=1}}}}
['mousedown','touchstart'].forEach(v=>c.addEventListener(v,e=>{{down=true;scratch(e)}}));
['mouseup','touchend','mouseleave'].forEach(v=>c.addEventListener(v,()=>down=false));
['mousemove','touchmove'].forEach(v=>c.addEventListener(v,scratch,{{passive:false}}));
</script>""", height=280)


def velocimetro(premio):
    p = json.dumps(premio)
    components.html(f"""
<div style="font-family:Montserrat,sans-serif;text-align:center;color:#fff">
  <p style="color:#9fb0e8;margin:0 0 6px">Aperte <b>PARAR</b> para travar a velocidade!</p>
  <svg viewBox="0 0 300 175" width="320">
    <path d="M30 150 A120 120 0 0 1 90 46" stroke="#e53935" stroke-width="22" fill="none"/>
    <path d="M90 46 A120 120 0 0 1 210 46" stroke="#f5a623" stroke-width="22" fill="none"/>
    <path d="M210 46 A120 120 0 0 1 270 150" stroke="#1FE36B" stroke-width="22" fill="none"/>
    <g id="n" transform="rotate(-90 150 150)">
      <line x1="150" y1="150" x2="150" y2="45" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
    </g>
    <circle cx="150" cy="150" r="11" fill="#fff"/>
    <text id="mb" x="150" y="128" text-anchor="middle" fill="#fff" font-size="22" font-weight="800">0 Mb</text>
  </svg><br>
  <button id="b" style="background:#1FE36B;color:#070B24;border:0;border-radius:999px;padding:12px 44px;
     font:800 16px Montserrat;cursor:pointer;margin-top:6px">PARAR</button>
  <div id="res" style="margin-top:16px;opacity:0;transition:.6s">
    <div style="font-size:13px;letter-spacing:2px;color:#9fb0e8">VELOCIDADE MÁXIMA! VOCÊ GANHOU</div>
    <div id="premio" style="font-size:26px;font-weight:800;color:#1FE36B"></div>
  </div>
</div>
<script>
document.getElementById('premio').textContent = {p};
const n=document.getElementById('n'),mb=document.getElementById('mb');
let a=-90,dir=1,run=true;
function draw(v){{n.setAttribute('transform',`rotate(${{v}} 150 150)`);mb.textContent=Math.round((v+90)/180*1000)+' Mb'}}
(function loop(){{if(!run)return;a+=dir*4.5;if(a>=90||a<=-90)dir*=-1;draw(a);requestAnimationFrame(loop)}})();
document.getElementById('b').onclick=function(){{
  if(!run)return;run=false;this.disabled=true;this.style.opacity=.4;
  const alvo=62+Math.random()*24,ini=a,t0=performance.now();   // sempre termina no verde
  (function ease(t){{const k=Math.min((t-t0)/1200,1),e=1-Math.pow(1-k,3);draw(ini+(alvo-ini)*e);
    if(k<1)requestAnimationFrame(ease);else document.getElementById('res').style.opacity=1}})(t0);
}};
</script>""", height=330)


def roleta(premio, todos):
    p, t = json.dumps(premio), json.dumps(todos)
    components.html(f"""
<div style="font-family:Montserrat,sans-serif;text-align:center;color:#fff">
  <div style="position:relative;width:300px;height:300px;margin:auto">
    <div style="position:absolute;top:-6px;left:50%;transform:translateX(-50%);z-index:2;width:0;height:0;
         border-left:14px solid transparent;border-right:14px solid transparent;border-top:28px solid #fff"></div>
    <canvas id="w" width="300" height="300" style="transition:transform 5s cubic-bezier(.12,.8,.2,1)"></canvas>
  </div>
  <button id="b" style="background:#1FE36B;color:#070B24;border:0;border-radius:999px;padding:12px 44px;
     font:800 16px Montserrat;cursor:pointer;margin-top:14px">GIRAR</button>
  <div id="res" style="margin-top:14px;opacity:0;transition:.6s">
    <div style="font-size:13px;letter-spacing:2px;color:#9fb0e8">VOCÊ GANHOU</div>
    <div id="premio" style="font-size:26px;font-weight:800;color:#1FE36B"></div>
  </div>
</div>
<script>
const todos={t}, premio={p};
document.getElementById('premio').textContent=premio;
const w=document.getElementById('w'),x=w.getContext('2d'),n=todos.length,fat=2*Math.PI/n;
const cores=['#0A2BD6','#11B76B','#1245C8','#1FE36B','#0d1a6b','#0e8f55'];
todos.forEach((nome,i)=>{{
  x.beginPath();x.moveTo(150,150);x.arc(150,150,146,-Math.PI/2+i*fat,-Math.PI/2+(i+1)*fat);
  x.fillStyle=cores[i%cores.length];x.fill();x.strokeStyle='#070B24';x.lineWidth=3;x.stroke();
  x.save();x.translate(150,150);x.rotate(-Math.PI/2+(i+.5)*fat);x.textAlign='right';x.fillStyle='#fff';
  x.font='700 13px Montserrat';x.fillText(nome.length>18?nome.slice(0,17)+'…':nome,136,5);x.restore();
}});
x.beginPath();x.arc(150,150,22,0,7);x.fillStyle='#070B24';x.fill();
x.fillStyle='#1FE36B';x.font='800 12px Montserrat';x.textAlign='center';x.fillText('GIGA+',150,154);
document.getElementById('b').onclick=function(){{
  this.disabled=true;this.style.opacity=.4;
  const idx=todos.indexOf(premio), meio=(idx+.5)*360/n, folga=(Math.random()-.5)*(360/n)*.6;
  w.style.transform=`rotate(${{360*6-meio+folga}}deg)`;
  setTimeout(()=>document.getElementById('res').style.opacity=1,5100);
}};
</script>""", height=440)


def caixa_surpresa(premio, todos):
    p, t = json.dumps(premio), json.dumps(todos)
    components.html(f"""
<div style="font-family:Montserrat,sans-serif;text-align:center;color:#fff">
  <p style="color:#9fb0e8;margin:0 0 14px">Escolha uma caixa 👇</p>
  <div id="cx" style="display:flex;gap:14px;justify-content:center"></div>
  <div id="res" style="margin-top:18px;opacity:0;transition:.6s">
    <div style="font-size:13px;letter-spacing:2px;color:#9fb0e8">VOCÊ GANHOU</div>
    <div id="premio" style="font-size:26px;font-weight:800;color:#1FE36B"></div>
  </div>
</div>
<style>
.box{{width:96px;height:110px;border-radius:14px;cursor:pointer;position:relative;
  background:linear-gradient(160deg,#0A2BD6,#11B76B);box-shadow:0 6px 18px #0008;transition:transform .3s,opacity .5s;
  display:flex;align-items:center;justify-content:center;font-size:44px}}
.box:hover{{transform:translateY(-6px) scale(1.04)}}
.box.aberta{{animation:abre .6s forwards}} .box.outra{{opacity:.35;cursor:default}}
.box small{{position:absolute;bottom:-38px;left:0;right:0;font-size:11px;color:#9fb0e8;opacity:0;transition:.5s}}
.box.outra small{{opacity:1}}
@keyframes abre{{0%{{transform:rotate(0)}}25%{{transform:rotate(-8deg)}}50%{{transform:rotate(8deg)}}100%{{transform:scale(1.12)}}}}
</style>
<script>
const premio={p}, todos={t};
document.getElementById('premio').textContent=premio;
const outros=todos.filter(x=>x!==premio); const cx=document.getElementById('cx'); let feito=false;
for(let i=0;i<3;i++){{
  const b=document.createElement('div');b.className='box';b.innerHTML='🎁<small></small>';cx.appendChild(b);
  b.onclick=()=>{{ if(feito)return; feito=true; let k=0;
    b.classList.add('aberta'); setTimeout(()=>{{b.firstChild.textContent='🎉';document.getElementById('res').style.opacity=1}},600);
    [...cx.children].forEach(o=>{{ if(o===b)return; o.classList.add('outra');
      o.querySelector('small').textContent=outros.length?outros[(k++)%outros.length]:premio; }});
  }};
}}
</script>""", height=300)


def caca_niquel(premio):
    p = json.dumps(premio)
    components.html(f"""
<div style="font-family:Montserrat,sans-serif;text-align:center;color:#fff">
  <div style="display:inline-flex;gap:10px;padding:16px;border-radius:20px;
       background:linear-gradient(120deg,#0A2BD6,#11B76B);box-shadow:0 0 30px #1FE36B55">
    <div class="r"><div class="f" id="r0"></div></div>
    <div class="r"><div class="f" id="r1"></div></div>
    <div class="r"><div class="f" id="r2"></div></div>
  </div><br>
  <button id="b" style="background:#1FE36B;color:#070B24;border:0;border-radius:999px;padding:12px 44px;
     font:800 16px Montserrat;cursor:pointer;margin-top:16px">PUXAR 🎰</button>
  <div id="res" style="margin-top:16px;opacity:0;transition:.6s">
    <div style="font-size:13px;letter-spacing:2px;color:#9fb0e8">JACKPOT! VOCÊ GANHOU</div>
    <div id="premio" style="font-size:26px;font-weight:800;color:#1FE36B"></div>
  </div>
</div>
<style>
.r{{width:78px;height:90px;overflow:hidden;background:#070B24;border-radius:12px}}
.f{{display:flex;flex-direction:column}} .f div{{height:90px;display:flex;align-items:center;justify-content:center;font-size:44px}}
</style>
<script>
document.getElementById('premio').textContent={p};
const sim=['📶','🚀','⚡','📡','💚','🏢'], alvo='📶', N=24;
for(let i=0;i<3;i++){{ const f=document.getElementById('r'+i);
  let h=''; for(let k=0;k<N;k++) h+='<div>'+sim[Math.floor(Math.random()*sim.length)]+'</div>';
  f.innerHTML=h+'<div>'+alvo+'</div>'; }}
document.getElementById('b').onclick=function(){{
  this.disabled=true;this.style.opacity=.4;
  for(let i=0;i<3;i++){{ const f=document.getElementById('r'+i);
    f.style.transition=`transform ${{1.6+i*0.7}}s cubic-bezier(.15,.85,.25,1)`;
    f.style.transform=`translateY(-${{N*90}}px)`; }}
  setTimeout(()=>document.getElementById('res').style.opacity=1,3200);
}};
</script>""", height=330)


# ---------- abas ----------
aba_premios, aba_forms, aba_jogar = st.tabs(["🎁 Prêmios", "📝 Cadastro", "🎮 Jogar"])

# ===== PRÊMIOS =====
with aba_premios:
    if st.text_input("Senha da equipe", type="password", key="senha") != SENHA_ADMIN:
        st.info("Área restrita à equipe Giga+.")
    else:
        titulo("Novo prêmio", "Peso = chance relativa (peso 3 sai 3x mais que peso 1).")
        c1, c2 = st.columns([4, 1])
        p_nome = c1.text_input("Nome do prêmio", key="p_nome")
        p_peso = c2.number_input("Peso", min_value=1, value=1, step=1, key="p_peso")
        if st.button("Adicionar prêmio"):
            if not p_nome.strip():
                st.error("Informe o nome do prêmio.")
            else:
                executar("INSERT INTO tb_premio (nome, peso) VALUES (%s, %s)", (p_nome.strip(), int(p_peso)))
                st.success("Prêmio adicionado!")
                st.rerun()

        titulo("Prêmios ativos")
        premios = consulta("SELECT id, nome, peso FROM tb_premio WHERE ativo ORDER BY id")
        if premios.empty:
            st.caption("Nenhum prêmio cadastrado ainda.")
        else:
            total = premios["peso"].sum()
            for _, r in premios.iterrows():
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{r.nome}**  \n<small style='color:#9fb0e8'>peso {r.peso} · chance {r.peso / total:.0%}</small>",
                            unsafe_allow_html=True)
                if c2.button("🗑️", key=f"del_{r.id}", help="Excluir prêmio"):
                    executar("DELETE FROM tb_premio WHERE id = %s", (int(r.id),))
                    st.rerun()

# ===== CADASTRO =====
with aba_forms:
    condos = carregar_condominios()
    n = st.session_state.setdefault("form_n", 0)   # muda a cada cadastro -> campos zerados
    if st.session_state.pop("salvo", None):
        st.success(f"Cadastro de {st.session_state.contato['nome']} salvo! ✅ Pode jogar na aba 🎮 Jogar ou cadastrar o próximo.")
    NAO_ENCONTREI = "➕ Não encontrei o condomínio na lista"

    titulo("Quem é o contato", "Dados de quem vamos falar")
    nome = st.text_input("Nome do contato", key=f"nome_{n}")
    tipo = st.selectbox("Tipo", ["Síndico", "Administrador", "Parceiro", "Lead", "Outro"],
                        index=None, placeholder="Selecione", key=f"tipo_{n}")
    whats = st.text_input("WhatsApp com DDD", placeholder="(85) 99999-9999", key=f"whats_{n}")

    titulo("Condomínio", "Digite para buscar pelo nome, bairro ou cidade")
    escolha = st.selectbox("Condomínio", [NAO_ENCONTREI] + condos["label"].tolist(),
                           index=None, placeholder="Buscar condomínio...", key=f"cond_{n}")

    novo = {}
    if escolha == NAO_ENCONTREI:
        st.caption("Informe o endereço completo do condomínio.")
        c1, c2 = st.columns([1, 2])
        c1.text_input("CEP (opcional)", key=f"cep_{n}", placeholder="Preenche o endereço",
                      on_change=preencher_cep, args=(n,))
        novo["condominio_nome"] = c2.text_input("Nome do condomínio", key=f"cnome_{n}")
        c3, c4 = st.columns([3, 1])
        novo["logradouro"] = c3.text_input("Logradouro", key=f"logr_{n}")
        novo["numero"] = c4.text_input("Número", key=f"num_{n}")
        c5, c6 = st.columns(2)
        novo["complemento"] = c5.text_input("Complemento", key=f"compl_{n}")
        novo["bairro"] = c6.text_input("Bairro", key=f"bairro_{n}")
        c7, c8 = st.columns([3, 1])
        novo["cidade"] = c7.text_input("Cidade", key=f"cidade_{n}")
        novo["uf"] = c8.text_input("UF", max_chars=2, key=f"uf_{n}").upper()
        cep = re.sub(r"\D", "", st.session_state.get(f"cep_{n}", ""))
        novo["cep"] = cep

    st.write("")
    if st.button("Salvar e jogar 🎁"):
        fone = re.sub(r"\D", "", whats)
        erros = []
        if not nome.strip(): erros.append("Informe o nome.")
        if not tipo: erros.append("Selecione o tipo.")
        if len(fone) not in (10, 11): erros.append("WhatsApp inválido (DDD + número).")
        if not escolha: erros.append("Selecione o condomínio.")
        if escolha == NAO_ENCONTREI:
            rotulos = {"condominio_nome": "nome do condomínio", "logradouro": "logradouro", "numero": "número",
                       "bairro": "bairro", "cidade": "cidade", "uf": "UF"}
            faltando = [r for k, r in rotulos.items() if not novo[k].strip()]
            if faltando:
                erros.append("Falta preencher: " + ", ".join(faltando) + ".")
        if erros:
            for e in erros: st.error(e)
        else:
            id_cond = None if escolha == NAO_ENCONTREI else condos.loc[condos["label"] == escolha, "id"].iloc[0]
            campos = {k: (v.strip() or None) for k, v in novo.items()} if id_cond is None else {}
            cols = ["nome", "tipo", "whatsapp", "id_condominio"] + list(campos)
            vals = [nome.strip(), tipo, fone, id_cond] + list(campos.values())
            try:
                novo_id = executar(
                    f"INSERT INTO tb_contato_evento ({', '.join(cols)}) "
                    f"VALUES ({', '.join(['%s'] * len(vals))}) RETURNING id", vals, retorno=True)[0]
                st.session_state.contato = {"id": novo_id, "nome": nome.strip()}
                st.session_state.pop("resultado", None)
                st.session_state.form_n += 1
                st.session_state.salvo = True
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# ===== JOGAR =====
JOGOS = {"Raspadinha": "🎟️", "Teste de velocidade": "🚀", "Roleta": "🎡",
         "Caixa surpresa": "🎁", "Caça-níquel": "🎰"}

with aba_jogar:
    contato = st.session_state.get("contato")
    primeiro = f", {contato['nome'].split()[0]}" if contato else ""
    if "resultado" in st.session_state:
        jogo, premio, todos = st.session_state.resultado
        titulo(f"Boa sorte{primeiro}!", jogo)
        if jogo == "Raspadinha":
            raspadinha(premio)
        elif jogo == "Teste de velocidade":
            velocimetro(premio)
        elif jogo == "Roleta":
            roleta(premio, todos)
        elif jogo == "Caixa surpresa":
            caixa_surpresa(premio, todos)
        else:
            caca_niquel(premio)
        if st.button("Jogar de novo"):
            st.session_state.pop("contato", None); st.session_state.pop("resultado")
            st.rerun()
    else:
        titulo(f"Olá{primeiro}! Escolha seu jogo", "Boa sorte!")
        cols = st.columns(3) + st.columns(3)
        for col, (jogo, icone) in zip(cols, JOGOS.items()):
            if col.button(f"{icone} {jogo}", key=f"jogo_{jogo}"):
                try:
                    premio, todos = sortear()
                    st.session_state.resultado = (jogo, premio, todos)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
