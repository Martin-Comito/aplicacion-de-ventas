import streamlit as st
import pandas as pd
from supabase import create_client
import google.generativeai as genai
from datetime import datetime, time, date
import pytz
import time as time_module
import extra_streamlit_components as stx

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="DevStudio Manager", page_icon="💼", layout="wide")

# ==============================================================================
# 🔐 ZONA DE CONEXIONES (AQUÍ ESTÁ EL ARREGLO)
# ==============================================================================

# 1. CONEXIÓN SUPABASE
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error: Falló la conexión a Supabase.")
    st.stop()

# 2. CONEXIÓN GOOGLE IA (CON LIMPIEZA AUTOMÁTICA)
api_key_final = None
try:
    # Leemos la clave de los secretos
    raw_key = st.secrets["google"]["api_key"]
    
    # .strip() ELIMINA ESPACIOS O SALTOS DE LÍNEA INVISIBLES
    api_key_final = raw_key.strip() 
    
    genai.configure(api_key=api_key_final)
except:
    pass 

# 3. GESTOR DE COOKIES
cookie_manager = stx.CookieManager()

# ==============================================================================
# 🧠 LÓGICA DE USUARIOS
# ==============================================================================

def login_check(user, password):
    try:
        res = supabase.table("agencia_usuarios").select("*").eq("username", user).eq("password", password).execute()
        if res.data: return res.data[0]
        return None
    except: return None

def get_user_from_cookie():
    time_module.sleep(0.1)
    cookie_user = cookie_manager.get('agencia_user')
    if cookie_user:
        res = supabase.table("agencia_usuarios").select("*").eq("username", cookie_user).execute()
        if res.data: return res.data[0]
    return None

if 'usuario' not in st.session_state: st.session_state.usuario = None

if st.session_state.usuario is None:
    user_cookie = get_user_from_cookie()
    if user_cookie: st.session_state.usuario = user_cookie

# --- PANTALLA DE LOGIN ---
if st.session_state.usuario is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write(""); st.write("")
        st.markdown("<h1 style='text-align: center;'>🚀 DevStudio</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR", type="primary", use_container_width=True):
                user_data = login_check(user_input, pass_input)
                if user_data:
                    st.session_state.usuario = user_data
                    cookie_manager.set('agencia_user', user_data['username'], expires_at=datetime.now() + pd.Timedelta(days=7))
                    st.toast(f"Hola {user_data['nombre_completo']}")
                    time_module.sleep(1); st.rerun()
                else: st.error("Datos incorrectos")
    st.stop()

# ==============================================================================
# 🖥️ APLICACIÓN PRINCIPAL
# ==============================================================================
USER = st.session_state.usuario
ID_USER = USER['id']
ROL = USER['rol']

with st.sidebar:
    st.title("💼 DevStudio")
    st.write(f"👤 **{USER['nombre_completo']}**")
    st.caption(f"Rol: {ROL}")
    st.divider()
    menu = st.radio("Menú", ["📇 Mis Clientes", "📅 Agenda", "🧠 Crear Proyecto (IA)", "📂 Estado de Proyectos"])
    st.divider()
    if api_key_final: st.success("🤖 IA Activa")
    else: st.warning("⚠️ IA Inactiva")
    st.divider()
    if st.button("Cerrar Sesión"):
        cookie_manager.delete('agencia_user')
        st.session_state.usuario = None; st.rerun()

