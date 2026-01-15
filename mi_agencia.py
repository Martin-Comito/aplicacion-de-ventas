import streamlit as st
import pandas as pd
from supabase import create_client
import google.generativeai as genai
from datetime import datetime, time, date
import pytz
import time as time_module
import extra_streamlit_components as stx # LIBRERÍA NUEVA PARA COOKIES

# CONFIGURACIÓN INICIAL
st.set_page_config(page_title="DevStudio Manager", page_icon="💼", layout="wide")

# CONEXIÓN SUPABASE
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error: No se encontraron las claves de Supabase. Configura .streamlit/secrets.toml")
    st.stop()

# GESTOR DE COOKIES 
# Esto maneja la memoria del navegador
cookie_manager = stx.CookieManager()

# FUNCIONES DE AUTENTICACIÓN 
def login_check(user, password):
    try:
        res = supabase.table("agencia_usuarios").select("*").eq("username", user).eq("password", password).execute()
        if res.data: return res.data[0]
        return None
    except: return None

def get_user_from_cookie():
    # Busca la cookie 'agencia_user'
    cookie_user = cookie_manager.get('agencia_user')
    if cookie_user:
        # Validamos que el usuario de la cookie siga existiendo en la base de datos
        res = supabase.table("agencia_usuarios").select("*").eq("username", cookie_user).execute()
        if res.data: return res.data[0]
    return None

# LÓGICA DE SESIÓN (PERSISTENCIA)
if 'usuario' not in st.session_state: st.session_state.usuario = None

# Intentar auto-login con cookie si no hay sesión activa
if st.session_state.usuario is None:
    user_from_cookie = get_user_from_cookie()
    if user_from_cookie:
        st.session_state.usuario = user_from_cookie

# PANTALLA DE LOGIN (Si no hay usuario ni cookie válida)
if st.session_state.usuario is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("")
        st.markdown("<h1 style='text-align: center;'>🚀 DevStudio</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Acceso al Portal</h3>", unsafe_allow_html=True)
        with st.container(border=True):
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            
            if st.button("INGRESAR", type="primary", use_container_width=True):
                user_data = login_check(user_input, pass_input)
                if user_data:
                    st.session_state.usuario = user_data
                    # GUARDAR COOKIE (Dura 7 días)
                    cookie_manager.set('agencia_user', user_data['username'], expires_at=datetime.now() + pd.Timedelta(days=7))
                    st.toast(f"Bienvenido {user_data['nombre_completo']}")
                    time_module.sleep(1) # Tiempo para que la cookie se asiente
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# APLICACIÓN PRINCIPAL (SOLO USUARIOS LOGUEADOS)
USER = st.session_state.usuario
ID_USER = USER['id']
ROL = USER['rol']

# BARRA LATERAL 
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.write(f"Hola, **{USER['nombre_completo']}**")
    st.caption(f"Rol: {ROL}")
    
    st.write("---")
    menu = st.radio("Menú", ["📇 Mis Clientes", "📅 Agenda", "🧠 Crear Proyecto (IA)", "📂 Estado de Proyectos"])
    
    st.write("---")
    st.write("🤖 **Configuración IA**")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        st.caption("✅ IA Activada")

    st.write("---")
    if st.button("Cerrar Sesión"):
        cookie_manager.delete('agencia_user') # BORRAR COOKIE
        st.session_state.usuario = None
        st.rerun()

