
import runpy
import streamlit as st
from supabase import create_client
import time
# Conexion para autenticar usuarios
cfg = st.secrets["supabase"]
auth = create_client(cfg["url"], cfg["key"])

# Administrador principal autorizado
ADMIN_EMAIL = "elreyadministracionrent@gmail.com"

if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False
if "ultima_actividad" not in st.session_state:
    st.session_state.ultima_actividad = time.time()

TIEMPO_LIMITE = 30 * 60

if st.session_state.admin_autenticado:
    tiempo_transcurrido = time.time() - st.session_state.ultima_actividad

    if tiempo_transcurrido >= TIEMPO_LIMITE:
        st.session_state.admin_autenticado = False
        st.session_state.pop("admin_uid", None)
        try:
            auth.auth.sign_out()
        except Exception:
            pass
        st.warning("🔒 Tu sesión expiró por inactividad.")
        st.rerun()


if not st.session_state.admin_autenticado:
    st.title("🔐 EL REY RENT A CAR")
    st.subheader("Acceso administrativo")
    if st.session_state.pop("login_limpio", False):
        st.session_state["login_correo"] = ""
        st.session_state["login_clave"] = ""
    with st.form("login"):
        correo = st.text_input("Correo electrónico", key="login_correo")
        clave = st.text_input("Contraseña", type="password", key="login_clave")
        ingresar = st.form_submit_button("Iniciar sesión")

    if ingresar:
        try:
            resultado = auth.auth.sign_in_with_password({
                "email": correo.strip(),
                "password": clave
            })

            usuario = resultado.user

            if (
                usuario
                and usuario.email
                and usuario.email.lower() == ADMIN_EMAIL.lower()
            ):
                st.session_state.admin_autenticado = True
                st.session_state.ultima_actividad = time.time()
                st.session_state.admin_uid = usuario.id
                st.rerun()
            else:
                st.error("Esta cuenta no tiene acceso administrativo.")

        except Exception:
            st.error("Correo o contraseña incorrectos.")

    st.stop()


st.sidebar.success("🔐 Administrador principal")

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.pop("login_correo", None)
    st.session_state.pop("login_clave", None)
    st.session_state["login_limpio"] = True
    st.session_state.admin_autenticado = False
    st.session_state.pop("admin_uid", None)
    try:
        auth.auth.sign_out()
    except Exception:
        pass
    st.rerun()

runpy.run_path(
    "el_rey_contratos_storage.py",
    run_name="__main__"
)

raise SystemExit

import streamlit as st
import math, io, os
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from supabase import create_client
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from xml.sax.saxutils import escape

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "assets", "file_0000000041ac81f5802486e44686db31.png")
LOGO_NAVIDAD = os.path.join(APP_DIR, "assets", "logo_navidad.jpg")
if "logo_temporada" not in st.session_state:
    st.session_state.logo_temporada = "Normal"
@st.cache_resource
def supabase_db():
    try:
        cfg = st.secrets["supabase"]
        st.write("URL configurada:", repr(cfg["url"]))
        return create_client(cfg["url"], cfg["key"])
    except Exception as exc:
        st.error(f"No se pudo configurar Supabase: {exc}")
        st.stop()


def query(table, columns="*", order=None, desc=False, limit=None):
    q = supabase_db().table(table).select(columns)
    if order: q = q.order(order, desc=desc)
    if limit: q = q.limit(limit)
    return q.execute().data or []

def safe_float(x):
    return float(x or 0)

def get_fx():
    rows = supabase_db().table("rey_configuracion").select("valor").eq("clave", "usd_crc").execute().data
    return float(rows[0]["valor"]) if rows else 510.0

def show_error(exc):
    st.error("No se pudo guardar o consultar la información en Supabase. Comprueba que ejecutaste el archivo SQL y que la clave es correcta.")
    st.caption(str(exc))

