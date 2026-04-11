"""
SUSVI — Generador de PDF Ejecutivo (ReportLab)
=================================================
Genera el reporte PDF listo para presentar a comités de inversión.
Paleta corporativa SUSVI: azul #185FA5, verde #1D9E75, rojo #E24B4A.
"""
# Importamos os para manejo de rutas y datetime para la marca de tiempo del documento
import os
from datetime import datetime

# Intentamos importar ReportLab y marcamos su disponibilidad para el fallback de texto plano
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    # Marcamos como no disponible para que los métodos usen el fallback de texto plano
    REPORTLAB_AVAILABLE = False


# ── Paleta corporativa ────────────────────────────────────────────────────────
# Declaramos los colores corporativos de SUSVI como constantes de ReportLab
if REPORTLAB_AVAILABLE:
    C_BLUE = colors.HexColor("#185FA5")        # Azul corporativo principal
    C_BLUE_LIGHT = colors.HexColor("#E8F0FC")  # Azul claro para fondos de sección
    C_GREEN = colors.HexColor("#1D9E75")       # Verde para zonas óptimas y activos
    C_GREEN_LIGHT = colors.HexColor("#E6F7F0") # Verde claro para fondos de activos
    C_AMBER = colors.HexColor("#EF9F27")       # Ámbar para zonas de cautela
    C_AMBER_LIGHT = colors.HexColor("#FFF7E6") # Ámbar claro para fondos de advertencia
    C_RED = colors.HexColor("#E24B4A")         # Rojo para zonas críticas y alertas
    C_RED_LIGHT = colors.HexColor("#FCEBEB")   # Rojo claro para fondos de alerta
    C_GRAY_LIGHT = colors.HexColor("#F1EFE8")  # Gris claro para filas alternas de tablas
    C_GRAY_MID = colors.HexColor("#888780")    # Gris medio para textos secundarios
    C_GRAY_DARK = colors.HexColor("#4A5068")   # Gris oscuro para metadatos
    C_BLACK = colors.HexColor("#2C2C2A")       # Negro suave para cuerpo de texto
    C_WHITE = colors.white                     # Blanco para textos sobre fondos oscuros
else:
    # Asignamos None a todos los colores si ReportLab no está instalado
    C_BLUE = C_BLUE_LIGHT = C_GREEN = C_GREEN_LIGHT = C_AMBER = C_AMBER_LIGHT = None
    C_RED = C_RED_LIGHT = C_GRAY_LIGHT = C_GRAY_MID = C_GRAY_DARK = C_BLACK = C_WHITE = None


