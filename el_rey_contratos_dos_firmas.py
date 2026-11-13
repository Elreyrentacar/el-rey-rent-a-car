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
    mensaje = str(exc)
    if "23P01" in mensaje or "rey_reservas_sin_duplicados" in mensaje:
        st.error(
            "⛔ Este vehículo ya tiene una reserva confirmada "
            "en las fechas seleccionadas. Elige otro vehículo "
            "o cambia las fechas."
        )
    else:
        st.error(
            "No se pudo completar la operación. "
            "Verifica la conexión con la base de datos."
        )
        st.caption(mensaje)


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
    """Cotización PDF premium, con tablas adaptables y cuatro idiomas."""
    from reportlab.lib.utils import ImageReader

    t = I18N[q["language"]]
    buf = io.BytesIO()
    navy = colors.HexColor("#14223B")
    red = colors.HexColor("#C52F43")
    blue = colors.HexColor("#2563A6")
    pale = colors.HexColor("#F3F6FA")
    muted = colors.HexColor("#58667B")
    white = colors.white
    width = 7.25 * inch

    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=45, rightMargin=45,
        topMargin=19, bottomMargin=19,
        title=f'EL REY RENT A CAR - {t["quote"]} #{q["id"]}',
        author="EL REY RENT A CAR COSTA RICA",
    )
    styles = getSampleStyleSheet()
    definitions = [
        ("ReyBrand", "Helvetica-Bold", 16, 19, navy, TA_CENTER),
        ("ReySubtitle", "Helvetica", 8, 10, muted, TA_CENTER),
        ("ReyTitle", "Helvetica-Bold", 11, 14, red, TA_LEFT),
        ("ReySection", "Helvetica-Bold", 9, 11, navy, TA_LEFT),
        ("ReyLabel", "Helvetica-Bold", 7.5, 9, muted, TA_LEFT),
        ("ReyValue", "Helvetica", 8.5, 11, navy, TA_LEFT),
        ("ReyPrice", "Helvetica", 8.5, 11, navy, 2),
        ("ReyTotalLabel", "Helvetica-Bold", 11, 16, white, TA_LEFT),
        ("ReyTotalValue", "Helvetica-Bold", 16, 20, white, 2),
        ("ReyTerms", "Helvetica", 7.5, 10, navy, TA_LEFT),
    ]
    for name, font, size, leading, color, align in definitions:
        styles.add(ParagraphStyle(
            name=name, fontName=font, fontSize=size, leading=leading,
            textColor=color, alignment=align, wordWrap="CJK",
        ))

    def p(value, style="ReyValue"):
        value = "—" if value is None or value == "" else value
        return Paragraph(escape(str(value)), styles[style])

    def localized(es, en, pt, fr):
        return {"Español": es, "English": en,
                "Português": pt, "Français": fr}[q["language"]]

    def field(label, value):
        return [p(label, "ReyLabel"), Spacer(1, 1), p(value)]

    def section(label):
        return Paragraph(escape(label), styles["ReySection"])

    def styled_table(rows, col_widths, backgrounds=True):
        table = Table(rows, colWidths=col_widths, hAlign="CENTER")
        rules = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 11),
            ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if backgrounds:
            rules.append(("ROWBACKGROUNDS", (0, 0), (-1, -1),
                          [pale, white]))
        table.setStyle(TableStyle(rules))
        return table

    story = []
    if os.path.isfile(LOGO_PATH):
        try:
            iw, ih = ImageReader(LOGO_PATH).getSize()
            scale = min(2.0 * inch / iw, 1.12 * inch / ih)
            logo = Image(LOGO_PATH, width=iw * scale, height=ih * scale)
            logo.hAlign = "CENTER"
            story.extend([logo, Spacer(1, 3)])
        except Exception:
            pass

    story.extend([
        Paragraph("EL REY RENT A CAR", styles["ReyBrand"]),
        Paragraph("COSTA RICA", styles["ReySubtitle"]),
        Spacer(1, 3),
    ])
    accent = Table([[""]], colWidths=[width], rowHeights=[3])
    accent.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), red),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([accent, Spacer(1, 3),
                  Paragraph(escape(t["title"]), styles["ReyTitle"]),
                  Spacer(1, 3)])

    story.append(styled_table([[
        field(t["quote"], f'#{q["id"]}'),
        field(t["generated"], q["created"]),
    ]], [width / 2, width / 2]))

    story.extend([Spacer(1, 3), section(localized(
        "CLIENTE Y VEHÍCULO", "CUSTOMER AND VEHICLE",
        "CLIENTE E VEÍCULO", "CLIENT ET VÉHICULE")), Spacer(1, 3)])
    story.append(styled_table([
        [field(t["customer"], q["customer"]), field(t["vehicle"], q["vehicle"])],
        [field(localized("Teléfono", "Phone", "Telefone", "Téléphone"),
               q.get("phone")), field(t["plate"], q.get("plate"))],
        [field(localized("Correo", "Email", "E-mail", "E-mail"),
               q.get("email")), field(t["insurance"], q["insurance"])],
    ], [width / 2, width / 2]))

    story.extend([Spacer(1, 3), section(localized(
        "DETALLES DEL ALQUILER", "RENTAL DETAILS",
        "DETALHES DO ALUGUEL", "DÉTAILS DE LOCATION")), Spacer(1, 3)])
    story.append(styled_table([
        [field(t["pickup"], q["start"]), field(t["return"], q["end"])],
        [field(localized("Lugar de recogida", "Pick-up location",
                         "Local de retirada", "Lieu de prise en charge"), q["pickup"]),
         field(localized("Lugar de devolución", "Return location",
                         "Local de devolução", "Lieu de retour"), q["dropoff"])],
        [field(t["days"], q["days"]), field(t["currency"], q["currency"])],
    ], [width / 2, width / 2]))

    story.extend([Spacer(1, 3), section(localized(
        "RESUMEN DE PRECIOS", "PRICE SUMMARY",
        "RESUMO DOS PREÇOS", "RÉCAPITULATIF DES PRIX")), Spacer(1, 3)])
    price_rows = [
        [p(t["daily"]), p(money(q["daily_rate"], q["currency"]), "ReyPrice")],
        [p(t["rental"]), p(money(q["rental"], q["currency"]), "ReyPrice")],
        [p(t["late"]), p(money(q["late_fee"], q["currency"]), "ReyPrice")],
    ]
    story.append(styled_table(price_rows, [width * .68, width * .32]))
    total = Table([[
        p(t["total"], "ReyTotalLabel"),
        p(money(q["total"], q["currency"]), "ReyTotalValue"),
    ]], colWidths=[width * .68, width * .32])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), navy),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([total, Spacer(1, 3)])
    story.append(p(f'{t["deposit"]}: {money(q["deposit"], q["currency"])}',
                   "ReyTerms"))
    story.append(p(localized(
        "El depósito se indica por separado y no se suma al alquiler.",
        "The security deposit is shown separately and is not added to the rental.",
        "O depósito é apresentado separadamente e não é somado ao aluguel.",
        "Le dépôt de garantie est indiqué séparément et ne s'ajoute pas à la location."),
        "ReyTerms"))

    if q.get("actual_return"):
        story.extend([Spacer(1, 3), section(localized(
            "DEVOLUCIÓN REGISTRADA", "RECORDED RETURN",
            "DEVOLUÇÃO REGISTRADA", "RETOUR ENREGISTRÉ"))])
        story.append(p(
            f'{q["actual_return"]}  |  '
            f'{localized("Días adicionales", "Additional days", "Dias adicionais", "Jours supplémentaires")}: '
            f'{q["late_days"]}', "ReyTerms"))

    story.extend([Spacer(1, 3), section(t["terms"]), Spacer(1, 3),
                  p("• " + t["term1"], "ReyTerms"), Spacer(1, 3),
                  p("• " + t["term2"], "ReyTerms")])
    if q.get("notes"):
        story.extend([Spacer(1, 3), section(localized(
            "NOTAS", "NOTES", "OBSERVAÇÕES", "NOTES")),
            p(q["notes"], "ReyTerms")])

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def pdf_quote(r):
    return dict(id=r["id"],created=str(r["creado_en"])[:16].replace("T"," "),customer=r["cliente"],email=r.get("email"),phone=r.get("telefono"),vehicle=r["vehiculo"],plate=r.get("placa"),pickup=r["recogida"],dropoff=r["devolucion"],start=r["inicio"],end=r["fin"],days=r["dias"],currency=r["moneda"],daily_rate=safe_float(r["tarifa_diaria"]),rental=safe_float(r["subtotal"]),late_days=r["dias_extra"],late_fee=safe_float(r["recargo"]),deposit=safe_float(r["deposito"]),insurance=r["seguro"],total=safe_float(r["total"]),language=r["idioma"],notes=r.get("notas") or "",actual_return=r.get("devolucion_real"))