# VISTA 1: CLIENTES
if menu == "📇 Mis Clientes":
    st.header("📇 Gestión de Clientes")

    with st.expander("➕ Agregar Nuevo Cliente"):
        with st.form("form_cliente"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre del Contacto *")
            empresa = c2.text_input("Empresa / Negocio *")
            rubro = c1.selectbox("Rubro", ["Comercio", "Logística", "Servicios", "Agro", "Gastronomía", "Construcción", "Otro"])
            tel = c2.text_input("Teléfono / WhatsApp")
            direccion = c1.text_input("Dirección")
            email = c2.text_input("Email")
            notas = st.text_area("Notas Personales")
            
            if st.form_submit_button("Guardar Cliente"):
                if nombre and empresa:
                    try:
                        supabase.table("agencia_clientes").insert({
                            "usuario_id": ID_USER,
                            "nombre": nombre, "empresa": empresa, "rubro": rubro,
                            "telefono": tel, "direccion": direccion, "email": email, "notas_personales": notas
                        }).execute()
                        st.success("Cliente guardado.")
                        time_module.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                else: st.warning("Nombre y Empresa son obligatorios.")

    st.subheader("Directorio")
    
    # Filtro de Rol
    if ROL == 'DIRECTOR':
        res = supabase.table("agencia_clientes").select("*, agencia_usuarios(nombre_completo)").order("created_at", desc=True).execute()
    else:
        res = supabase.table("agencia_clientes").select("*").eq("usuario_id", ID_USER).order("created_at", desc=True).execute()

    if res.data:
        for c in res.data:
            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                titulo = f"**{c['nombre']}** ({c['empresa']})"
                if ROL == 'DIRECTOR' and 'agencia_usuarios' in c:
                    titulo += f" | 👤 *{c['agencia_usuarios']['nombre_completo']}*"
                
                col_a.markdown(titulo)
                col_a.caption(f"🔧 {c['rubro']} | 📞 {c['telefono']} | 📍 {c['direccion']}")
                if c['notas_personales']: col_a.info(f"📝 {c['notas_personales']}")
                
                if col_b.button("🗑️", key=f"del_{c['id']}"):
                    supabase.table("agencia_clientes").delete().eq("id", c['id']).execute()
                    st.rerun()
    else: st.info("No hay clientes registrados.")

# VISTA 2: AGENDA
elif menu == "📅 Agenda":
    st.header("📅 Agenda de Reuniones")

    if ROL == 'DIRECTOR':
        clientes = supabase.table("agencia_clientes").select("id, nombre, empresa").execute()
    else:
        clientes = supabase.table("agencia_clientes").select("id, nombre, empresa").eq("usuario_id", ID_USER).execute()
        
    mapa_clientes = {f"{c['nombre']} ({c['empresa']})": c['id'] for c in clientes.data} if clientes.data else {}

    with st.form("form_cita"):
        c1, c2, c3 = st.columns(3)
        if mapa_clientes:
            cli_sel = c1.selectbox("Cliente", list(mapa_clientes.keys()))
            fecha = c2.date_input("Fecha", min_value=date.today())
            hora = c3.time_input("Hora", value=time(9, 00))
            motivo = st.text_input("Motivo de la reunión")
            
            if st.form_submit_button("Agendar"):
                dt_str = datetime.combine(fecha, hora).isoformat()
                supabase.table("agencia_citas").insert({
                    "usuario_id": ID_USER, "cliente_id": mapa_clientes[cli_sel],
                    "fecha_hora": dt_str, "motivo": motivo
                }).execute()
                st.success("Agendado."); st.rerun()
        else: st.warning("Carga clientes primero.")

    st.divider()
    if ROL == 'DIRECTOR':
        citas = supabase.table("agencia_citas").select("*, agencia_clientes(nombre), agencia_usuarios(nombre_completo)").order("fecha_hora").execute()
    else:
        citas = supabase.table("agencia_citas").select("*, agencia_clientes(nombre)").eq("usuario_id", ID_USER).order("fecha_hora").execute()

    st.subheader("Próximos Eventos")
    if citas.data:
        for cita in citas.data:
            try: dt = datetime.fromisoformat(cita['fecha_hora'])
            except: dt = datetime.now()
            fecha_fmt = dt.strftime('%d/%m %H:%M')
            extra_info = ""
            if ROL == 'DIRECTOR' and 'agencia_usuarios' in cita: extra_info = f" | 👤 {cita['agencia_usuarios']['nombre_completo']}"
            st.info(f"🕒 **{fecha_fmt}** | {cita['agencia_clientes']['nombre']}{extra_info}\n\n📌 {cita['motivo']}")
    else: st.caption("Agenda libre.")

# VISTA 3: IA GENERADOR
elif menu == "🧠 Crear Proyecto (IA)":
    st.header("✨ Generador de Propuestas con IA")
    
    if ROL == 'DIRECTOR':
        clientes = supabase.table("agencia_clientes").select("id, nombre, empresa, rubro").execute()
    else:
        clientes = supabase.table("agencia_clientes").select("id, nombre, empresa, rubro").eq("usuario_id", ID_USER).execute()
    
    mapa_cli = {f"{c['nombre']} ({c['empresa']})": c for c in clientes.data} if clientes.data else {}

    if mapa_cli:
        cli_key = st.selectbox("Seleccionar Cliente", list(mapa_cli.keys()))
        datos_cliente = mapa_cli[cli_key]
        st.info("Describe qué necesita el cliente y la IA redactará la solución comercial.")
        
        problema = st.text_area("Problema / Necesidad del Cliente", height=100)
        c1, c2 = st.columns(2)
        enfoque = c1.selectbox("Enfoque", ["Eficiencia Operativa", "Control de Stock/Dinero", "Aumento de Ventas", "Imagen Profesional"])
        fecha_entrega = c2.date_input("Fecha límite propuesta")

        if st.button("🚀 GENERAR PROPUESTA", type="primary"):
            if api_key and problema:
                with st.spinner("Consultando a la IA..."):
                    try:
                        prompt = f"""
                        Actúa como Consultor de Software. Cliente: {datos_cliente['rubro']}.
                        Problema: {problema}. Enfoque: {enfoque}.
                        Genera una propuesta comercial para una App a medida.
                        Estructura:
                        1. Título Impactante.
                        2. Entendimiento del Problema (Empatía).
                        3. Solución Propuesta (Sin tecnicismos complejos).
                        4. 3 Funcionalidades Clave.
                        5. Beneficio Económico/Operativo.
                        """
                        model = genai.GenerativeModel('gemini-pro')
                        res = model.generate_content(prompt)
                        st.session_state.ia_result = res.text
                        st.session_state.ia_problema = problema
                    except Exception as e: st.error(f"Error IA: {e}")
            else: st.warning("Falta API Key o Problema.")

        if 'ia_result' in st.session_state:
            with st.container(border=True):
                st.markdown(st.session_state.ia_result)
                st.divider()
                if st.button("💾 Guardar Proyecto"):
                    supabase.table("agencia_proyectos").insert({
                        "usuario_id": ID_USER, "cliente_id": datos_cliente['id'],
                        "problema_cliente": st.session_state.ia_problema,
                        "solucion_ia": st.session_state.ia_result,
                        "fecha_limite_entrega": str(fecha_entrega)
                    }).execute()
                    st.success("Proyecto Guardado."); del st.session_state.ia_result
    else: st.warning("Carga clientes primero.")

# VISTA 4: ESTADO DE PROYECTOS (CON EDICIÓN)
elif menu == "📂 Estado de Proyectos":
    st.header("📂 Pipeline de Proyectos")

    if ROL == 'DIRECTOR':
        proys = supabase.table("agencia_proyectos").select("*, agencia_clientes(empresa), agencia_usuarios(nombre_completo)").order("created_at", desc=True).execute()
    else:
        proys = supabase.table("agencia_proyectos").select("*, agencia_clientes(empresa)").eq("usuario_id", ID_USER).order("created_at", desc=True).execute()

    if proys.data:
        for p in proys.data:
            titulo = f"📂 {p['agencia_clientes']['empresa']}"
            if ROL == 'DIRECTOR' and 'agencia_usuarios' in p:
                titulo += f" (Vendedor: {p['agencia_usuarios']['nombre_completo']})"

            with st.expander(titulo):
                # CONTROL DE MODO EDICIÓN
                # Usamos session_state para saber si este proyecto específico se está editando
                key_edit = f"edit_mode_{p['id']}"
                if key_edit not in st.session_state: st.session_state[key_edit] = False

                if not st.session_state[key_edit]:
                    # MODO LECTURA
                    col_tit, col_btn = st.columns([5, 1])
                    col_tit.caption(f"Fecha Entrega: {p['fecha_limite_entrega']}")
                    if col_btn.button("✏️ Editar", key=f"btn_edit_{p['id']}"):
                        st.session_state[key_edit] = True
                        st.rerun()

                    st.write(f"**Problema:** {p['problema_cliente']}")
                    st.markdown("**Solución:**")
                    st.markdown(p['solucion_ia'])
                    
                    st.divider()
                    # Gestión de Estado Rápida
                    c_estado, _ = st.columns([3, 1])
                    estados = ["EN_PREPARACION", "ENVIADO", "GANADO", "PERDIDO"]
                    idx = estados.index(p['estado_proyecto']) if p['estado_proyecto'] in estados else 0
                    
                    nuevo_est = c_estado.selectbox("Estado", estados, index=idx, key=f"s_{p['id']}")
                    if nuevo_est != p['estado_proyecto']:
                        supabase.table("agencia_proyectos").update({"estado_proyecto": nuevo_est}).eq("id", p['id']).execute()
                        st.toast("Estado actualizado"); time_module.sleep(0.5); st.rerun()

                else:
                    # MODO EDICIÓN
                    st.info("✏️ Editando Proyecto")
                    
                    new_prob = st.text_area("Editar Problema", value=p['problema_cliente'], key=f"txt_prob_{p['id']}")
                    new_sol = st.text_area("Editar Solución (Markdown)", value=p['solucion_ia'], height=300, key=f"txt_sol_{p['id']}")
                    
                    c_save, c_cancel = st.columns(2)
                    
                    if c_save.button("💾 Guardar Cambios", key=f"save_{p['id']}", type="primary"):
                        supabase.table("agencia_proyectos").update({
                            "problema_cliente": new_prob,
                            "solucion_ia": new_sol
                        }).eq("id", p['id']).execute()
                        st.session_state[key_edit] = False
                        st.success("Actualizado")
                        st.rerun()
                        
                    if c_cancel.button("❌ Cancelar", key=f"cancel_{p['id']}"):
                        st.session_state[key_edit] = False
                        st.rerun()

    else:
        st.info("No hay proyectos activos.")