# Construimos y retornamos el diccionario de estilos de párrafo reutilizables del PDF
def _styles():
    # Tomamos los estilos base de ReportLab para heredar de ellos en los estilos personalizados
    base = getSampleStyleSheet()
    custom = {}
    # Estilo para el título principal del documento en azul corporativo
    custom["title"] = ParagraphStyle(
        "title", parent=base["Normal"],
        fontSize=22, textColor=C_BLUE, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    # Estilo para el subtítulo y descripción debajo del título
    custom["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"],
        fontSize=12, textColor=C_GRAY_MID, spaceAfter=16,
        fontName="Helvetica", alignment=TA_LEFT,
    )
    # Estilo para encabezados de sección en azul corporativo
    custom["section"] = ParagraphStyle(
        "section", parent=base["Normal"],
        fontSize=13, textColor=C_BLUE, spaceBefore=16, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    # Estilo alternativo para secciones de activos de campo en verde
    custom["section_alt"] = ParagraphStyle(
        "section_alt", parent=base["Normal"],
        fontSize=13, textColor=C_GREEN, spaceBefore=16, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    # Estilo para el cuerpo de texto estándar del documento
    custom["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=4,
        fontName="Helvetica", leading=14,
    )
    # Estilo para texto de cuerpo con énfasis en negrita
    custom["body_bold"] = ParagraphStyle(
        "body_bold", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=4,
        fontName="Helvetica-Bold", leading=14,
    )
    # Estilo para elementos de lista con sangría izquierda
    custom["bullet"] = ParagraphStyle(
        "bullet", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=3,
        fontName="Helvetica", leftIndent=16, leading=14,
    )
    # Estilo para etiquetas de KPI en celdas de tabla con fondo de color
    custom["kpi_label"] = ParagraphStyle(
        "kpi_label", parent=base["Normal"],
        fontSize=9, textColor=C_WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    # Estilo para valores numéricos grandes en las celdas de KPI
    custom["kpi_value"] = ParagraphStyle(
        "kpi_value", parent=base["Normal"],
        fontSize=24, textColor=C_WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=2,
    )
    # Estilo para metadatos y timestamps alineados a la derecha
    custom["small_gray"] = ParagraphStyle(
        "small_gray", parent=base["Normal"],
        fontSize=8, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_RIGHT,
    )
    # Estilo para notas de pie de página centradas
    custom["small_center"] = ParagraphStyle(
        "small_center", parent=base["Normal"],
        fontSize=8, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_CENTER,
    )
    # Estilo para texto de alerta en rojo con negrita
    custom["alert"] = ParagraphStyle(
        "alert", parent=base["Normal"],
        fontSize=10, textColor=C_RED, fontName="Helvetica-Bold",
        spaceAfter=4, leading=14,
    )
    # Estilo para la marca de agua y notas legales al pie del documento
    custom["watermark"] = ParagraphStyle(
        "watermark", parent=base["Normal"],
        fontSize=7, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_CENTER,
    )
    return custom


# Retornamos el color de acento correspondiente al score SSU para usarlo en tablas y textos
def _ssu_color(ssu):
    """Devuelve color de acuerdo al score SSU."""
    if ssu >= 75:
        return C_GREEN   # Zona óptima: verde
    if ssu >= 50:
        return C_AMBER   # Zona aceptable: ámbar
    if ssu >= 30:
        return C_RED     # Zona deficiente: rojo
    return colors.HexColor("#7B1C1C")  # Zona crítica: rojo oscuro


# Retornamos el color de fondo suave para la tarjeta SSU según el nivel de seguridad
def _ssu_bg_color(ssu):
    """Fondo suave para SSU."""
    if ssu >= 75:
        return C_GREEN_LIGHT   # Fondo verde claro para zonas óptimas
    if ssu >= 50:
        return C_AMBER_LIGHT   # Fondo ámbar claro para zonas aceptables
    if ssu >= 30:
        return C_RED_LIGHT     # Fondo rojo claro para zonas deficientes
    return C_RED_LIGHT         # Fondo rojo claro también para zonas críticas


# Declaramos la clase generadora de reportes PDF ejecutivos para la plataforma SUSVI
class SUSVIReportGenerator:
    """Generador de reportes PDF ejecutivos para SUSVI."""

    # Generamos el reporte ejecutivo genérico para análisis de inversión territorial
    def generate(self, data: dict, output_path: str) -> str:
        """Genera reporte ejecutivo genérico (inversión territorial)."""
        if not REPORTLAB_AVAILABLE:
            # Escribimos un archivo de texto plano como fallback si ReportLab no está instalado
            with open(output_path.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
                f.write("SUSVI — Reporte Ejecutivo\n")
                f.write("=" * 50 + "\n")
                f.write(data.get("resumen_ejecutivo", "") + "\n")
            return output_path.replace(".pdf", ".txt")

        # Cargamos los estilos de párrafo personalizados del documento
        styles = _styles()
        # Creamos el documento PDF con los márgenes corporativos estándar en formato A4
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        # Inicializamos la lista de elementos del documento que construimos secuencialmente
        story = []

        # ── Encabezado ────────────────────────────────────────────────────────
        # Agregamos el título principal y el subtítulo del análisis
        story.append(Paragraph("SUSVI", styles["title"]))
        story.append(Paragraph(
            data.get("titulo", "Reporte de Inteligencia Territorial"),
            styles["subtitle"]
        ))
        # Agregamos una línea horizontal azul corporativa como separador visual del encabezado
        story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=12))

        # Agregamos la marca de tiempo y el ID del análisis como metadato del documento
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        story.append(Paragraph(
            f"Generado: {ts} &nbsp;|&nbsp; Análisis ID: {data.get('analysis_id', 'demo')[:8]}",
            styles["small_gray"]
        ))
        story.append(Spacer(1, 12))

        # ── KPIs ──────────────────────────────────────────────────────────────
        # Extraemos los conteos de zonas por clasificación para la tabla de KPIs
        kpis = data.get("kpis", {})
        verdes = kpis.get("verdes", "—")
        cautela_n = kpis.get("cautela", "—")
        descarte_n = kpis.get("descarte", "—")

        # Construimos la tabla de tres celdas para los KPIs de zonas verdes, cautela y descarte
        kpi_data = [
            [
                Paragraph(f"🟢 {verdes}", styles["kpi_label"]),
                Paragraph(f"🟡 {cautela_n}", styles["kpi_label"]),
                Paragraph(f"🔴 {descarte_n}", styles["kpi_label"]),
            ],
            [
                Paragraph("Zonas Verdes", styles["kpi_label"]),
                Paragraph("Zonas Cautela", styles["kpi_label"]),
                Paragraph("Zonas Descarte", styles["kpi_label"]),
            ],
        ]
        # Aplicamos fondos de color corporativo a cada columna según su clasificación
        kpi_table = Table(kpi_data, colWidths=["33%", "33%", "34%"])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), C_GREEN),  # Verde para zonas viables
            ("BACKGROUND", (1, 0), (1, -1), C_AMBER),  # Ámbar para zonas de cautela
            ("BACKGROUND", (2, 0), (2, -1), C_RED),    # Rojo para zonas de descarte
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [None]),
            ("FONTSIZE", (0, 0), (-1, -1), 18),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, 0), 40),
            ("ROWHEIGHT", (0, 1), (-1, 1), 22),
            ("GRID", (0, 0), (-1, -1), 0.5, C_WHITE),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 16))

        # ── Resumen Ejecutivo ─────────────────────────────────────────────────
        # Agregamos la sección de resumen ejecutivo generado por el agente de negocio
        story.append(Paragraph("Resumen Ejecutivo", styles["section"]))
        story.append(Paragraph(data.get("resumen_ejecutivo", ""), styles["body"]))

        # ── Hallazgos Clave ───────────────────────────────────────────────────
        # Listamos cada hallazgo clave del análisis como viñeta si existen hallazgos
        hallazgos = data.get("hallazgos_clave", [])
        if hallazgos:
            story.append(Paragraph("Hallazgos Clave", styles["section"]))
            for h in hallazgos:
                story.append(Paragraph(f"• {h}", styles["bullet"]))

        # ── Top Zonas de Inversión ─────────────────────────────────────────────
        # Construimos la tabla de zonas prioritarias si el análisis las contiene
        top_zonas = data.get("top_zonas_inversion", [])
        if top_zonas:
            story.append(Paragraph("Zonas Prioritarias de Inversión", styles["section"]))
            headers = ["Zona", "Viabilidad", "Demanda", "Riesgo"]
            # Construimos las filas de la tabla con los scores de las mejores zonas
            rows = [headers] + [
                [
                    z.get("zona", "—"),
                    f"{z.get('score_viabilidad', '—')}/100",
                    f"{z.get('score_demanda', '—')}/100",
                    f"{z.get('score_riesgo', '—')}/100",
                ]
                for z in top_zonas
            ]
            t = Table(rows, colWidths=["45%", "18%", "18%", "19%"])
            # Aplicamos el estilo con encabezado azul y filas alternas grises
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_GRAY_LIGHT, C_WHITE]),
                ("GRID", (0, 0), (-1, -1), 0.5, C_GRAY_MID),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 20),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        # ── Zonas de Descarte ─────────────────────────────────────────────────
        # Construimos la tabla de zonas de descarte con su razón si existen zonas descartadas
        descarte_list = data.get("zonas_descarte_explicitas", [])
        if descarte_list:
            story.append(Paragraph("Zonas de Descarte — No Invertir", styles["section"]))
            d_headers = ["Zona", "Score", "Razón"]
            # Limitamos la razón a 120 caracteres para evitar desbordamiento en la celda
            d_rows = [d_headers] + [
                [
                    z.get("zona", "—"),
                    f"{z.get('score_viabilidad', '—')}/100",
                    Paragraph(z.get("razon", "Score inferior al umbral mínimo.")[:120], styles["body"]),
                ]
                for z in descarte_list
            ]
            dt = Table(d_rows, colWidths=["25%", "12%", "63%"])
            # Aplicamos el estilo con encabezado rojo para señalizar el riesgo de estas zonas
            dt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_RED),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FCEBEB"), C_WHITE]),
                ("GRID", (0, 0), (-1, -1), 0.5, C_GRAY_MID),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 28),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(dt)
            story.append(Spacer(1, 8))

        # ── Escenario Recomendado ─────────────────────────────────────────────
        # Construimos la tabla del escenario recomendado con sus métricas financieras
        esc = data.get("escenario_recomendado", {})
        if esc:
            story.append(Paragraph(f"Escenario Recomendado: {esc.get('nombre', '—')}", styles["section"]))
            story.append(Paragraph(esc.get("descripcion", ""), styles["body"]))
            story.append(Spacer(1, 8))

            # Construimos las filas con los indicadores financieros del escenario
            esc_data = [
                ["Unidades a desplegar", f"{esc.get('n_unidades', '—')}"],
                ["Score de viabilidad promedio", f"{esc.get('sv_promedio', '—')}/100"],
                ["ROI estimado", f"{esc.get('roi_estimado_pct', '—')}%"],
                ["Payback", f"{esc.get('payback_anios', '—')} años"],
                ["VPN estimado (MXN)", f"${esc.get('npv_mxn', 0):,.0f}"],
                ["Inversión total (MXN)", f"${esc.get('inversion_total_mxn', 0):,.0f}"],
                ["Exposición al riesgo", esc.get("riesgo_exposicion", "—")],
            ]
            esc_table = Table(esc_data, colWidths=["55%", "45%"])
            # Aplicamos fondo gris en la columna de etiquetas para mayor legibilidad
            esc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), C_GRAY_LIGHT),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, C_GRAY_MID),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 22),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(esc_table)
            story.append(Spacer(1, 12))

        # ── Advertencias ──────────────────────────────────────────────────────
        # Listamos las advertencias y limitaciones del análisis si las hay
        advertencias = data.get("advertencias", [])
        if advertencias:
            story.append(Paragraph("Advertencias y Limitaciones", styles["section"]))
            for adv in advertencias:
                story.append(Paragraph(f"⚠ {adv}", styles["bullet"]))

        # ── Próximos Pasos ─────────────────────────────────────────────────────
        # Numeramos los próximos pasos recomendados para facilitar su seguimiento
        pasos = data.get("proximos_pasos", [])
        if pasos:
            story.append(Paragraph("Próximos Pasos Recomendados", styles["section"]))
            for i, paso in enumerate(pasos, 1):
                story.append(Paragraph(f"{i}. {paso}", styles["bullet"]))

        # ── Pie de página ─────────────────────────────────────────────────────
        # Agregamos la nota legal y de fuentes de datos al pie del documento
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=C_GRAY_MID))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Documento generado por SUSVI — Plataforma de Inteligencia Territorial · XOLUM © 2026 · "
            "Análisis basado en datos públicos INEGI, SNSP, NASA VIIRS y OpenStreetMap. "
            "Este reporte es de uso interno y no constituye asesoría financiera certificada.",
            styles["small_gray"]
        ))

        # Compilamos todos los elementos del story y construimos el archivo PDF final
        doc.build(story)
        return output_path

    # ══════════════════════════════════════════════════════════════════════════
    # REPORTE POR CLIENTE (videovigilancia / constructora / inmobiliaria)
    # ══════════════════════════════════════════════════════════════════════════

    # Generamos el PDF ejecutivo de reporte por cliente con todos los datos del SSU y narrativa IA
    def generate_reporte_cliente(self, reporte_data: dict, output_path: str) -> str:
        """
        Genera un PDF ejecutivo con TODOS los datos del reporte por cliente.
        Incluye: zona, SSU, clasificación, narrativa IA, breakdown por componente,
        oportunidad, puntos clave, alertas, activos de campo y metadatos.
        """
        if not REPORTLAB_AVAILABLE:
            # Escribimos un texto plano con los datos básicos si ReportLab no está disponible
            with open(output_path.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
                f.write(f"SUSVI — Reporte {reporte_data.get('cliente', 'N/A')}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Zona: {reporte_data.get('zona', '')}\n")
                f.write(f"SSU: {reporte_data.get('ssu', 0)}\n")
                rec = reporte_data.get("reporte", {})
                f.write(f"\n{rec.get('titulo', '')}\n")
                f.write(f"{rec.get('oportunidad', '')}\n")
            return output_path.replace(".pdf", ".txt")

        # Cargamos los estilos y creamos el documento en formato LETTER con márgenes compactos
        styles = _styles()
        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
        )
        # Inicializamos el contenedor de elementos del PDF que llenamos por secciones
        story = []

        # Extraemos todos los campos del reporte de cliente para usarlos en las secciones
        zona_name = reporte_data.get("zona", "Zona Desconocida")
        ssu = reporte_data.get("ssu", 0)
        clasificacion = reporte_data.get("clasificacion", "—")
        cliente = reporte_data.get("cliente", "videovigilancia")
        narrativa_ia = reporte_data.get("narrativa_zona_ia", "")
        watsonx_usado = reporte_data.get("watsonx_usado", False)
        breakdown = reporte_data.get("breakdown", {})
        rec = reporte_data.get("reporte", {})
        fuente = reporte_data.get("fuente", "XOLUM Campo Propio")
        fecha = reporte_data.get("fecha_auditoria", "—")
        # Generamos la marca de tiempo del momento de creación del PDF
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Mapeamos la clave de cliente a su etiqueta descriptiva para el sub-banner
        cliente_labels = {
            "videovigilancia": "Videovigilancia",
            "constructora": "Constructora / Obra Pública",
            "inmobiliaria": "Desarrolladora Inmobiliaria",
        }
        # Mapeamos la clave de cliente a su ícono representativo para el sub-banner
        cliente_icons = {
            "videovigilancia": "📷",
            "constructora": "🏗️",
            "inmobiliaria": "🏢",
        }

        # ═══════════════════════════════════════════════════════════════════════
        # PORTADA / ENCABEZADO
        # ═══════════════════════════════════════════════════════════════════════

        # Construimos el banner azul principal con el nombre SUSVI y el tagline
        banner_data = [[
            Paragraph("SUSVI", ParagraphStyle(
                "banner_title", fontName="Helvetica-Bold", fontSize=20,
                textColor=C_WHITE, alignment=TA_LEFT,
            )),
            Paragraph("INTELIGENCIA DE SEGURIDAD URBANA", ParagraphStyle(
                "banner_sub", fontName="Helvetica", fontSize=9,
                textColor=colors.HexColor("#B0C4DE"), alignment=TA_RIGHT,
            )),
        ]]
        # Aplicamos el fondo azul corporativo al banner con esquinas redondeadas en la parte superior
        banner_table = Table(banner_data, colWidths=["50%", "50%"])
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_BLUE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("ROUNDEDCORNERS", [6, 6, 0, 0]),
        ]))
        story.append(banner_table)

        # Construimos el sub-banner con el tipo de cliente al que va dirigido el reporte
        sub_content = f"{cliente_icons.get(cliente, '📋')}  Reporte para {cliente_labels.get(cliente, cliente)}"
        sub_data = [[Paragraph(sub_content, ParagraphStyle(
            "sub_banner", fontName="Helvetica-Bold", fontSize=11,
            textColor=C_BLUE, alignment=TA_LEFT,
        ))]]
        # Aplicamos fondo azul claro con esquinas redondeadas en la parte inferior
        sub_table = Table(sub_data, colWidths=["100%"])
        sub_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_BLUE_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [0, 0, 6, 6]),
        ]))
        story.append(sub_table)
        story.append(Spacer(1, 6))

        # Agregamos los metadatos de generación, auditoría y fuente de datos al encabezado
        story.append(Paragraph(
            f"Generado: {ts} &nbsp;|&nbsp; Auditoría: {fecha} &nbsp;|&nbsp; Fuente: {fuente}",
            styles["small_gray"]
        ))
        story.append(Spacer(1, 14))

        # ═══════════════════════════════════════════════════════════════════════
        # ZONA + SSU SCORE
        # ═══════════════════════════════════════════════════════════════════════

        # Obtenemos los colores de acento y fondo según el nivel del SSU de la zona
        ssu_color = _ssu_color(ssu)
        ssu_bg = _ssu_bg_color(ssu)

        # Construimos la tarjeta de zona con el nombre a la izquierda y el SSU grande a la derecha
        zona_ssu_data = [[
            Paragraph(
                f'<font name="Helvetica-Bold" size="16">{zona_name}</font><br/>'
                f'<font name="Helvetica" size="10" color="#888780">{clasificacion}</font>',
                ParagraphStyle("zona_info", alignment=TA_LEFT, leading=20, textColor=C_BLACK)
            ),
            # Renderizamos el score SSU en tamaño 36 con el color correspondiente a su nivel
            Paragraph(
                f'<font name="Helvetica-Bold" size="36" color="{ssu_color.hexval()}">{ssu:.0f}</font><br/>'
                f'<font name="Helvetica" size="9" color="#888780">SSU / 100</font>',
                ParagraphStyle("ssu_big", alignment=TA_CENTER, leading=38)
            ),
        ]]
        # Aplicamos el fondo y borde de color correspondiente al nivel del SSU
        zona_ssu_table = Table(zona_ssu_data, colWidths=["65%", "35%"])
        zona_ssu_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ssu_bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("BOX", (0, 0), (-1, -1), 1, ssu_color),
        ]))
        story.append(zona_ssu_table)
        story.append(Spacer(1, 16))

        # ═══════════════════════════════════════════════════════════════════════
        # BREAKDOWN POR COMPONENTE
        # ═══════════════════════════════════════════════════════════════════════

        # Agregamos la sección del desglose con el peso de cada componente del SSU
        story.append(Paragraph("Desglose por Componente de Seguridad", styles["section"]))
        story.append(Spacer(1, 4))

        # Mapeamos cada clave de componente a su etiqueta y peso correspondiente
        component_labels = {
            "iluminacion": ("💡 Iluminación", "35%"),
            "cobertura_camara": ("📷 Cobertura de Cámara", "30%"),
            "infraestructura": ("🏗️ Infraestructura", "20%"),
            "entorno": ("🏘️ Entorno Urbano", "15%"),
        }

        # Construimos las filas del breakdown con encabezado y una fila por componente
        bd_headers = ["Componente", "Peso", "Score", "Ponderado", "Detalle"]
        bd_rows = [bd_headers]
        for comp_key, (comp_label, peso_str) in component_labels.items():
            comp = breakdown.get(comp_key, {})
            score_val = comp.get("score", 0)
            ponderado = comp.get("ponderado", 0)
            detalle = comp.get("detalle", "—")
            # Agregamos la fila del componente con su score y detalle textual de campo
            bd_rows.append([
                comp_label,
                peso_str,
                f"{score_val:.0f}/100",
                f"{ponderado:.1f}",
                Paragraph(detalle, styles["body"]),
            ])

        # Agregamos la fila de totales con el SSU final compuesto
        bd_rows.append([
            "TOTAL SSU",
            "100%",
            f"{ssu:.1f}/100",
            f"{ssu:.1f}",
            Paragraph("Score de Seguridad Urbana compuesto", styles["body"]),
        ])

        bd_table = Table(bd_rows, colWidths=["25%", "8%", "12%", "12%", "43%"])
        bd_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -2), 9),
            # Aplicamos filas alternas grises para mejorar la legibilidad
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [C_GRAY_LIGHT, C_WHITE]),
            # Aplicamos fondo azul claro a la fila de TOTAL para distinguirla del cuerpo
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D6E4F0")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, C_GRAY_MID),
            ("ALIGN", (1, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(bd_table)
        story.append(Spacer(1, 12))

        # ═══════════════════════════════════════════════════════════════════════
        # ACTIVOS VERIFICADOS EN CAMPO
        # ═══════════════════════════════════════════════════════════════════════

        # Agregamos la sección de activos de campo con estilo verde para destacar la verificación
        story.append(Paragraph("Activos Verificados en Campo", styles["section_alt"]))
        story.append(Spacer(1, 4))

        # Extraemos los datos de cada componente del breakdown para poblar la tabla de activos
        ilum = breakdown.get("iluminacion", {})
        cam = breakdown.get("cobertura_camara", {})
        infra = breakdown.get("infraestructura", {})
        ent = breakdown.get("entorno", {})

        # Construimos las filas de la tabla con indicadores, valores y observaciones de campo
        activos_data = [
            ["Indicador", "Valor", "Observaciones"],
            ["Luminarias totales", str(ilum.get("total", "—")),
             f"{ilum.get('ok', 0)} operativas, {ilum.get('mal', 0)} fuera de servicio"],
            ["Luminarias vandalizadas", str(ilum.get("vandalizadas", 0)),
             # Indicamos intervención prioritaria solo si hay luminarias vandalizadas
             "Requiere intervención prioritaria" if ilum.get("vandalizadas", 0) > 0 else "Sin vandalismo detectado"],
            ["Cobertura iluminación", f"{ilum.get('cobertura_pct', 0):.0f}%",
             "Porcentaje de luminarias operativas"],
            ["Puntos ciegos", str(cam.get("n_puntos_ciegos", 0)),
             f"{cam.get('criticos', 0)} con severidad crítica"],
            ["Terrenos abandonados", str(infra.get("n_terrenos_abandonados", 0)),
             f"Score terrenos: {infra.get('score_terrenos', 0):.0f}/100"],
            ["Score pavimento", f"{infra.get('score_pavimento', 0):.0f}/100",
             "Estado de infraestructura vial"],
            ["Calles observadas", str(ent.get("n_calles_observadas", 0)),
             f"Gentrificación: {ent.get('nivel_gentrificacion_predominante', '—')}"],
        ]

        # Aplicamos encabezado verde y filas alternas verdes claro para la tabla de activos
        activos_table = Table(activos_data, colWidths=["28%", "15%", "57%"])
        activos_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),  # Etiquetas en negrita
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_GREEN_LIGHT, C_WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.5, C_GRAY_MID),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(activos_table)
        story.append(Spacer(1, 4))
        # Agregamos la nota de verificación de campo para reforzar la diferenciación de XOLUM
        story.append(Paragraph(
            "🔒 Todos los datos son verificados en campo por equipo XOLUM — no gubernamentales",
            ParagraphStyle("campo_note", fontName="Helvetica", fontSize=8,
                           textColor=C_GREEN, alignment=TA_LEFT)
        ))
        story.append(Spacer(1, 12))

        # ═══════════════════════════════════════════════════════════════════════
        # NARRATIVA IA
        # ═══════════════════════════════════════════════════════════════════════

        # Incluimos la sección de narrativa IA solo si el motor generó texto para la zona
        if narrativa_ia:
            story.append(Paragraph("Análisis de Inteligencia Artificial", styles["section"]))
            # Indicamos si la narrativa fue generada por Granite o por el motor algorítmico
            ia_label = "IBM Watsonx Granite 3-8B" if watsonx_usado else "Motor Algorítmico SUSVI"
            story.append(Paragraph(
                f'<font name="Helvetica-Oblique" size="8" color="#888780">Generado por: {ia_label}</font>',
                styles["body"]
            ))
            story.append(Spacer(1, 4))

            # Enmarcamos la narrativa en un recuadro azul claro para distinguirla del resto del contenido
            narr_data = [[Paragraph(narrativa_ia, ParagraphStyle(
                "narr_text", fontName="Helvetica", fontSize=10,
                textColor=C_BLACK, leading=15,
            ))]]
            narr_table = Table(narr_data, colWidths=["100%"])
            narr_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_BLUE_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, C_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ]))
            story.append(narr_table)
            story.append(Spacer(1, 12))

        # ═══════════════════════════════════════════════════════════════════════
        # REPORTE ESPECÍFICO DEL CLIENTE
        # ═══════════════════════════════════════════════════════════════════════

        # Construimos la sección de reporte del cliente si el reporte tiene contenido
        if rec:
            titulo_rec = rec.get("titulo", f"Reporte para {cliente_labels.get(cliente, cliente)}")
            story.append(Paragraph(titulo_rec, styles["section"]))

            # Agregamos la referencia al motor que generó el análisis (Granite o fallback)
            gen_con = rec.get("generado_con", "—")
            story.append(Paragraph(
                f'<font name="Helvetica-Oblique" size="8" color="#888780">Análisis: {gen_con}</font>',
                styles["body"]
            ))
            story.append(Spacer(1, 6))

            # Agregamos el texto de oportunidad identificada si existe en el reporte
            oportunidad = rec.get("oportunidad", "")
            if oportunidad:
                story.append(Paragraph("Oportunidad Identificada", styles["body_bold"]))
                story.append(Paragraph(oportunidad, styles["body"]))
                story.append(Spacer(1, 8))

            # Numeramos los puntos clave del reporte del cliente
            puntos = rec.get("puntos_clave", [])
            if puntos:
                story.append(Paragraph("Puntos Clave", styles["body_bold"]))
                for i, p in enumerate(puntos, 1):
                    story.append(Paragraph(f"  {i}. {p}", styles["bullet"]))
                story.append(Spacer(1, 8))

            # Construimos el recuadro de alerta en rojo si el reporte incluye una alerta
            alerta = rec.get("alerta")
            if alerta:
                alerta_data = [[Paragraph(f"⚠  ALERTA: {alerta}", styles["alert"])]]
                alerta_table = Table(alerta_data, colWidths=["100%"])
                # Aplicamos fondo rojo claro con borde rojo para señalizar el riesgo
                alerta_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), C_RED_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 1.5, C_RED),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                ]))
                story.append(alerta_table)
                story.append(Spacer(1, 8))

        # ═══════════════════════════════════════════════════════════════════════
        # PIE DE PÁGINA
        # ═══════════════════════════════════════════════════════════════════════

        # Agregamos el pie de página con la nota legal y los créditos corporativos
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "Documento generado por SUSVI — Plataforma de Inteligencia de Seguridad Urbana",
            styles["small_center"]
        ))
        story.append(Paragraph(
            "XOLUM © 2026 · Datos verificados en campo · IBM Watsonx AI (Granite 3-8B)",
            styles["small_center"]
        ))
        # Agregamos la nota de uso interno como aviso legal obligatorio
        story.append(Paragraph(
            "Este reporte es de uso interno y no constituye asesoría de seguridad certificada. "
            "Los datos presentados son capturados y verificados por equipo de campo XOLUM.",
            styles["small_center"]
        ))

        # Compilamos todos los elementos y construimos el archivo PDF final en la ruta indicada
        doc.build(story)
        return output_path