I18N = {
    "Español": {
        "title":"COTIZACIÓN DE ALQUILER", "quote":"Cotización", "customer":"Cliente",
        "vehicle":"Vehículo", "plate":"Placa", "pickup":"Recogida", "return":"Devolución",
        "days":"Días contratados", "daily":"Tarifa diaria", "rental":"Subtotal alquiler",
        "late":"Cargo por devolución tardía", "deposit":"Depósito de garantía",
        "total":"Total estimado", "insurance":"Seguro", "location":"Lugar",
        "terms":"Condiciones", "term1":"La devolución después de la hora acordada genera el cobro de un día adicional, sin horas de cortesía.",
        "term2":"La cotización está sujeta a disponibilidad y confirmación de la empresa.",
        "currency":"Moneda", "generated":"Generada el"
    },
    "English": {
        "title":"CAR RENTAL QUOTATION", "quote":"Quotation", "customer":"Customer",
        "vehicle":"Vehicle", "plate":"License plate", "pickup":"Pick-up", "return":"Return",
        "days":"Rental days", "daily":"Daily rate", "rental":"Rental subtotal",
        "late":"Late return charge", "deposit":"Security deposit",
        "total":"Estimated total", "insurance":"Insurance", "location":"Location",
        "terms":"Terms and conditions", "term1":"Returning the vehicle after the agreed time results in an additional full-day charge. No grace period applies.",
        "term2":"This quotation is subject to vehicle availability and company confirmation.",
        "currency":"Currency", "generated":"Generated on"
    },
    "Português": {
        "title":"COTAÇÃO DE ALUGUEL DE VEÍCULO", "quote":"Cotação", "customer":"Cliente",
        "vehicle":"Veículo", "plate":"Placa", "pickup":"Retirada", "return":"Devolução",
        "days":"Dias contratados", "daily":"Tarifa diária", "rental":"Subtotal do aluguel",
        "late":"Taxa por devolução atrasada", "deposit":"Depósito de garantia",
        "total":"Total estimado", "insurance":"Seguro", "location":"Local",
        "terms":"Termos e condições", "term1":"A devolução após o horário combinado gera a cobrança de um dia adicional completo, sem período de tolerância.",
        "term2":"Esta cotação está sujeita à disponibilidade do veículo e à confirmação da empresa.",
        "currency":"Moeda", "generated":"Gerada em"
    },
    "Français": {
        "title":"DEVIS DE LOCATION DE VOITURE", "quote":"Devis", "customer":"Client",
        "vehicle":"Véhicule", "plate":"Immatriculation", "pickup":"Prise en charge", "return":"Retour",
        "days":"Jours de location", "daily":"Tarif journalier", "rental":"Sous-total de location",
        "late":"Frais de retour tardif", "deposit":"Dépôt de garantie",
        "total":"Total estimé", "insurance":"Assurance", "location":"Lieu",
        "terms":"Conditions", "term1":"Tout retour après l'heure convenue entraîne la facturation d'une journée supplémentaire complète, sans délai de grâce.",
        "term2":"Ce devis est soumis à la disponibilité du véhicule et à la confirmation de l'entreprise.",
        "currency":"Devise", "generated":"Émis le"
    }
}

def money(v, cur):
    return (f"${v:,.2f}" if cur == "USD" else f"₡{v:,.0f}")

