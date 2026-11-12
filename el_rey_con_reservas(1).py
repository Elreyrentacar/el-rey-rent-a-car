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

def money(v, cur="USD"):
    # Conservar la representación original de registros históricos en CRC.
    # Las cotizaciones nuevas se generan exclusivamente en USD.
    return f"${v:,.2f}" if cur == "USD" else f"{v:,.0f} CRC"


def create_pdf(q):
    """Cotización Premium: presentación bilingüe según el idioma seleccionado."""
    t = I18N[q["language"]]
    buf = io.BytesIO()
    navy = colors.HexColor("#14223B")
    red = colors.HexColor("#C52F43")
    blue = colors.HexColor("#2563A6")
    pale = colors.HexColor("#F3F6FA")
    muted = colors.HexColor("#58667B")
    white = colors.white

    doc = SimpleDocTemplate(
        buf, pagesize=letter, rightMargin=42, leftMargin=42,
        topMargin=22, bottomMargin=24,
        title=f'EL REY RENT A CAR - {t["quote"]} #{q["id"]}',
        author="EL REY RENT A CAR COSTA RICA",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReyBrand", fontName="Helvetica-Bold", fontSize=17,
        leading=19, alignment=TA_CENTER, textColor=navy, spaceAfter=3))
    styles.add(ParagraphStyle(
        name="ReySubtitle", fontName="Helvetica", fontSize=9,
        leading=13, alignment=TA_CENTER, textColor=muted))
    styles.add(ParagraphStyle(
        name="ReySection", fontName="Helvetica-Bold", fontSize=11,
        leading=15, textColor=navy, spaceBefore=7, spaceAfter=4))
    styles.add(ParagraphStyle(
        name="ReyLabel", fontName="Helvetica-Bold", fontSize=8,
        leading=11, textColor=muted))
    styles.add(ParagraphStyle(
        name="ReyValue", fontName="Helvetica", fontSize=9,
        leading=12, textColor=navy, wordWrap="CJK"))
    styles.add(ParagraphStyle(
        name="ReyTotalLabel", fontName="Helvetica-Bold", fontSize=11,
        leading=16, textColor=white))
    styles.add(ParagraphStyle(
        name="ReyTotalValue", fontName="Helvetica-Bold", fontSize=16,
        leading=19, textColor=white, alignment=2))
    styles.add(ParagraphStyle(
        name="ReyTerms", fontName="Helvetica", fontSize=8,
        leading=12, textColor=navy))
    styles.add(ParagraphStyle(
        name="ReyFooter", fontName="Helvetica", fontSize=8,
        leading=11, alignment=TA_CENTER, textColor=muted))

    def p(value, style="ReyValue"):
        return Paragraph(escape(str(value if value is not None else "—")), styles[style])

    def localized(es, en, pt, fr):
        return {"Español": es, "English": en, "Português": pt,
                "Français": fr}[q["language"]]

    def detail(label, value):
        return [p(label, "ReyLabel"), p(value)]

    story = []
    if os.path.isfile(LOGO_PATH):
        try:
            logo = Image(LOGO_PATH, width=1.35*inch, height=.66*inch,
                         kind="proportional")
            logo.hAlign = "CENTER"
            story.extend([logo, Spacer(1, 3)])
        except Exception:
            pass

    story.extend([
        Paragraph("EL REY RENT A CAR", styles["ReyBrand"]),
        Paragraph("COSTA RICA", styles["ReySubtitle"]),
        Spacer(1, 5),
    ])
    line = Table([[""]], colWidths=[7.3*inch], rowHeights=[3])
    line.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), red),
                              ("BOTTOMPADDING", (0,0), (-1,-1), 0),
                              ("TOPPADDING", (0,0), (-1,-1), 0)]))
    story.extend([line, Spacer(1, 5),
                  Paragraph(escape(t["title"]), styles["ReySection"])])

    metadata = Table([
        [p(t["quote"], "ReyLabel"), p(f'#{q["id"]}'),
         p(t["generated"], "ReyLabel"), p(q["created"])],
    ], colWidths=[1.0*inch, 2.05*inch, 1.15*inch, 3.1*inch])
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), pale),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(metadata)

    story.append(Paragraph(
        localized("DATOS DEL CLIENTE Y VEHÍCULO", "CUSTOMER AND VEHICLE",
                  "CLIENTE E VEÍCULO", "CLIENT ET VÉHICULE"),
        styles["ReySection"]))
    info = [
        [detail(t["customer"], q["customer"]),
         detail(t["vehicle"], q["vehicle"])],
        [detail(localized("Teléfono", "Phone", "Telefone", "Téléphone"),
                q.get("phone") or "—"),
         detail(t["plate"], q.get("plate") or "—")],
        [detail(localized("Correo", "Email", "E-mail", "E-mail"),
                q.get("email") or "—"),
         detail(t["insurance"], q["insurance"])],
    ]
    grid = Table(info, colWidths=[3.65*inch, 3.65*inch])
    grid.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [white, pale]),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW", (0,-1), (-1,-1), .5, colors.HexColor("#E1E6ED")),
    ]))
    story.append(grid)

    story.append(Paragraph(
        localized("DETALLES DEL ALQUILER", "RENTAL DETAILS",
                  "DETALHES DO ALUGUEL", "DÉTAILS DE LOCATION"),
        styles["ReySection"]))
    schedule = [
        [detail(t["pickup"], q["start"]), detail(t["return"], q["end"])],
        [detail(localized("Lugar de recogida", "Pick-up location",
                          "Local de retirada", "Lieu de prise en charge"),
                q["pickup"]),
         detail(localized("Lugar de devolución", "Return location",
                          "Local de devolução", "Lieu de retour"),
                q["dropoff"])],
        [detail(t["days"], q["days"]),
         detail(t["currency"], q["currency"])],
    ]
    schedule_table = Table(schedule, colWidths=[3.65*inch, 3.65*inch])
    schedule_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [pale, white]),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(schedule_table)

    story.append(Paragraph(
        localized("RESUMEN DE PRECIOS", "PRICE SUMMARY",
                  "RESUMO DOS PREÇOS", "RÉCAPITULATIF DES PRIX"),
        styles["ReySection"]))
    amounts = [
        [p(t["daily"]), p(money(q["daily_rate"], q["currency"]))],
        [p(t["rental"]), p(money(q["rental"], q["currency"]))],
        [p(t["late"]), p(money(q["late_fee"], q["currency"]))],
    ]
    costs = Table(amounts, colWidths=[4.9*inch, 2.4*inch])
    costs.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [pale, white]),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(costs)
    total = Table([[
        Paragraph(escape(t["total"]), styles["ReyTotalLabel"]),
        Paragraph(escape(money(q["total"], q["currency"])),
                  styles["ReyTotalValue"])
    ]], colWidths=[4.9*inch, 2.4*inch])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), navy),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.extend([total, Spacer(1, 4)])
    story.append(p(
        f'{t["deposit"]}: {money(q["deposit"], q["currency"])}',
        "ReyTerms"))
    story.append(p(localized(
        "El depósito se indica por separado y no se suma al alquiler.",
        "The security deposit is shown separately and is not added to the rental.",
        "O depósito é apresentado separadamente e não é somado ao aluguel.",
        "Le dépôt de garantie est indiqué séparément et ne s'ajoute pas à la location."),
        "ReyTerms"))

    if q.get("actual_return"):
        story.append(Paragraph(
            localized("DEVOLUCIÓN REGISTRADA", "RECORDED RETURN",
                      "DEVOLUÇÃO REGISTRADA", "RETOUR ENREGISTRÉ"),
            styles["ReySection"]))
        story.append(p(
            f'{q["actual_return"]}  |  '
            f'{localized("Días adicionales", "Additional days", "Dias adicionais", "Jours supplémentaires")}: '
            f'{q["late_days"]}', "ReyTerms"))

    story.append(Paragraph(escape(t["terms"]), styles["ReySection"]))
    story.extend([
        p("• " + t["term1"], "ReyTerms"), Spacer(1, 4),
        p("• " + t["term2"], "ReyTerms"),
    ])
    if q.get("notes"):
        story.extend([
            Paragraph(localized("NOTAS", "NOTES", "OBSERVAÇÕES", "NOTES"),
                      styles["ReySection"]),
            p(q["notes"], "ReyTerms"),
        ])
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def pdf_quote(r):
    return dict(id=r["id"],created=str(r["creado_en"])[:16].replace("T"," "),customer=r["cliente"],email=r.get("email"),phone=r.get("telefono"),vehicle=r["vehiculo"],plate=r.get("placa"),pickup=r["recogida"],dropoff=r["devolucion"],start=r["inicio"],end=r["fin"],days=r["dias"],currency=r["moneda"],daily_rate=safe_float(r["tarifa_diaria"]),rental=safe_float(r["subtotal"]),late_days=r["dias_extra"],late_fee=safe_float(r["recargo"]),deposit=safe_float(r["deposito"]),insurance=r["seguro"],total=safe_float(r["total"]),language=r["idioma"],notes=r.get("notas") or "",actual_return=r.get("devolucion_real"))

