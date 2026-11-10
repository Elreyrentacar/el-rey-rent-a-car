import streamlit as st
import sqlite3, math, io, os
from datetime import datetime, date, time, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "el_rey.db")
LOGO_PATH = os.path.join(APP_DIR, "assets", "logo.png")

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

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS vehicles(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, year TEXT,
            plate TEXT, rate_usd REAL NOT NULL DEFAULT 90, active INTEGER NOT NULL DEFAULT 1)""")
        con.execute("""CREATE TABLE IF NOT EXISTS quotes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, customer TEXT, email TEXT,
            phone TEXT, vehicle TEXT, plate TEXT, pickup TEXT, dropoff TEXT,
            start TEXT, end TEXT, days INTEGER, currency TEXT, daily_rate REAL,
            rental REAL, late_days INTEGER, late_fee REAL, deposit REAL, insurance TEXT,
            total REAL, language TEXT, notes TEXT)""")
        count = con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        if count == 0:
            seed = [
                ("Toyota RAV4","", "",90), ("Hyundai Tucson","", "",85),
                ("Hyundai Santa Fe","", "",100), ("Suzuki Grand Vitara","", "",75),
                ("Toyota Corolla Cross","", "",90)
            ]
            con.executemany("INSERT INTO vehicles(name,year,plate,rate_usd) VALUES(?,?,?,?)", seed)
        # Add actual-return tracking to databases created by earlier versions.
        cols = [r[1] for r in con.execute("PRAGMA table_info(quotes)").fetchall()]
        if "actual_return" not in cols:
            con.execute("ALTER TABLE quotes ADD COLUMN actual_return TEXT")
        con.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('usd_crc','510')")
        con.commit()

def setting(key, default):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

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
        [t["customer"], q["customer"] or "—", t["vehicle"], q["vehicle"]],
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
        story += [Spacer(1,10), Paragraph(q["notes"], styles["Small"])]
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

st.set_page_config(page_title="EL REY RENT A CAR", page_icon="🚘", layout="wide")
init_db()
st.markdown("""
<style>
.stApp {background:#f5f6f8}
[data-testid="stSidebar"] {background:#101116}
[data-testid="stSidebar"] * {color:#fff}
h1,h2,h3 {color:#15171d}
div.stButton>button {border-radius:9px;font-weight:600}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
    st.title("EL REY RENT A CAR")
    st.caption("COSTA RICA · PANEL ADMINISTRATIVO")
    page = st.radio("MENÚ", ["Inicio", "Nueva cotización", "Devoluciones", "Vehículos y tarifas", "Historial", "Configuración"])

st.title("👑 EL REY RENT A CAR")
st.caption("Sistema de administración de alquiler de vehículos")

if page == "Inicio":
    with db() as con:
        vehicles = con.execute("SELECT COUNT(*) FROM vehicles WHERE active=1").fetchone()[0]
        quotes = con.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        revenue = con.execute("SELECT COALESCE(SUM(total),0) FROM quotes").fetchone()[0]
    a,b,c = st.columns(3)
    a.metric("Vehículos activos", vehicles)
    b.metric("Cotizaciones creadas", quotes)
    c.metric("Total cotizado*","$"+f"{revenue:,.2f}")
    st.info("*Suma informativa de cotizaciones guardadas; no representa necesariamente pagos recibidos.")
    st.subheader("Accesos rápidos")
    st.write("Usa el menú lateral para crear cotizaciones, administrar vehículos y consultar el historial.")

elif page == "Vehículos y tarifas":
    st.subheader("🚗 Vehículos y precios por día")
    with db() as con:
        rows = con.execute("SELECT id,name,year,plate,rate_usd,active FROM vehicles ORDER BY id").fetchall()
    for row in rows:
        with st.expander(f"{row[1]} · ${row[4]:,.2f} USD/día", expanded=False):
            with st.form(f"vehicle_{row[0]}"):
                name = st.text_input("Nombre / modelo", row[1])
                year = st.text_input("Año", row[2] or "")
                plate = st.text_input("Placa", row[3] or "")
                rate = st.number_input("Tarifa diaria (USD)", min_value=0.0, value=float(row[4]), step=5.0)
                active = st.checkbox("Vehículo activo", bool(row[5]))
                if st.form_submit_button("Guardar cambios"):
                    with db() as con:
                        con.execute("UPDATE vehicles SET name=?,year=?,plate=?,rate_usd=?,active=? WHERE id=?",
                                    (name,year,plate,rate,int(active),row[0]))
                        con.commit()
                    st.success("Vehículo actualizado.")
                    st.rerun()
    st.markdown("---")
    st.subheader("Agregar vehículo")
    with st.form("new_vehicle"):
        n1,n2,n3 = st.columns(3)
        name = n1.text_input("Modelo *")
        year = n2.text_input("Año")
        plate = n3.text_input("Placa")
        rate = st.number_input("Tarifa diaria (USD)", min_value=0.0, value=90.0, step=5.0)
        if st.form_submit_button("Agregar vehículo"):
            if name.strip():
                with db() as con:
                    con.execute("INSERT INTO vehicles(name,year,plate,rate_usd) VALUES(?,?,?,?)",(name,year,plate,rate))
                    con.commit()
                st.success("Vehículo agregado.")
                st.rerun()
            else: st.error("Escribe el modelo del vehículo.")

elif page == "Configuración":
    st.subheader("⚙️ Configuración del negocio")
    fx = float(setting("usd_crc","510"))
    new_fx = st.number_input("Tipo de cambio de referencia: 1 USD = CRC", min_value=1.0, value=fx, step=1.0)
    st.caption("Actualiza este valor manualmente según el tipo de cambio que quieras aplicar a tus cotizaciones.")
    if st.button("Guardar tipo de cambio"):
        with db() as con:
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('usd_crc',?)",(str(new_fx),))
            con.commit()
        st.success("Tipo de cambio guardado.")

elif page == "Nueva cotización":
    st.subheader("🧾 Crear cotización")
    with db() as con:
        cars = con.execute("SELECT name,plate,rate_usd FROM vehicles WHERE active=1 ORDER BY name").fetchall()
    if not cars:
        st.warning("Primero agrega un vehículo activo.")
    else:
        names = [x[0] for x in cars]
        with st.form("quote_form"):
            c1,c2 = st.columns(2)
            customer = c1.text_input("Nombre del cliente")
            email = c2.text_input("Correo electrónico")
            phone = c1.text_input("Teléfono / WhatsApp")
            vehicle_name = c2.selectbox("Vehículo", names)
            selected = next(x for x in cars if x[0] == vehicle_name)
            plate = st.text_input("Placa", selected[1] or "")
            curr = st.selectbox("Moneda", ["USD","CRC"])
            fx = float(setting("usd_crc","510"))
            base_rate = float(selected[2]) * (fx if curr=="CRC" else 1)
            daily = st.number_input(f"Precio por día ({curr})", min_value=0.0, value=float(base_rate), step=5.0)
            insurance = st.selectbox("Seguro", ["Básico","Estándar","Completo","No especificado"])
            deposit = st.number_input(f"Depósito de garantía ({curr})", min_value=0.0, value=0.0, step=50.0)
            p1,p2 = st.columns(2)
            start_date = p1.date_input("Fecha de recogida", value=date.today())
            start_time = p1.time_input("Hora de recogida", value=time(8,0))
            end_date = p2.date_input("Fecha y hora acordada de devolución", value=date.today()+timedelta(days=1))
            end_time = p2.time_input("Hora de devolución", value=time(8,0))
            pickup = st.text_input("Lugar de recogida", "SJO")
            dropoff = st.text_input("Lugar de devolución", "SJO")
            language = st.selectbox("Idioma del PDF", ["Español","English","Português","Français"])
            notes = st.text_area("Notas adicionales")
            submitted = st.form_submit_button("Calcular y guardar cotización", type="primary")
        if submitted:
            start = datetime.combine(start_date,start_time)
            end = datetime.combine(end_date,end_time)
            if end <= start:
                st.error("La devolución debe ser posterior a la recogida.")
            else:
                seconds = (end-start).total_seconds()
                days = math.ceil(seconds/86400)
                rental = days*daily
                # Retardo: no grace. Any positive delay past agreed return triggers a full day;
                # each subsequent 24-hour block triggers another full day.
                late_days = 0
                late_fee = 0.0
                total = rental + late_fee
                created = datetime.now().strftime("%Y-%m-%d %H:%M")
                q = dict(id=0,created=created,customer=customer,email=email,phone=phone,
                         vehicle=vehicle_name,plate=plate,pickup=pickup,dropoff=dropoff,
                         start=start.strftime("%Y-%m-%d %H:%M"),end=end.strftime("%Y-%m-%d %H:%M"),
                         days=days,currency=curr,daily_rate=daily,rental=rental,
                         late_days=late_days,late_fee=late_fee,deposit=deposit,
                         insurance=insurance,total=total,language=language,notes=notes,actual_return=None)
                with db() as con:
                    cur=con.execute("""INSERT INTO quotes(created,customer,email,phone,vehicle,plate,pickup,dropoff,start,end,days,currency,daily_rate,rental,late_days,late_fee,deposit,insurance,total,language,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (created,customer,email,phone,vehicle_name,plate,pickup,dropoff,q["start"],q["end"],days,curr,daily,rental,late_days,late_fee,deposit,insurance,total,language,notes))
                    q["id"]=cur.lastrowid
                    con.commit()
                st.success("Cotización guardada.")
                st.write(f"**{days} día(s) · Alquiler: {money(rental,curr)} · Depósito: {money(deposit,curr)}**")
                st.download_button("📄 Descargar cotización PDF", data=create_pdf(q),
                                   file_name=f"El_Rey_Cotizacion_{q['id']}.pdf", mime="application/pdf")
                st.caption("El depósito se muestra por separado y no se suma al precio del alquiler.")

elif page == "Devoluciones":
    st.subheader("⏱️ Registrar devolución real")
    st.caption("Sin horas de cortesía: cualquier minuto después de la hora pactada genera un día adicional. Cada nuevo bloque de 24 horas genera otro día.")
    with db() as con:
        rows = con.execute("SELECT id,customer,vehicle,end,currency,daily_rate,late_days,late_fee,actual_return FROM quotes ORDER BY id DESC").fetchall()
    if not rows:
        st.info("Primero debes crear una cotización.")
    else:
        labels = {f'#{r[0]} · {r[1] or "Cliente"} · {r[2]} · devolución pactada {r[3]}': r for r in rows}
        chosen = st.selectbox("Alquiler / cotización", list(labels.keys()))
        r = labels[chosen]
        quote_id, customer, vehicle, planned_end, currency, daily_rate, old_late_days, old_late_fee, actual_return = r
        st.write(f"**Devolución pactada:** {planned_end}")
        if actual_return:
            st.success(f"Devolución registrada: {actual_return} · Recargo guardado: {money(old_late_fee,currency)} ({old_late_days} día(s) adicional(es)).")
        actual_date = st.date_input("Fecha de devolución real", value=date.today(), key="actual_date")
        actual_time = st.time_input("Hora de devolución real", value=datetime.now().time().replace(second=0,microsecond=0), key="actual_time")
        if st.button("Calcular y guardar recargo", type="primary"):
            planned = datetime.strptime(planned_end, "%Y-%m-%d %H:%M")
            actual = datetime.combine(actual_date, actual_time)
            delay_seconds = (actual-planned).total_seconds()
            extra_days = math.ceil(delay_seconds/86400) if delay_seconds > 0 else 0
            fee = extra_days * float(daily_rate)
            actual_text = actual.strftime("%Y-%m-%d %H:%M")
            with db() as con:
                con.execute("UPDATE quotes SET actual_return=?,late_days=?,late_fee=?,total=(rental+?) WHERE id=?",
                            (actual_text,extra_days,fee,fee,quote_id))
                con.commit()
            st.success(f"Devolución registrada. Días adicionales: {extra_days}. Recargo: {money(fee,currency)}.")
            st.caption("El depósito de garantía se mantiene separado del total del alquiler.")
            st.rerun()

elif page == "Historial":
    st.subheader("📚 Historial de cotizaciones")
    with db() as con:
        rows = con.execute("SELECT id,created,customer,vehicle,start,end,total,currency,language FROM quotes ORDER BY id DESC").fetchall()
    if not rows:
        st.info("Todavía no hay cotizaciones guardadas.")
    else:
        st.dataframe([{"N.º":r[0],"Creada":r[1],"Cliente":r[2],"Vehículo":r[3],"Recogida":r[4],"Devolución":r[5],"Total":money(r[6],r[7]),"Idioma":r[8]} for r in rows], use_container_width=True)
        selected_id = st.selectbox("Selecciona una cotización para descargar", [r[0] for r in rows])
        with db() as con:
            r=con.execute("SELECT id,created,customer,email,phone,vehicle,plate,pickup,dropoff,start,end,days,currency,daily_rate,rental,late_days,late_fee,deposit,insurance,total,language,notes,actual_return FROM quotes WHERE id=?",(selected_id,)).fetchone()
        if r:
            keys=["id","created","customer","email","phone","vehicle","plate","pickup","dropoff","start","end","days","currency","daily_rate","rental","late_days","late_fee","deposit","insurance","total","language","notes","actual_return"]
            q=dict(zip(keys,r))
            st.download_button("📄 Descargar PDF", data=create_pdf(q), file_name=f"El_Rey_Cotizacion_{selected_id}.pdf", mime="application/pdf")

st.markdown("---")
st.caption("EL REY RENT A CAR COSTA RICA · Herramienta administrativa inicial. Verifica tarifas, impuestos, seguros y condiciones antes de entregar cotizaciones a clientes.")