def crear_comprobante_reserva(reserva, idioma="Español", abono=0.0):
    """Comprobante premium. El abono se informa para este PDF; no se guarda en Supabase."""
    textos = {
        "Español": ["COMPROBANTE DE RESERVA", "Reserva", "Estado", "Cliente", "Teléfono / WhatsApp", "Correo electrónico", "Vehículo", "Recogida", "Devolución", "Lugar de recogida", "Lugar de devolución", "Días de alquiler", "Tarifa diaria", "TOTAL DEL ALQUILER", "Información importante", "Una reserva pendiente no constituye una confirmación. La disponibilidad y los detalles deben ser confirmados por la empresa.", "La devolución posterior a la hora acordada genera un cargo de un día adicional, sin horas de cortesía.", "Documento informativo generado por EL REY RENT A CAR COSTA RICA.", {"pendiente":"PENDIENTE", "confirmada":"CONFIRMADA", "en curso":"EN CURSO", "finalizada":"FINALIZADA", "cancelada":"CANCELADA"}],
        "English": ["BOOKING VOUCHER", "Booking", "Status", "Customer", "Phone / WhatsApp", "Email", "Vehicle", "Pick-up", "Return", "Pick-up location", "Return location", "Rental days", "Daily rate", "TOTAL RENTAL", "Important information", "A pending booking is not a confirmation. Availability and details must be confirmed by the company.", "Returns after the agreed time incur an additional full-day charge, with no grace period.", "Information document issued by EL REY RENT A CAR COSTA RICA.", {"pendiente":"PENDING", "confirmada":"CONFIRMED", "en curso":"IN PROGRESS", "finalizada":"COMPLETED", "cancelada":"CANCELLED"}],
        "Português": ["COMPROVANTE DE RESERVA", "Reserva", "Estado", "Cliente", "Telefone / WhatsApp", "E-mail", "Veículo", "Retirada", "Devolução", "Local de retirada", "Local de devolução", "Dias de aluguel", "Tarifa diária", "TOTAL DO ALUGUEL", "Informações importantes", "Uma reserva pendente não constitui confirmação. A disponibilidade e os detalhes devem ser confirmados pela empresa.", "A devolução após o horário combinado gera cobrança de um dia adicional, sem tolerância.", "Documento informativo emitido por EL REY RENT A CAR COSTA RICA.", {"pendiente":"PENDENTE", "confirmada":"CONFIRMADA", "en curso":"EM ANDAMENTO", "finalizada":"CONCLUÍDA", "cancelada":"CANCELADA"}],
        "Français": ["BON DE RÉSERVATION", "Réservation", "Statut", "Client", "Téléphone / WhatsApp", "E-mail", "Véhicule", "Prise en charge", "Retour", "Lieu de prise en charge", "Lieu de retour", "Jours de location", "Tarif journalier", "TOTAL LOCATION", "Informations importantes", "Une réservation en attente ne constitue pas une confirmation. La disponibilité et les détails doivent être confirmés par l'entreprise.", "Tout retour après l'heure convenue entraîne la facturation d'une journée supplémentaire, sans délai de grâce.", "Document informatif émis par EL REY RENT A CAR COSTA RICA.", {"pendiente":"EN ATTENTE", "confirmada":"CONFIRMÉE", "en curso":"EN COURS", "finalizada":"TERMINÉE", "cancelada":"ANNULÉE"}],
    }
    extras = {
        "Español": ["ABONO RECIBIDO", "SALDO PENDIENTE", "Firma del cliente", "Nombre completo", "Fecha", "Detalle de pagos (informativo)"],
        "English": ["PAYMENT RECEIVED", "BALANCE DUE", "Customer signature", "Full name", "Date", "Payment details (informational)"],
        "Português": ["PAGAMENTO RECEBIDO", "SALDO PENDENTE", "Assinatura do cliente", "Nome completo", "Data", "Detalhes de pagamento (informativo)"],
        "Français": ["ACOMPTE REÇU", "SOLDE RESTANT", "Signature du client", "Nom complet", "Date", "Détail des paiements (informatif)"],
    }
    t = textos.get(idioma, textos["Español"])
    x = extras.get(idioma, extras["Español"])
    buf = io.BytesIO()
    navy = colors.HexColor("#14223B")
    red = colors.HexColor("#C52F43")
    pale = colors.HexColor("#F3F6FA")
    muted = colors.HexColor("#58667B")
    width = 7.25 * inch
    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=45, rightMargin=45,
        topMargin=18, bottomMargin=18,
        title=f'EL REY RENT A CAR - {t[0]} #{reserva["id"]}'
    )
    stl = getSampleStyleSheet()
    for name, font, size, leading, color, alignment in [
        ("VoucherBrand", "Helvetica-Bold", 17, 20, navy, TA_CENTER),
        ("VoucherSub", "Helvetica", 9, 12, muted, TA_CENTER),
        ("VoucherTitle", "Helvetica-Bold", 12, 16, red, TA_LEFT),
        ("VoucherLabel", "Helvetica-Bold", 8.3, 11, navy, TA_LEFT),
        ("VoucherValue", "Helvetica", 8.3, 11, navy, TA_LEFT),
        ("VoucherTotal", "Helvetica-Bold", 12, 16, colors.white, TA_LEFT),
        ("VoucherNote", "Helvetica", 7.5, 10, navy, TA_LEFT),
        ("VoucherNumber", "Helvetica-Bold", 19, 23, navy, TA_CENTER),
        ("VoucherNumberLabel", "Helvetica-Bold", 9, 13, red, TA_CENTER),
    ]:
        stl.add(ParagraphStyle(name=name, fontName=font, fontSize=size,
                               leading=leading, textColor=color,
                               alignment=alignment, wordWrap="CJK"))
    def par(value, style="VoucherValue"):
        return Paragraph(escape(str(value if value not in (None, "") else "—")), stl[style])
    def fmt_date(value):
        return str(value or "—")[:16].replace("T", " ")
    inicio = datetime.fromisoformat(str(reserva["inicio"]).replace("Z", "+00:00"))
    fin = datetime.fromisoformat(str(reserva["fin"]).replace("Z", "+00:00"))
    dias = max(1, math.ceil((fin - inicio).total_seconds() / 86400))
    estado = str(reserva.get("estado") or "pendiente").lower()
    total_valor = safe_float(reserva.get("total"))
    abono = max(0.0, min(safe_float(abono), total_valor))
    saldo = max(0.0, round(total_valor - abono, 2))
    story = []
    if os.path.isfile(LOGO_PATH):
        try:
            from reportlab.lib.utils import ImageReader
            image_width, image_height = ImageReader(LOGO_PATH).getSize()
            max_w, max_h = 2.35 * inch, 1.25 * inch
            scale = min(max_w / image_width, max_h / image_height)
            logo = Image(LOGO_PATH, width=image_width * scale,
                         height=image_height * scale)
            logo.hAlign = "CENTER"
            story.extend([logo, Spacer(1, 4)])
        except Exception:
            pass
    story.extend([
        Paragraph("EL REY RENT A CAR", stl["VoucherBrand"]),
        Paragraph("COSTA RICA", stl["VoucherSub"]),
        Spacer(1, 5)
    ])
    headline = Table([[
        par(t[0], "VoucherTitle"),
        [par(t[1].upper(), "VoucherNumberLabel"),
         par(f'#{int(reserva["id"]):05d}', "VoucherNumber")]
    ]], colWidths=[4.7*inch, 2.55*inch])
    headline.setStyle(TableStyle([
        ("BACKGROUND", (1,0), (1,0), pale),
        ("LINEBELOW", (0,0), (-1,-1), 2, red),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 10)
    ]))
    story.extend([headline, Spacer(1, 7)])
    fields = [
        (t[2], t[18].get(estado, estado.upper())),
        (t[3], reserva.get("cliente")),
        (t[4], reserva.get("telefono")),
        (t[5], reserva.get("correo")),
        (t[6], reserva.get("vehiculo")),
        (t[7], fmt_date(reserva.get("inicio"))),
        (t[8], fmt_date(reserva.get("fin"))),
        (t[9], reserva.get("lugar_recogida")),
        (t[10], reserva.get("lugar_devolucion")),
        (t[11], dias),
        (t[12], money(safe_float(reserva.get("tarifa_diaria")))),
    ]
    table = Table([[par(k, "VoucherLabel"), par(v)] for k, v in fields],
                  colWidths=[2.15*inch, 5.1*inch], hAlign="CENTER")
    table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [pale, colors.white]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.extend([table, Spacer(1, 5)])
    total = Table([[
        par(t[13], "VoucherTotal"),
        par(money(total_valor), "VoucherTotal")
    ]], colWidths=[4.4*inch, 2.85*inch])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), navy),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.extend([total, Spacer(1, 5)])
    payments = Table([
        [par(x[0], "VoucherLabel"), par(money(abono))],
        [par(x[1], "VoucherLabel"), par(money(saldo))],
    ], colWidths=[4.4*inch, 2.85*inch])
    payments.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [pale, colors.white]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.extend([payments, Spacer(1, 6)])
    story.extend([
        par(x[2], "VoucherLabel"),
        Spacer(1, 13),
    ])
    signature = Table([["", ""]], colWidths=[4.65*inch, 2.6*inch],
                      rowHeights=[1])
    signature.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), .8, navy),
    ]))
    story.extend([
        signature,
        Table([[par(x[3], "VoucherNote"), par(x[4], "VoucherNote")]],
              colWidths=[4.65*inch, 2.6*inch]),
        Spacer(1, 6),
        par(t[14], "VoucherLabel"), Spacer(1, 4),
        par(t[15], "VoucherNote"), Spacer(1, 3),
        par(t[16], "VoucherNote"), Spacer(1, 6),
        par(t[17], "VoucherNote")
    ])
    doc.build(story)
    return buf.getvalue()