# 1. CLIENTES
if menu == "📇 Mis Clientes":
    st.header("📇 Gestión de Clientes")
    with st.expander("➕ Agregar Nuevo Cliente"):
        with st.form("new_cli"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre *")
            empresa = c2.text_input("Empresa *")
            rubro = c1.selectbox("Rubro", ["Comercio", "Logística", "Servicios", "Agro", "Otro"])
            tel = c2.text_input("Teléfono")
            dire = c1.text_input("Dirección")
            email = c2.text_input("Email")
            notas = st.text_area("Notas")
            if st.form_submit_button("Guardar"):
                if nombre and empresa:
                    try:
                        supabase.table("agencia_clientes").insert({
                            "usuario_id": ID_USER, "nombre": nombre, "empresa": empresa, "rubro": rubro,
                            "telefono": tel, "direccion": dire, "email": email, "notas_personales": notas
                        }).execute()
                        st.success("Guardado"); time_module.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                else: st.error("Faltan datos")

    if ROL == 'DIRECTOR':
        res = supabase.table("agencia_clientes").select("*, agencia_usuarios(nombre_completo)").order("created_at", desc=True).execute()
    else:
        res = supabase.table("agencia_clientes").select("*").eq("usuario_id", ID_USER).order("created_at", desc=True).execute()

    if res.data:
        for c in res.data:
            with st.container(border=True):
                col_a, col_b = st.columns([4,1])
                tit = f"**{c['nombre']}** ({c['empresa']})"
                if ROL == 'DIRECTOR' and 'agencia_usuarios' in c: tit += f" | 👤 {c['agencia_usuarios']['nombre_completo']}"
                col_a.markdown(tit)
                col_a.caption(f"{c['rubro']} | {c['telefono']}")
                if col_b.button("🗑️", key=f"d_{c['id']}"):
                    supabase.table("agencia_clientes").delete().eq("id", c['id']).execute(); st.rerun()
    else: st.info("Sin clientes.")

# 2. AGENDA
elif menu == "📅 Agenda":
    st.header("📅 Agenda")
    if ROL == 'DIRECTOR': cli = supabase.table("agencia_clientes").select("id, nombre, empresa").execute()
    else: cli = supabase.table("agencia_clientes").select("id, nombre, empresa").eq("usuario_id", ID_USER).execute()
    mapa = {f"{c['nombre']} ({c['empresa']})": c['id'] for c in cli.data} if cli.data else {}

    with st.form("new_cita"):
        c1, c2, c3 = st.columns(3)
        if mapa:
            sel = c1.selectbox("Cliente", list(mapa.keys()))
            fec = c2.date_input("Fecha", min_value=date.today())
            hor = c3.time_input("Hora", value=time(9,0))
            mot = st.text_input("Motivo")
            if st.form_submit_button("Agendar"):
                dt = datetime.combine(fec, hor).isoformat()
                supabase.table("agencia_citas").insert({"usuario_id": ID_USER, "cliente_id": mapa[sel], "fecha_hora": dt, "motivo": mot}).execute()
                st.success("Listo"); st.rerun()
        else: st.warning("Carga clientes primero")

    st.divider()
    if ROL == 'DIRECTOR': citas = supabase.table("agencia_citas").select("*, agencia_clientes(nombre), agencia_usuarios(nombre_completo)").order("fecha_hora").execute()
    else: citas = supabase.table("agencia_citas").select("*, agencia_clientes(nombre)").eq("usuario_id", ID_USER).order("fecha_hora").execute()
    
    if citas.data:
        for ci in citas.data:
            try: dtf = datetime.fromisoformat(ci['fecha_hora']).strftime('%d/%m %H:%M')
            except: dtf = ci['fecha_hora']
            usr = f" | {ci['agencia_usuarios']['nombre_completo']}" if ROL=='DIRECTOR' and 'agencia_usuarios' in ci else ""
            st.info(f"🕒 {dtf} | {ci['agencia_clientes']['nombre']}{usr} - {ci['motivo']}")

# 3. IA (USANDO MODELO ESTÁNDAR PARA EVITAR ERROR 404)
elif menu == "🧠 Crear Proyecto (IA)":
    st.header("✨ Consultor IA")
    if ROL == 'DIRECTOR': cli = supabase.table("agencia_clientes").select("id, nombre, empresa, rubro").execute()
    else: cli = supabase.table("agencia_clientes").select("id, nombre, empresa, rubro").eq("usuario_id", ID_USER).execute()
    mapa = {f"{c['nombre']} ({c['empresa']})": c for c in cli.data} if cli.data else {}

    if mapa:
        sel = st.selectbox("Cliente", list(mapa.keys()))
        dat = mapa[sel]
        prob = st.text_area("Problema del cliente")
        c1, c2 = st.columns(2)
        enf = c1.selectbox("Enfoque", ["Eficiencia", "Control", "Ventas", "Modernización"])
        lim = c2.date_input("Fecha Entrega")

        if st.button("🚀 Generar Propuesta", type="primary"):
            if api_key_final and prob:
                with st.spinner("Pensando..."):
                    try:
                        p = f"Actúa como Consultor de Software. Cliente: {dat['rubro']}. Problema: {prob}. Enfoque: {enf}. Crea una propuesta comercial (Título, Diagnóstico, Solución, Funciones, Beneficios)."
                        
                        # USAMOS EL MODELO CLÁSICO GEMINI-PRO (ESTABLE)
                        model = genai.GenerativeModel('gemini-pro')
                        
                        res = model.generate_content(p)
                        st.session_state.res_ia = res.text
                        st.session_state.prob_ia = prob
                    except Exception as e: st.error(f"Error IA: {e}")
            else: st.warning("Falta API Key o Problema")

        if 'res_ia' in st.session_state:
            with st.container(border=True):
                st.markdown(st.session_state.res_ia)
                st.divider()
                if st.button("💾 Guardar"):
                    supabase.table("agencia_proyectos").insert({
                        "usuario_id": ID_USER, "cliente_id": dat['id'], "problema_cliente": st.session_state.prob_ia,
                        "solucion_ia": st.session_state.res_ia, "fecha_limite_entrega": str(lim)
                    }).execute()
                    st.success("Guardado"); del st.session_state.res_ia
    else: st.warning("Carga clientes primero")

# 4. PROYECTOS
elif menu == "📂 Estado de Proyectos":
    st.header("📂 Pipeline")
    if ROL == 'DIRECTOR': proys = supabase.table("agencia_proyectos").select("*, agencia_clientes(empresa), agencia_usuarios(nombre_completo)").order("created_at", desc=True).execute()
    else: proys = supabase.table("agencia_proyectos").select("*, agencia_clientes(empresa)").eq("usuario_id", ID_USER).order("created_at", desc=True).execute()

    if proys.data:
        for p in proys.data:
            tit = f"📂 {p['agencia_clientes']['empresa']}"
            if ROL == 'DIRECTOR' and 'agencia_usuarios' in p: tit += f" ({p['agencia_usuarios']['nombre_completo']})"
            
            with st.expander(tit):
                k = f"ed_{p['id']}"
                if k not in st.session_state: st.session_state[k] = False
                
                if not st.session_state[k]: # Lectura
                    col1, col2 = st.columns([5,1])
                    if col2.button("✏️", key=f"b_{p['id']}"): st.session_state[k]=True; st.rerun()
                    st.write(f"**Problema:** {p['problema_cliente']}")
                    st.markdown(p['solucion_ia'])
                    st.divider()
                    est = ["EN_PREPARACION", "ENVIADO", "GANADO", "PERDIDO"]
                    try: i = est.index(p['estado_proyecto'])
                    except: i=0
                    ne = st.selectbox("Estado", est, index=i, key=f"s_{p['id']}")
                    if ne != p['estado_proyecto']:
                        supabase.table("agencia_proyectos").update({"estado_proyecto": ne}).eq("id", p['id']).execute(); st.rerun()
                else: # Edición
                    np = st.text_area("Problema", value=p['problema_cliente'], key=f"tp_{p['id']}")
                    ns = st.text_area("Solución", value=p['solucion_ia'], height=300, key=f"ts_{p['id']}")
                    if st.button("💾 Guardar", key=f"sv_{p['id']}"):
                        supabase.table("agencia_proyectos").update({"problema_cliente": np, "solucion_ia": ns}).eq("id", p['id']).execute()
                        st.session_state[k]=False; st.rerun()
    else: st.info("No hay proyectos activos.")