st.set_page_config(page_title="EL REY RENT A CAR", page_icon="🚘", layout="wide")
st.markdown("""<style>
.stApp {background:#F4F6FA;color:#152033}
[data-testid="stSidebar"] {background:#101722}
[data-testid="stSidebar"] * {color:#F8FAFC}
[data-testid="stMetric"] {background:#fff;border:1px solid #E4E9F2;border-radius:16px;padding:18px;box-shadow:0 3px 14px rgba(16,24,40,.04)}
[data-testid="stMetricLabel"] {color:#526075}
[data-testid="stMetricValue"] {color:#17233A}
h1,h2,h3 {color:#152033}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {background:#C52F43;border-radius:10px;border:0}
.block-container {padding-top:1.5rem;max-width:1250px}
@media(max-width:640px){.block-container{padding-left:1rem;padding-right:1rem} [data-testid="stMetric"]{padding:12px}}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    estilo = st.selectbox("🎨 Selecciona el logo", ["Normal 🚘", "Navideño 🎄"], index=1 if st.session_state.logo_temporada == "Navideño" else 0)
    st.session_state.logo_temporada = "Navideño" if estilo.startswith("Navideño") else "Normal"
    logo_actual = LOGO_NAVIDAD if st.session_state.logo_temporada == "Navideño" else LOGO_PATH
    if os.path.exists(logo_actual):
        st.image(logo_actual, width=220)
    st.title("EL REY RENT A CAR")
    st.caption("COSTA RICA · PANEL ADMINISTRATIVO")
    page = st.radio("MENÚ", ["Inicio", "Nueva cotización", "Reservas", "Devoluciones", "Vehículos y tarifas", "Historial"])

if page != "Inicio":
    st.title("👑 EL REY RENT A CAR")
    st.caption("Sistema administrativo · Costa Rica")

try:
    if page == "Inicio":
        st.title("👑 Panel de control")
        st.caption("EL REY RENT A CAR · Resumen de operaciones")
        cars = query("rey_vehiculos", "id,activo")
        quotes = query("rey_cotizaciones", "id,total,moneda")
        activos = sum(bool(v["activo"]) for v in cars)
        cotizaciones = len(quotes)
        total_usd = sum(safe_float(q["total"]) for q in quotes if q["moneda"] == "USD")
        a,b = st.columns(2)
        a.metric("🚗 Vehículos activos", activos)
        b.metric("🧾 Cotizaciones", cotizaciones)
        st.metric("💵 Cotizado en USD", money(total_usd, "USD"))
        st.info("Los importes son cotizaciones en USD, no ingresos cobrados. Las cotizaciones históricas en CRC permanecen guardadas y se consultan en Historial.")
        st.subheader("⚡ Accesos rápidos")
        st.caption("Abre el menú lateral para crear cotizaciones, gestionar vehículos, registrar devoluciones o consultar el historial.")
        st.markdown("""<div style="background:#fff;border:1px solid #e4e9f2;border-radius:16px;padding:18px;margin-top:8px">
        <div style="font-weight:700;color:#17233a;font-size:17px">🚘 Tu centro de operaciones</div>
        <div style="color:#566276;margin-top:7px">Tarifas editables · PDF en 4 idiomas · Control de devoluciones · Datos guardados en Supabase</div>
        </div>""",unsafe_allow_html=True)
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
                moneda="USD"
                st.caption("💵 Moneda de cotización: USD ($)")
                daily_default=safe_float(car["tarifa_diaria"])
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
    elif page == "Reservas":
        st.subheader("📅 Reservas administrativas")
        st.caption("Registra solicitudes, revisa disponibilidad y confirma reservas. Importes en USD.")
        reservas = query("rey_reservas", order="id", desc=True)
        vehiculos = query("rey_vehiculos", order="modelo")

        def fecha_reserva(valor):
            # Los horarios de reservas se registran en hora local de Costa Rica.
            if isinstance(valor, datetime):
                return valor.replace(tzinfo=None)
            return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).replace(tzinfo=None)

        def cruza_reserva(vehiculo_id, inicio, fin, excluir=None):
            for r in reservas:
                if r.get("id") == excluir:
                    continue
                if str(r.get("vehiculo_id")) != str(vehiculo_id):
                    continue
                if str(r.get("estado", "")).lower() not in ("confirmada", "en curso"):
                    continue
                if inicio < fecha_reserva(r["fin"]) and fin > fecha_reserva(r["inicio"]):
                    return r
            return None

        a, b, c = st.columns(3)
        a.metric("Pendientes", sum(str(r.get("estado", "")).lower() == "pendiente" for r in reservas))
        b.metric("Confirmadas", sum(str(r.get("estado", "")).lower() == "confirmada" for r in reservas))
        c.metric("En curso", sum(str(r.get("estado", "")).lower() == "en curso" for r in reservas))

        with st.expander("➕ Crear nueva reserva", expanded=not bool(reservas)):
            activos = [v for v in vehiculos if v.get("activo")]
            if not activos:
                st.warning("Primero registra un vehículo activo.")
            else:
                opciones = {f'{v["modelo"]} · #{v["id"]}': v for v in activos}
                with st.form("crear_reserva_rey"):
                    cliente = st.text_input("Nombre del cliente *")
                    col1, col2 = st.columns(2)
                    telefono = col1.text_input("Teléfono / WhatsApp")
                    correo = col2.text_input("Correo electrónico")
                    vehiculo = opciones[st.selectbox("Vehículo *", list(opciones))]
                    tarifa = st.number_input("Tarifa diaria (USD)", min_value=0.0,
                                             value=safe_float(vehiculo["tarifa_diaria"]), step=5.0)
                    col1, col2 = st.columns(2)
                    fecha_inicio = col1.date_input("Fecha de recogida", date.today(), key="res_inicio")
                    hora_inicio = col1.time_input("Hora de recogida", time(8, 0), key="res_hinicio")
                    fecha_fin = col2.date_input("Fecha de devolución", date.today() + timedelta(days=1), key="res_fin")
                    hora_fin = col2.time_input("Hora de devolución", time(8, 0), key="res_hfin")
                    lugar_recogida = st.selectbox("Lugar de recogida", ["SJO", "LIR", "Otro"])
                    if lugar_recogida == "Otro":
                        lugar_recogida = st.text_input("Especifica el lugar de recogida")
                    lugar_devolucion = st.selectbox("Lugar de devolución", ["SJO", "LIR", "Otro"])
                    if lugar_devolucion == "Otro":
                        lugar_devolucion = st.text_input("Especifica el lugar de devolución")
                    notas = st.text_area("Notas internas")
                    guardar = st.form_submit_button("💾 Guardar reserva pendiente", type="primary")
                if guardar:
                    inicio = datetime.combine(fecha_inicio, hora_inicio)
                    fin = datetime.combine(fecha_fin, hora_fin)
                    if not cliente.strip():
                        st.error("Escribe el nombre del cliente.")
                    elif fin <= inicio:
                        st.error("La devolución debe ser posterior a la recogida.")
                    elif not lugar_recogida.strip() or not lugar_devolucion.strip():
                        st.error("Indica ambos lugares.")
                    else:
                        dias = math.ceil((fin - inicio).total_seconds() / 86400)
                        conflicto = cruza_reserva(vehiculo["id"], inicio, fin)
                        if conflicto:
                            st.warning(f'⚠️ El vehículo tiene la reserva confirmada/en curso #{conflicto["id"]} en esas fechas. Puedes guardar la solicitud pendiente, pero no confirmarla mientras exista el conflicto.')
                        data = dict(cliente=cliente.strip(), telefono=telefono, correo=correo,
                                    vehiculo_id=vehiculo["id"], vehiculo=vehiculo["modelo"],
                                    inicio=inicio.isoformat(timespec="minutes"),
                                    fin=fin.isoformat(timespec="minutes"), tarifa_diaria=tarifa,
                                    total=round(dias * tarifa, 2), estado="pendiente",
                                    lugar_recogida=lugar_recogida, lugar_devolucion=lugar_devolucion,
                                    notas=notas)
                        creado = supabase_db().table("rey_reservas").insert(data).execute().data
                        st.success(f'✅ Reserva #{creado[0]["id"]} guardada como pendiente.')
                        st.rerun()

        st.subheader("📋 Gestionar reservas")
        if not reservas:
            st.info("Todavía no hay reservas registradas.")
        else:
            filtro = st.selectbox("Filtrar por estado", ["Todas", "pendiente", "confirmada", "en curso", "finalizada", "cancelada"])
            visibles = [r for r in reservas if filtro == "Todas" or str(r.get("estado", "")).lower() == filtro]
            st.dataframe([{
                "N.º": r["id"], "Cliente": r["cliente"], "Vehículo": r["vehiculo"],
                "Recogida": str(r["inicio"])[:16].replace("T", " "),
                "Devolución": str(r["fin"])[:16].replace("T", " "),
                "Total USD": money(safe_float(r["total"])), "Estado": r["estado"]
            } for r in visibles], use_container_width=True, hide_index=True)
            for r in visibles:
                with st.expander(f'#{r["id"]} · {r["cliente"]} · {r["vehiculo"]} · {r["estado"]}'):
                    st.write("**Teléfono:**", r.get("telefono") or "—")
                    st.write("**Correo:**", r.get("correo") or "—")
                    st.write("**Recogida:**", str(r["inicio"])[:16].replace("T", " "), "·", r.get("lugar_recogida") or "—")
                    st.write("**Devolución:**", str(r["fin"])[:16].replace("T", " "), "·", r.get("lugar_devolucion") or "—")
                    st.write("**Total:**", money(safe_float(r["total"])))
                    st.write("**Notas:**", r.get("notas") or "—")
                    estado_actual = str(r.get("estado") or "pendiente").lower()
                    siguientes = {"pendiente": ["confirmada", "cancelada"],
                                  "confirmada": ["en curso", "cancelada"],
                                  "en curso": ["finalizada"],
                                  "finalizada": [], "cancelada": []}
                    permitidos = siguientes.get(estado_actual, [])
                    if permitidos:
                        nuevo = st.selectbox("Cambiar estado a", permitidos, key=f'est_{r["id"]}')
                        if st.button("Guardar nuevo estado", key=f'guardar_est_{r["id"]}'):
                            # Reconsultar antes de confirmar para detectar cambios recientes.
                            actuales = query("rey_reservas")
                            if nuevo in ("confirmada", "en curso"):
                                choque = next((x for x in actuales
                                    if x["id"] != r["id"]
                                    and str(x.get("vehiculo_id")) == str(r.get("vehiculo_id"))
                                    and str(x.get("estado", "")).lower() in ("confirmada", "en curso")
                                    and fecha_reserva(r["inicio"]) < fecha_reserva(x["fin"])
                                    and fecha_reserva(r["fin"]) > fecha_reserva(x["inicio"])), None)
                                if choque:
                                    st.error(f'⛔ No se puede confirmar: se superpone con la reserva #{choque["id"]}.')
                                    st.stop()
                            supabase_db().table("rey_reservas").update({"estado": nuevo}).eq("id", r["id"]).eq("estado", r["estado"]).execute()
                            st.success("Estado actualizado. Comprueba el resultado en la lista.")
                            st.rerun()
                    else:
                        st.caption("Esta reserva está cerrada y no permite nuevos cambios de estado.")
        st.caption("La verificación de disponibilidad se hace desde este panel. Antes de habilitar reservas públicas, se implementará una validación transaccional en Supabase para evitar conflictos simultáneos.")
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