# ─── CONTRATOS DE ALQUILER (módulo integrado) ──────────────────────────
def crear_contrato_pdf(reserva, idioma="Español", firma_bytes=None,
                       conductor="", identificacion="", licencia="",
                       deposito=0.0, seguro="Según acuerdo", condiciones="", firma_representante_bytes=None):
    """Genera contrato imprimible o con imagen de firma, sin alterar Supabase."""
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import KeepTogether
    textos = {
        "Español": ["CONTRATO DE ALQUILER DE VEHÍCULO", "Contrato asociado a reserva", "DATOS DEL CLIENTE Y CONDUCTOR", "Cliente", "Conductor", "Identificación / pasaporte", "Licencia de conducir", "Teléfono", "Correo", "DATOS DEL VEHÍCULO Y ALQUILER", "Vehículo", "Recogida", "Devolución pactada", "Lugar de recogida", "Lugar de devolución", "Tarifa diaria", "Total estimado", "Depósito de garantía (separado)", "Seguro", "CONDICIONES GENERALES", "El cliente se compromete a devolver el vehículo en la fecha y hora acordadas y en condiciones conformes al acta de entrega.", "No hay horas de cortesía: cualquier devolución posterior a la hora pactada genera el cobro de un día adicional completo por cada período de hasta 24 horas de retraso.", "Los daños, combustible, multas, deducibles y demás cargos se regirán por las condiciones y coberturas expresamente acordadas y la legislación aplicable.", "Este documento debe revisarse y completarse antes de su firma; la reserva y la cotización no sustituyen la entrega efectiva del vehículo.", "Firma del cliente", "Firma del representante", "Fecha", "Condiciones adicionales"],
        "English": ["VEHICLE RENTAL AGREEMENT", "Agreement linked to booking", "CUSTOMER AND DRIVER", "Customer", "Driver", "ID / passport", "Driver's license", "Phone", "Email", "VEHICLE AND RENTAL DETAILS", "Vehicle", "Pick-up", "Agreed return", "Pick-up location", "Return location", "Daily rate", "Estimated total", "Security deposit (separate)", "Insurance", "GENERAL TERMS", "The customer agrees to return the vehicle at the agreed date and time and in accordance with the vehicle handover record.", "No grace period applies: any return after the agreed time incurs an additional full-day charge for each period of up to 24 hours of delay.", "Damage, fuel, fines, deductibles and other charges are governed by the expressly agreed terms and coverages and applicable law.", "This document must be reviewed and completed before signing; the booking and quotation do not replace actual vehicle handover.", "Customer signature", "Company representative signature", "Date", "Additional terms"],
        "Português": ["CONTRATO DE ALUGUEL DE VEÍCULO", "Contrato vinculado à reserva", "CLIENTE E CONDUTOR", "Cliente", "Condutor", "Documento / passaporte", "Carteira de habilitação", "Telefone", "E-mail", "VEÍCULO E LOCAÇÃO", "Veículo", "Retirada", "Devolução combinada", "Local de retirada", "Local de devolução", "Tarifa diária", "Total estimado", "Depósito de garantia (separado)", "Seguro", "CONDIÇÕES GERAIS", "O cliente concorda em devolver o veículo na data e hora combinadas e conforme o registro de entrega.", "Não há tolerância: qualquer devolução após o horário combinado gera cobrança de um dia adicional completo por cada período de até 24 horas de atraso.", "Danos, combustível, multas, franquias e outras cobranças seguem as condições e coberturas expressamente acordadas e a legislação aplicável.", "Este documento deve ser revisado e preenchido antes da assinatura; a reserva e a cotação não substituem a entrega efetiva do veículo.", "Assinatura do cliente", "Assinatura do representante", "Data", "Condições adicionais"],
        "Français": ["CONTRAT DE LOCATION DE VÉHICULE", "Contrat lié à la réservation", "CLIENT ET CONDUCTEUR", "Client", "Conducteur", "Pièce d'identité / passeport", "Permis de conduire", "Téléphone", "E-mail", "VÉHICULE ET LOCATION", "Véhicule", "Prise en charge", "Retour convenu", "Lieu de prise en charge", "Lieu de retour", "Tarif journalier", "Total estimé", "Dépôt de garantie (séparé)", "Assurance", "CONDITIONS GÉNÉRALES", "Le client s'engage à restituer le véhicule à la date et à l'heure convenues, conformément à l'état des lieux de remise.", "Aucun délai de grâce : tout retour après l'heure convenue entraîne la facturation d'une journée entière supplémentaire pour chaque période de retard allant jusqu'à 24 heures.", "Les dommages, le carburant, les amendes, les franchises et autres frais sont régis par les conditions et garanties expressément convenues et la législation applicable.", "Ce document doit être relu et complété avant signature ; la réservation et le devis ne remplacent pas la remise effective du véhicule.", "Signature du client", "Signature du représentant", "Date", "Conditions supplémentaires"],
    }
    t = textos[idioma]
    buf = io.BytesIO()
    navy = colors.HexColor("#14223B")
    red = colors.HexColor("#C52F43")
    pale = colors.HexColor("#F3F6FA")
    styles = getSampleStyleSheet()
    for name, font, size, leading, color in [
        ("ContractTitle", "Helvetica-Bold", 13, 17, navy),
        ("ContractHead", "Helvetica-Bold", 9, 12, red),
        ("ContractLabel", "Helvetica-Bold", 8, 11, navy),
        ("ContractText", "Helvetica", 8.2, 12, navy),
        ("ContractSmall", "Helvetica", 7.5, 11, navy),
    ]:
        styles.add(ParagraphStyle(name=name, fontName=font, fontSize=size,
                                  leading=leading, textColor=color, spaceAfter=3))
    def par(x, sty="ContractText"):
        return Paragraph(escape(str(x if x not in (None, "") else "—")), styles[sty])
    def heading(x):
        return par(x, "ContractHead")
    def table(rows):
        tab = Table([[par(k,"ContractLabel"),par(v)] for k,v in rows],
                    colWidths=[2.15*inch, 5.1*inch], repeatRows=0)
        tab.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[pale,colors.white]),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),9),
            ("RIGHTPADDING",(0,0),(-1,-1),9),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return tab
    story=[]
    if os.path.isfile(LOGO_PATH):
        try:
            w,h=ImageReader(LOGO_PATH).getSize()
            ratio=min(1.15*inch/w,0.68*inch/h)
            img=Image(LOGO_PATH,width=w*ratio,height=h*ratio)
            img.hAlign="CENTER"
            story.append(img)
        except Exception:
            pass
    story += [par("EL REY RENT A CAR · COSTA RICA", "ContractTitle"),
              heading(t[0]), par(f'{t[1]} #{reserva["id"]}'), Spacer(1,8),
              heading(t[2]), table([
                  (t[3],reserva.get("cliente")),
                  (t[4],conductor or reserva.get("cliente")),
                  (t[5],identificacion), (t[6],licencia),
                  (t[7],reserva.get("telefono")),(t[8],reserva.get("correo"))]),
              Spacer(1,9), heading(t[9]), table([
                  (t[10],reserva.get("vehiculo")),
                  (t[11],str(reserva.get("inicio",""))[:16].replace("T"," ")),
                  (t[12],str(reserva.get("fin",""))[:16].replace("T"," ")),
                  (t[13],reserva.get("lugar_recogida")),
                  (t[14],reserva.get("lugar_devolucion")),
                  (t[15],money(safe_float(reserva.get("tarifa_diaria")))),
                  (t[16],money(safe_float(reserva.get("total")))),
                  (t[17],money(deposito)),(t[18],seguro)]),
              Spacer(1,9),heading(t[19])]
    for clause in t[20:24]:
        story.append(par("• " + clause,"ContractSmall"))
    if condiciones.strip():
        story += [heading(t[27]),par(condiciones,"ContractSmall")]
    story.append(Spacer(1,14))
    def firma_celda(datos):
        if not datos:
            return Spacer(1, 38)
        try:
            from PIL import Image as PILImage
            foto = PILImage.open(io.BytesIO(datos))
            foto.load()
            ancho, alto = foto.size
            if ancho <= 0 or alto <= 0:
                return Spacer(1, 38)
            escala = min((2.7*inch)/ancho, (.8*inch)/alto)
            return Image(io.BytesIO(datos), width=ancho*escala,
                         height=alto*escala)
        except Exception:
            return Spacer(1, 38)
    sig=Table([
        [par(t[24],"ContractLabel"),par(t[25],"ContractLabel")],
        [firma_celda(firma_bytes), firma_celda(firma_representante_bytes)],
        [par("____________________________"),par("____________________________")],
        [par(t[26]+": __________________"),par(t[26]+": __________________")]
    ], colWidths=[3.625*inch,3.625*inch])
    sig.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"BOTTOM"),
                             ("TOPPADDING",(0,0),(-1,-1),4)]))
    story.append(KeepTogether(sig))
    doc=SimpleDocTemplate(buf,pagesize=letter,leftMargin=45,rightMargin=45,
                          topMargin=28,bottomMargin=30,
                          title=f'EL REY RENT A CAR - Contrato #{reserva["id"]}')
    doc.build(story)
    return buf.getvalue()