def create_pdf(q):
    t = I18N[q["language"]]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=42, leftMargin=42, topMargin=34, bottomMargin=36)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#17191f")))
    styles.add(ParagraphStyle(name="Sub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=11))
    story = []
    if os.path.exists(LOGO_PATH):
        try:
            im = Image(LOGO_PATH, width=2.25*inch, height=1.0*inch, kind="proportional")
            im.hAlign = "CENTER"
            story += [im, Spacer(1,8)]
        except Exception:
            pass
    story += [Paragraph("EL REY RENT A CAR", styles["Brand"]), Paragraph("COSTA RICA", styles["Sub"]), Spacer(1,16),
              Paragraph(t["title"], styles["Heading2"]), Spacer(1,8)]
    rows = [
        [t["quote"], f'#{q["id"]}', t["generated"], q["created"]],
        [t["customer"], escape(str(q["customer"] or "—")), t["vehicle"], q["vehicle"]],
        [t["plate"], q["plate"] or "—", t["insurance"], q["insurance"]],
        [t["pickup"], q["start"], t["return"], q["end"]],
        [t["location"], q["pickup"] + " → " + q["dropoff"], t["days"], str(q["days"])],
        [t["currency"], q["currency"], t["daily"], money(q["daily_rate"], q["currency"])],
        [t["rental"], money(q["rental"], q["currency"]), t["late"], money(q["late_fee"], q["currency"])],
        [t["deposit"], money(q["deposit"], q["currency"]), t["total"], money(q["total"], q["currency"])],
        ["Devolución real", q.get("actual_return") or "—", "Días adicionales", str(q["late_days"])]
    ]
    table = Table(rows, colWidths=[1.15*inch,2.1*inch,1.15*inch,2.1*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#222222")),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#d1d5db")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)
    ]))
    story += [table, Spacer(1,18), Paragraph(t["terms"], styles["Heading3"]),
              Paragraph("• " + t["term1"], styles["Small"]), Spacer(1,4),
              Paragraph("• " + t["term2"], styles["Small"])]
    if q["notes"]:
        story += [Spacer(1,10), Paragraph(escape(str(q["notes"])), styles["Small"])]
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def pdf_quote(r):
    return dict(id=r["id"],created=str(r["creado_en"])[:16].replace("T"," "),customer=r["cliente"],email=r.get("email"),phone=r.get("telefono"),vehicle=r["vehiculo"],plate=r.get("placa"),pickup=r["recogida"],dropoff=r["devolucion"],start=r["inicio"],end=r["fin"],days=r["dias"],currency=r["moneda"],daily_rate=safe_float(r["tarifa_diaria"]),rental=safe_float(r["subtotal"]),late_days=r["dias_extra"],late_fee=safe_float(r["recargo"]),deposit=safe_float(r["deposito"]),insurance=r["seguro"],total=safe_float(r["total"]),language=r["idioma"],notes=r.get("notas") or "",actual_return=r.get("devolucion_real"))

st.set_page_config(page_title="EL REY RENT A CAR", page_icon="🚘", layout="wide")
st.markdown("""<style>.stApp{background:#f5f6f8}[data-testid="stSidebar"]{background:#101116}[data-testid="stSidebar"] *{color:#fff}h1,h2,h3{color:#15171d}</style>""", unsafe_allow_html=True)
with st.sidebar:
    
    estilo = st.selectbox(
        "🎨 Selecciona el logo",
        ["Normal 🚘", "Navideño 🎄"],
        index=1
    )
    logo_actual = LOGO_PATH if estilo == "Normal 🚘" else LOGO_NAVIDAD
    if os.path.exists(logo_actual):
        st.image(logo_actual, width=220)

    st.title("EL REY RENT A CAR")
    st.caption("COSTA RICA · PANEL ADMINISTRATIVO")
    page = st.radio("MENÚ", ["Inicio", "Nueva cotización", "Devoluciones", "Vehículos y tarifas", "Historial", "Configuración"])
st.title("👑 EL REY RENT A CAR")
st.caption("Sistema administrativo con almacenamiento en Supabase")

try:
    if page == "Inicio":
        cars = query("rey_vehiculos", "id,activo")
        quotes = query("rey_cotizaciones", "id,total,moneda")
        a,b,c = st.columns(3)
        a.metric("Vehículos activos", sum(bool(v["activo"]) for v in cars))
        b.metric("Cotizaciones creadas", len(quotes))
        c.metric("Total cotizado USD*", money(sum(safe_float(q["total"]) for q in quotes if q["moneda"]=="USD"), "USD"))
        st.info("*Total de cotizaciones en USD; no representa pagos recibidos. Las cotizaciones en CRC no se incluyen.")
    elif page == "Vehículos y tarifas":
        st.subheader("🚗 Vehículos y tarifas")
        cars = query("rey_vehiculos", order="id")
        for car in cars:
            with st.expander(f'{car["modelo"]} · ${safe_float(car["tarifa_diaria"]):,.2f} USD/día'):
                with st.form(f'veh_{car["id"]}'):
                    modelo=st.text_input("Modelo",car["modelo"])
                    anio=st.text_input("Año",str(car.get("anio") or ""))
                    placa=st.text_input("Placa",car.get("placa") or "")
                    tarifa=st.number_input("Tarifa diaria USD",min_value=0.0,value=safe_float(car["tarifa_diaria"]),step=5.0)
                    activo=st.checkbox("Activo",value=bool(car["activo"]))
                    if st.form_submit_button("Guardar cambios"):
                        supabase_db().table("rey_vehiculos").update(dict(modelo=modelo,anio=anio,placa=placa or None,tarifa_diaria=tarifa,activo=activo)).eq("id",car["id"]).execute()
                        st.success("Vehículo actualizado"); st.rerun()
        with st.form("new_car"):
            st.subheader("Agregar vehículo")
            modelo=st.text_input("Modelo nuevo")
            anio=st.text_input("Año nuevo")
            placa=st.text_input("Placa nueva")
            tarifa=st.number_input("Tarifa diaria USD nueva",min_value=0.0,value=90.0)
            if st.form_submit_button("Agregar vehículo"):
                if not modelo.strip(): st.error("Indica un modelo")
                else:
                    supabase_db().table("rey_vehiculos").insert(dict(modelo=modelo.strip(),anio=anio,placa=placa or None,tarifa_diaria=tarifa,activo=True)).execute()
                    st.success("Vehículo agregado"); st.rerun()
    elif page == "Configuración":
        st.subheader("⚙️ Configuración")
        fx=st.number_input("1 USD = CRC",min_value=1.0,value=get_fx(),step=1.0)
        if st.button("Guardar tipo de cambio"):
            supabase_db().table("rey_configuracion").upsert({"clave":"usd_crc","valor":str(fx)},on_conflict="clave").execute()
            st.success("Tipo de cambio guardado")
    elif page == "Nueva cotización":
        st.subheader("🧾 Crear cotización")
        cars=[c for c in query("rey_vehiculos",order="modelo") if c["activo"]]
        if not cars: st.warning("Agrega un vehículo activo primero")
        else:
            car_options={f'{c["modelo"]} · #{c["id"]}':c for c in cars}
            with st.form("quote"):
                a,b=st.columns(2)
                cliente=a.text_input("Nombre del cliente")
                email=b.text_input("Correo")
                telefono=a.text_input("Teléfono / WhatsApp")
                car=car_options[b.selectbox("Vehículo",list(car_options))]
                placa=st.text_input("Placa",car.get("placa") or "")
                moneda=st.selectbox("Moneda",["USD","CRC"])
                daily_default=safe_float(car["tarifa_diaria"])*(get_fx() if moneda=="CRC" else 1)
                tarifa=st.number_input(f"Precio por día ({moneda})",min_value=0.0,value=float(daily_default),step=5.0)
                seguro=st.selectbox("Seguro",["Básico","Estándar","Completo","No especificado"])
                deposito=st.number_input(f"Depósito de garantía ({moneda})",min_value=0.0,value=0.0)
                a,b=st.columns(2)
                fecha_inicio=a.date_input("Fecha de recogida",date.today())
                hora_inicio=a.time_input("Hora de recogida",time(8,0))
                fecha_fin=b.date_input("Fecha de devolución pactada",date.today()+timedelta(days=1))
                hora_fin=b.time_input("Hora de devolución pactada",time(8,0))
                recogida=st.text_input("Lugar de recogida","SJO")
                devolucion=st.text_input("Lugar de devolución","SJO")
                idioma=st.selectbox("Idioma del PDF",["Español","English","Português","Français"])
                notas=st.text_area("Notas")
                submitted=st.form_submit_button("Calcular y guardar cotización",type="primary")
            if submitted:
                inicio=datetime.combine(fecha_inicio,hora_inicio)
                fin=datetime.combine(fecha_fin,hora_fin)
                if fin<=inicio: st.error("La devolución debe ser posterior a la recogida")
                elif not cliente.strip(): st.error("Escribe el nombre del cliente")
                else:
                    dias=math.ceil((fin-inicio).total_seconds()/86400)
                    subtotal=dias*tarifa
                    data=dict(cliente=cliente.strip(),email=email,telefono=telefono,vehiculo_id=car["id"],vehiculo=car["modelo"],placa=placa,recogida=recogida,devolucion=devolucion,inicio=inicio.strftime("%Y-%m-%d %H:%M"),fin=fin.strftime("%Y-%m-%d %H:%M"),dias=dias,moneda=moneda,tarifa_diaria=tarifa,subtotal=subtotal,dias_extra=0,recargo=0,deposito=deposito,seguro=seguro,total=subtotal,idioma=idioma,notas=notas)
                    saved=supabase_db().table("rey_cotizaciones").insert(data).execute().data[0]
                    st.session_state["last_quote_id"]=saved["id"]
                    st.success(f'Cotización #{saved["id"]} guardada en Supabase')
            if st.session_state.get("last_quote_id"):
                res=supabase_db().table("rey_cotizaciones").select("*").eq("id",st.session_state["last_quote_id"]).execute().data
                if res:
                    q=pdf_quote(res[0]); st.download_button("📄 Descargar PDF",data=create_pdf(q),file_name=f'El_Rey_Cotizacion_{q["id"]}.pdf',mime="application/pdf")
                    st.caption("El depósito se muestra separado del precio del alquiler")
    elif page == "Devoluciones":
        st.subheader("⏱️ Registrar devolución real")
        st.caption("Sin horas de cortesía: cualquier retraso genera un día completo; cada 24 horas adicionales, otro día.")
        rows=query("rey_cotizaciones",order="id",desc=True)
        if not rows: st.info("Primero crea una cotización")
        else:
            options={f'#{r["id"]} · {r["cliente"]} · {r["vehiculo"]} · {r["fin"]}':r for r in rows}
            q=options[st.selectbox("Alquiler / cotización",list(options))]
            st.write("**Devolución pactada:**",q["fin"])
            if q.get("devolucion_real"):
                st.success(f'Devolución registrada: {q["devolucion_real"]} · Recargo: {money(safe_float(q["recargo"]),q["moneda"])}')
            fecha=st.date_input("Fecha de devolución real",date.today())
            hora=st.time_input("Hora de devolución real",datetime.now().time().replace(second=0,microsecond=0))
            if st.button("Calcular y guardar recargo",type="primary"):
                pactada=datetime.strptime(q["fin"],"%Y-%m-%d %H:%M")
                real=datetime.combine(fecha,hora)
                demora=(real-pactada).total_seconds()
                extra=math.ceil(demora/86400) if demora>0 else 0
                cargo=extra*safe_float(q["tarifa_diaria"])
                supabase_db().table("rey_cotizaciones").update(dict(devolucion_real=real.strftime("%Y-%m-%d %H:%M"),dias_extra=extra,recargo=cargo,total=safe_float(q["subtotal"])+cargo)).eq("id",q["id"]).execute()
                st.success(f'Recargo guardado: {money(cargo,q["moneda"])} · {extra} día(s) extra')
                st.rerun()
    elif page == "Historial":
        st.subheader("📚 Historial de cotizaciones")
        rows=query("rey_cotizaciones",order="id",desc=True)
        if not rows: st.info("Todavía no hay cotizaciones")
        else:
            st.dataframe([{"N.º":r["id"],"Cliente":r["cliente"],"Vehículo":r["vehiculo"],"Recogida":r["inicio"],"Devolución":r["fin"],"Total":money(safe_float(r["total"]),r["moneda"]),"Idioma":r["idioma"]} for r in rows],use_container_width=True)
            selected=st.selectbox("Cotización para descargar",[r["id"] for r in rows])
            q=pdf_quote(next(r for r in rows if r["id"]==selected))
            st.download_button("📄 Descargar PDF",data=create_pdf(q),file_name=f'El_Rey_Cotizacion_{selected}.pdf',mime="application/pdf")
except Exception as exc:
    show_error(exc)
st.markdown("---")
st.caption("EL REY RENT A CAR COSTA RICA · Verifica tarifas, seguros, impuestos y condiciones antes de entregar cotizaciones.")