def pantalla_contratos():
    st.subheader("📑 Contratos de alquiler")
    st.caption("Genera contratos en cuatro idiomas, para firma en papel o con una firma dibujada.")
    reservas = query("rey_reservas", order="id", desc=True)
    validas = [r for r in reservas if str(r.get("estado") or "").lower() in ("confirmada","en curso","finalizada")]
    if not validas:
        st.info("Primero confirma una reserva en el menú Reservas para preparar su contrato.")
        return
    opciones = {f'#{r["id"]} · {r["cliente"]} · {r["vehiculo"]}':r for r in validas}
    reserva = opciones[st.selectbox("Reserva para el contrato",list(opciones))]
    idioma = st.selectbox("🌎 Idioma del contrato",["Español","English","Português","Français"])
    conductor = st.text_input("Nombre completo del conductor",value=reserva.get("cliente") or "")
    identificacion = st.text_input("Identificación o pasaporte")
    licencia = st.text_input("Número de licencia de conducir")
    deposito = st.number_input("Depósito de garantía (USD)",min_value=0.0,value=0.0)
    seguro = st.text_input("Seguro y cobertura acordada",value="Según acuerdo")
    condiciones = st.text_area("Condiciones adicionales acordadas (opcional)")
    modo = st.radio("Tipo de firma", ["🖨️ Imprimir y firmar en papel", "✍️ Firmar ambos desde el celular"])
    firma_bytes = None
    firma_representante_bytes = None
    if modo.startswith("✍️"):
        st.info("Cada persona firma en su propio espacio. También puedes subir una imagen PNG o JPG de cada firma.")
        def obtener_firma(etiqueta, clave):
            st.markdown("**" + etiqueta + "**")
            datos = None
            try:
                from streamlit_drawable_canvas import st_canvas
                resultado = st_canvas(fill_color="rgba(255,255,255,1)",
                                      stroke_width=3, stroke_color="#14223B",
                                      background_color="#FFFFFF", height=170,
                                      width=320, drawing_mode="freedraw",
                                      key=f"{clave}_{reserva['id']}")
                if resultado is not None and resultado.image_data is not None:
                    from PIL import Image as PILImage, ImageChops
                    imagen = PILImage.fromarray(resultado.image_data.astype("uint8")).convert("RGB")
                    diferencia = ImageChops.difference(imagen, PILImage.new("RGB", imagen.size, "white"))
                    if diferencia.getbbox() is not None:
                        memoria = io.BytesIO()
                        imagen.save(memoria, format="PNG")
                        datos = memoria.getvalue()
            except Exception:
                st.caption("Si el panel no procesa la firma, puedes subirla como imagen.")
            subida = st.file_uploader("Subir firma (PNG o JPG) — " + etiqueta,
                                      type=["png", "jpg", "jpeg"], key="subir_"+clave)
            if subida is not None:
                datos = subida.getvalue()
            return datos
        firma_bytes = obtener_firma("Firma del cliente", "cliente_firma")
        firma_representante_bytes = obtener_firma("Firma del representante", "representante_firma")
    st.warning("Revisa los datos, las coberturas y las condiciones con el cliente antes de firmar. Este es un modelo operativo, no una revisión legal.")
    if modo.startswith("✍️") and (not firma_bytes or not firma_representante_bytes):
        st.warning("Una o ambas firmas están pendientes. Puedes descargar el contrato con las firmas disponibles o imprimirlo para completarlo después.")
    try:
        pdf = crear_contrato_pdf(reserva, idioma, firma_bytes, conductor,
                                 identificacion, licencia, deposito, seguro, condiciones,
                                 firma_representante_bytes=firma_representante_bytes)
        st.download_button("📄 Descargar contrato PDF", data=pdf,
                           file_name=f'El_Rey_Contrato_Reserva_{reserva["id"]}.pdf',
                           mime="application/pdf", type="primary")
    except Exception as exc:
        st.error(f"No se pudo generar el contrato PDF: {exc}")
    st.caption("Los contratos se pueden regenerar desde las reservas guardadas. Las firmas y los datos adicionales de este formulario todavía no se almacenan en Supabase: descarga y conserva el PDF firmado.")

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
    page = st.radio("MENÚ", ["Inicio", "Nueva cotización", "Reservas", "Devoluciones", "Vehículos y tarifas", "Historial", "Contratos"])

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

        # Calendario de disponibilidad: consulta las reservas existentes en Supabase.
        # No modifica reservas ni sustituye la validación al confirmar.
        st.subheader("🗓️ Calendario de disponibilidad")
        st.caption("🔴 Ocupado: confirmada/en curso · 🟡 Solicitud pendiente · 🟢 Disponible · ⚪ Inactivo")
        cal_a, cal_b = st.columns(2)
        fecha_cal = cal_a.date_input("Desde", value=date.today(), key="cal_desde")
        dias_cal = cal_b.selectbox("Mostrar días", [7, 14, 30], index=1, key="cal_dias")

        def estado_en_dia(vehiculo_id, dia):
            # Un día está ocupado si alguna parte de la reserva coincide con él.
            inicio_dia = datetime.combine(dia, time.min)
            fin_dia = inicio_dia + timedelta(days=1)
            estados = set()
            for reserva in reservas:
                if str(reserva.get("vehiculo_id")) != str(vehiculo_id):
                    continue
                if (fecha_reserva(reserva["inicio"]) < fin_dia
                        and fecha_reserva(reserva["fin"]) > inicio_dia):
                    estados.add(str(reserva.get("estado") or "").lower())
            if estados.intersection({"confirmada", "en curso"}):
                return "🔴"
            if "pendiente" in estados:
                return "🟡"
            return "🟢"

        dias_visibles = [fecha_cal + timedelta(days=i) for i in range(dias_cal)]
        filas_cal = []
        for v in vehiculos:
            fila = {"Vehículo": f'{v["modelo"]} · #{v["id"]}'}
            for dia in dias_visibles:
                fila[dia.strftime("%d/%m")] = (
                    estado_en_dia(v["id"], dia) if v.get("activo") else "⚪"
                )
            filas_cal.append(fila)
        if filas_cal:
            st.dataframe(filas_cal, hide_index=True, use_container_width=True,
                         height=min(420, 55 + len(filas_cal) * 36))
            st.caption("Desliza la tabla horizontalmente para ver más fechas. "
                       "El día de recogida y el de devolución se marcan cuando "
                       "la reserva ocupa alguna parte de ese día.")
        else:
            st.info("Agrega vehículos para consultar su disponibilidad.")

        st.subheader("🔎 Buscar vehículos disponibles")
        st.caption("Consulta toda la flota para un período exacto. Los precios son estimados en USD y no incluyen cargos adicionales.")
        with st.form("buscar_toda_flota"):
            busca_a, busca_b = st.columns(2)
            busca_fecha_ini = busca_a.date_input("Fecha de recogida", date.today(), key="busca_fecha_ini")
            busca_hora_ini = busca_a.time_input("Hora de recogida", time(8, 0), key="busca_hora_ini")
            busca_fecha_fin = busca_b.date_input("Fecha de devolución", date.today() + timedelta(days=1), key="busca_fecha_fin")
            busca_hora_fin = busca_b.time_input("Hora de devolución", time(8, 0), key="busca_hora_fin")
            buscar_flota = st.form_submit_button("🔍 Buscar en todos los vehículos", type="primary")

        if buscar_flota:
            st.session_state["busqueda_flota"] = (
                datetime.combine(busca_fecha_ini, busca_hora_ini).isoformat(),
                datetime.combine(busca_fecha_fin, busca_hora_fin).isoformat(),
            )
        if st.session_state.get("busqueda_flota"):
            inicio_busca = datetime.fromisoformat(st.session_state["busqueda_flota"][0])
            fin_busca = datetime.fromisoformat(st.session_state["busqueda_flota"][1])
            if fin_busca <= inicio_busca:
                st.error("La devolución debe ser posterior a la recogida.")
            else:
                dias_busca = math.ceil((fin_busca - inicio_busca).total_seconds() / 86400)
                st.caption(f"Período consultado: {dias_busca} día(s) de alquiler.")
                disponibles_busca = 0
                for v in vehiculos:
                    nombre_v = f'{v["modelo"]} · #{v["id"]}'
                    if not v.get("activo"):
                        st.write(f"⚪ **{nombre_v}** — Inactivo")
                        continue
                    choque_v = cruza_reserva(v["id"], inicio_busca, fin_busca)
                    if choque_v:
                        st.write(f'🔴 **{nombre_v}** — Ocupado (reserva #{choque_v["id"]})')
                        continue
                    pendientes_v = [r for r in reservas
                        if str(r.get("vehiculo_id")) == str(v["id"])
                        and str(r.get("estado") or "").lower() == "pendiente"
                        and inicio_busca < fecha_reserva(r["fin"])
                        and fin_busca > fecha_reserva(r["inicio"])]
                    disponibles_busca += 1
                    tarifa_v = safe_float(v["tarifa_diaria"])
                    aviso_v = f" · 🟡 {len(pendientes_v)} solicitud(es) pendiente(s)" if pendientes_v else ""
                    st.write(f"🟢 **{nombre_v}** — {money(tarifa_v)} / día · **Total estimado: {money(dias_busca * tarifa_v)}**{aviso_v}")
                    if st.button(f"➕ Preparar reserva de {v['modelo']} · #{v['id']}", key=f"preparar_{v['id']}"):
                        st.session_state["res_vehiculo_elegido"] = nombre_v
                        st.session_state["res_inicio"] = inicio_busca.date()
                        st.session_state["res_hinicio"] = inicio_busca.time()
                        st.session_state["res_fin"] = fin_busca.date()
                        st.session_state["res_hfin"] = fin_busca.time()
                        st.session_state["abrir_form_reserva"] = True
                        st.rerun()
                if not disponibles_busca:
                    st.warning("No hay vehículos activos disponibles para ese período.")
                else:
                    st.success(f"{disponibles_busca} vehículo(s) sin reservas confirmadas o en curso que se superpongan.")
                st.caption("La disponibilidad se verifica nuevamente al confirmar la reserva. Las solicitudes pendientes no bloquean automáticamente un vehículo.")

        with st.expander("🔎 Consultar un período exacto"):
            st.caption("La disponibilidad se calcula con fecha y hora exactas, "
                       "no solo por días del calendario.")
            opciones_cal = {f'{v["modelo"]} · #{v["id"]}': v for v in vehiculos if v.get("activo")}
            if opciones_cal:
                with st.form("consulta_disponibilidad"):
                    elegido_cal = opciones_cal[st.selectbox("Vehículo", list(opciones_cal), key="cal_vehiculo")]
                    c1, c2 = st.columns(2)
                    desde_fecha = c1.date_input("Recogida", date.today(), key="cal_fecha_ini")
                    desde_hora = c1.time_input("Hora de recogida", time(8, 0), key="cal_hora_ini")
                    hasta_fecha = c2.date_input("Devolución", date.today() + timedelta(days=1), key="cal_fecha_fin")
                    hasta_hora = c2.time_input("Hora de devolución", time(8, 0), key="cal_hora_fin")
                    consultar_cal = st.form_submit_button("Consultar disponibilidad")
                if consultar_cal:
                    inicio_cal = datetime.combine(desde_fecha, desde_hora)
                    fin_cal = datetime.combine(hasta_fecha, hasta_hora)
                    if fin_cal <= inicio_cal:
                        st.error("La devolución debe ser posterior a la recogida.")
                    else:
                        choque_cal = cruza_reserva(elegido_cal["id"], inicio_cal, fin_cal)
                        if choque_cal:
                            st.error(f'🔴 No disponible: coincide con la reserva #{choque_cal["id"]}.')
                        else:
                            pendientes_cal = [r for r in reservas
                                if str(r.get("vehiculo_id")) == str(elegido_cal["id"])
                                and str(r.get("estado") or "").lower() == "pendiente"
                                and inicio_cal < fecha_reserva(r["fin"])
                                and fin_cal > fecha_reserva(r["inicio"])]
                            st.success("🟢 Disponible: no hay reservas confirmadas o en curso que se superpongan.")
                            if pendientes_cal:
                                st.warning(f'🟡 Hay {len(pendientes_cal)} solicitud(es) pendiente(s) en este período.')
            else:
                st.info("No hay vehículos activos para consultar.")

        with st.expander("➕ Crear nueva reserva", expanded=not bool(reservas) or st.session_state.get("abrir_form_reserva", False)):
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
                    vehiculo = opciones[st.selectbox("Vehículo *", list(opciones), key="res_vehiculo_elegido")]
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
                    idioma_comprobante = st.selectbox(
                        "🌎 Idioma del comprobante PDF",
                        ["Español", "English", "Português", "Français"],
                        key=f'idioma_comprobante_{r["id"]}')
                    abono_pdf = st.number_input(
                        "💵 Abono recibido (USD) para este comprobante",
                        min_value=0.0,
                        max_value=max(0.0, safe_float(r["total"])),
                        value=0.0,
                        step=5.0,
                        key=f'abono_comprobante_{r["id"]}')
                    st.caption("Este abono se refleja únicamente en el PDF. No se guarda como pago en Supabase.")
                    st.download_button(
                        "📄 Descargar comprobante de reserva",
                        data=crear_comprobante_reserva(r, idioma_comprobante, abono_pdf),
                        file_name=f'El_Rey_Reserva_{r["id"]}.pdf',
                        mime="application/pdf",
                        key=f'pdf_reserva_{r["id"]}')

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
    elif page == "Contratos":
        pantalla_contratos()
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
