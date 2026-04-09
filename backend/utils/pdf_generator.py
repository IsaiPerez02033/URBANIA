"""
URBANIA — Generador de PDF Ejecutivo (ReportLab)
=================================================
Genera el reporte PDF listo para presentar a comités de inversión.
Paleta corporativa URBANIA: azul #185FA5, verde #1D9E75, rojo #E24B4A.
"""
import os
from datetime import datetime

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
    REPORTLAB_AVAILABLE = False


# ── Paleta corporativa ────────────────────────────────────────────────────────
if REPORTLAB_AVAILABLE:
    C_BLUE = colors.HexColor("#185FA5")
    C_BLUE_LIGHT = colors.HexColor("#E8F0FC")
    C_GREEN = colors.HexColor("#1D9E75")
    C_GREEN_LIGHT = colors.HexColor("#E6F7F0")
    C_AMBER = colors.HexColor("#EF9F27")
    C_AMBER_LIGHT = colors.HexColor("#FFF7E6")
    C_RED = colors.HexColor("#E24B4A")
    C_RED_LIGHT = colors.HexColor("#FCEBEB")
    C_GRAY_LIGHT = colors.HexColor("#F1EFE8")
    C_GRAY_MID = colors.HexColor("#888780")
    C_GRAY_DARK = colors.HexColor("#4A5068")
    C_BLACK = colors.HexColor("#2C2C2A")
    C_WHITE = colors.white
else:
    C_BLUE = C_BLUE_LIGHT = C_GREEN = C_GREEN_LIGHT = C_AMBER = C_AMBER_LIGHT = None
    C_RED = C_RED_LIGHT = C_GRAY_LIGHT = C_GRAY_MID = C_GRAY_DARK = C_BLACK = C_WHITE = None


def _styles():
    base = getSampleStyleSheet()
    custom = {}
    custom["title"] = ParagraphStyle(
        "title", parent=base["Normal"],
        fontSize=22, textColor=C_BLUE, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    custom["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"],
        fontSize=12, textColor=C_GRAY_MID, spaceAfter=16,
        fontName="Helvetica", alignment=TA_LEFT,
    )
    custom["section"] = ParagraphStyle(
        "section", parent=base["Normal"],
        fontSize=13, textColor=C_BLUE, spaceBefore=16, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    custom["section_alt"] = ParagraphStyle(
        "section_alt", parent=base["Normal"],
        fontSize=13, textColor=C_GREEN, spaceBefore=16, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    custom["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=4,
        fontName="Helvetica", leading=14,
    )
    custom["body_bold"] = ParagraphStyle(
        "body_bold", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=4,
        fontName="Helvetica-Bold", leading=14,
    )
    custom["bullet"] = ParagraphStyle(
        "bullet", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=3,
        fontName="Helvetica", leftIndent=16, leading=14,
    )
    custom["kpi_label"] = ParagraphStyle(
        "kpi_label", parent=base["Normal"],
        fontSize=9, textColor=C_WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    custom["kpi_value"] = ParagraphStyle(
        "kpi_value", parent=base["Normal"],
        fontSize=24, textColor=C_WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=2,
    )
    custom["small_gray"] = ParagraphStyle(
        "small_gray", parent=base["Normal"],
        fontSize=8, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_RIGHT,
    )
    custom["small_center"] = ParagraphStyle(
        "small_center", parent=base["Normal"],
        fontSize=8, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_CENTER,
    )
    custom["alert"] = ParagraphStyle(
        "alert", parent=base["Normal"],
        fontSize=10, textColor=C_RED, fontName="Helvetica-Bold",
        spaceAfter=4, leading=14,
    )
    custom["watermark"] = ParagraphStyle(
        "watermark", parent=base["Normal"],
        fontSize=7, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_CENTER,
    )
    return custom


def _ssu_color(ssu):
    """Devuelve color de acuerdo al score SSU."""
    if ssu >= 75:
        return C_GREEN
    if ssu >= 50:
        return C_AMBER
    if ssu >= 30:
        return C_RED
    return colors.HexColor("#7B1C1C")


def _ssu_bg_color(ssu):
    """Fondo suave para SSU."""
    if ssu >= 75:
        return C_GREEN_LIGHT
    if ssu >= 50:
        return C_AMBER_LIGHT
    if ssu >= 30:
        return C_RED_LIGHT
    return C_RED_LIGHT


class URBANIAReportGenerator:
    """Generador de reportes PDF ejecutivos para URBANIA."""

    def generate(self, data: dict, output_path: str) -> str:
        """Genera reporte ejecutivo genérico (inversión territorial)."""
        if not REPORTLAB_AVAILABLE:
            # Fallback: escribir texto plano
            with open(output_path.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
                f.write("URBANIA — Reporte Ejecutivo\n")
                f.write("=" * 50 + "\n")
                f.write(data.get("resumen_ejecutivo", "") + "\n")
            return output_path.replace(".pdf", ".txt")

        styles = _styles()
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        story = []

        # ── Encabezado ────────────────────────────────────────────────────────
        story.append(Paragraph("URBANIA", styles["title"]))
        story.append(Paragraph(
            data.get("titulo", "Reporte de Inteligencia Territorial"),
            styles["subtitle"]
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=12))

        # Metadata
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        story.append(Paragraph(
            f"Generado: {ts} &nbsp;|&nbsp; Análisis ID: {data.get('analysis_id', 'demo')[:8]}",
            styles["small_gray"]
        ))
        story.append(Spacer(1, 12))

        # ── KPIs ──────────────────────────────────────────────────────────────
        kpis = data.get("kpis", {})
        verdes = kpis.get("verdes", "—")
        cautela_n = kpis.get("cautela", "—")
        descarte_n = kpis.get("descarte", "—")

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
        kpi_table = Table(kpi_data, colWidths=["33%", "33%", "34%"])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), C_GREEN),
            ("BACKGROUND", (1, 0), (1, -1), C_AMBER),
            ("BACKGROUND", (2, 0), (2, -1), C_RED),
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
        story.append(Paragraph("Resumen Ejecutivo", styles["section"]))
        story.append(Paragraph(data.get("resumen_ejecutivo", ""), styles["body"]))

        # ── Hallazgos Clave ───────────────────────────────────────────────────
        hallazgos = data.get("hallazgos_clave", [])
        if hallazgos:
            story.append(Paragraph("Hallazgos Clave", styles["section"]))
            for h in hallazgos:
                story.append(Paragraph(f"• {h}", styles["bullet"]))

        # ── Top Zonas de Inversión ─────────────────────────────────────────────
        top_zonas = data.get("top_zonas_inversion", [])
        if top_zonas:
            story.append(Paragraph("Zonas Prioritarias de Inversión", styles["section"]))
            headers = ["Zona", "Viabilidad", "Demanda", "Riesgo"]
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
        descarte_list = data.get("zonas_descarte_explicitas", [])
        if descarte_list:
            story.append(Paragraph("Zonas de Descarte — No Invertir", styles["section"]))
            d_headers = ["Zona", "Score", "Razón"]
            d_rows = [d_headers] + [
                [
                    z.get("zona", "—"),
                    f"{z.get('score_viabilidad', '—')}/100",
                    Paragraph(z.get("razon", "Score inferior al umbral mínimo.")[:120], styles["body"]),
                ]
                for z in descarte_list
            ]
            dt = Table(d_rows, colWidths=["25%", "12%", "63%"])
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
        esc = data.get("escenario_recomendado", {})
        if esc:
            story.append(Paragraph(f"Escenario Recomendado: {esc.get('nombre', '—')}", styles["section"]))
            story.append(Paragraph(esc.get("descripcion", ""), styles["body"]))
            story.append(Spacer(1, 8))

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
        advertencias = data.get("advertencias", [])
        if advertencias:
            story.append(Paragraph("Advertencias y Limitaciones", styles["section"]))
            for adv in advertencias:
                story.append(Paragraph(f"⚠ {adv}", styles["bullet"]))

        # ── Próximos Pasos ─────────────────────────────────────────────────────
        pasos = data.get("proximos_pasos", [])
        if pasos:
            story.append(Paragraph("Próximos Pasos Recomendados", styles["section"]))
            for i, paso in enumerate(pasos, 1):
                story.append(Paragraph(f"{i}. {paso}", styles["bullet"]))

        # ── Pie de página ─────────────────────────────────────────────────────
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=C_GRAY_MID))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Documento generado por URBANIA — Plataforma de Inteligencia Territorial · XOLUM © 2026 · "
            "Análisis basado en datos públicos INEGI, SNSP, NASA VIIRS y OpenStreetMap. "
            "Este reporte es de uso interno y no constituye asesoría financiera certificada.",
            styles["small_gray"]
        ))

        doc.build(story)
        return output_path

    # ══════════════════════════════════════════════════════════════════════════
    # REPORTE POR CLIENTE (videovigilancia / constructora / inmobiliaria)
    # ══════════════════════════════════════════════════════════════════════════

    def generate_reporte_cliente(self, reporte_data: dict, output_path: str) -> str:
        """
        Genera un PDF ejecutivo con TODOS los datos del reporte por cliente.
        Incluye: zona, SSU, clasificación, narrativa IA, breakdown por componente,
        oportunidad, puntos clave, alertas, activos de campo y metadatos.
        """
        if not REPORTLAB_AVAILABLE:
            with open(output_path.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
                f.write(f"URBANIA — Reporte {reporte_data.get('cliente', 'N/A')}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Zona: {reporte_data.get('zona', '')}\n")
                f.write(f"SSU: {reporte_data.get('ssu', 0)}\n")
                rec = reporte_data.get("reporte", {})
                f.write(f"\n{rec.get('titulo', '')}\n")
                f.write(f"{rec.get('oportunidad', '')}\n")
            return output_path.replace(".pdf", ".txt")

        styles = _styles()
        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
        )
        story = []

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
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")

        cliente_labels = {
            "videovigilancia": "Videovigilancia",
            "constructora": "Constructora / Obra Pública",
            "inmobiliaria": "Desarrolladora Inmobiliaria",
        }
        cliente_icons = {
            "videovigilancia": "📷",
            "constructora": "🏗️",
            "inmobiliaria": "🏢",
        }

        # ═══════════════════════════════════════════════════════════════════════
        # PORTADA / ENCABEZADO
        # ═══════════════════════════════════════════════════════════════════════

        # Banner superior
        banner_data = [[
            Paragraph("URBANIA", ParagraphStyle(
                "banner_title", fontName="Helvetica-Bold", fontSize=20,
                textColor=C_WHITE, alignment=TA_LEFT,
            )),
            Paragraph("INTELIGENCIA DE SEGURIDAD URBANA", ParagraphStyle(
                "banner_sub", fontName="Helvetica", fontSize=9,
                textColor=colors.HexColor("#B0C4DE"), alignment=TA_RIGHT,
            )),
        ]]
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

        # Sub-banner con tipo de reporte
        sub_content = f"{cliente_icons.get(cliente, '📋')}  Reporte para {cliente_labels.get(cliente, cliente)}"
        sub_data = [[Paragraph(sub_content, ParagraphStyle(
            "sub_banner", fontName="Helvetica-Bold", fontSize=11,
            textColor=C_BLUE, alignment=TA_LEFT,
        ))]]
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

        # Metadatos
        story.append(Paragraph(
            f"Generado: {ts} &nbsp;|&nbsp; Auditoría: {fecha} &nbsp;|&nbsp; Fuente: {fuente}",
            styles["small_gray"]
        ))
        story.append(Spacer(1, 14))

        # ═══════════════════════════════════════════════════════════════════════
        # ZONA + SSU SCORE
        # ═══════════════════════════════════════════════════════════════════════

        ssu_color = _ssu_color(ssu)
        ssu_bg = _ssu_bg_color(ssu)

        zona_ssu_data = [[
            Paragraph(
                f'<font name="Helvetica-Bold" size="16">{zona_name}</font><br/>'
                f'<font name="Helvetica" size="10" color="#888780">{clasificacion}</font>',
                ParagraphStyle("zona_info", alignment=TA_LEFT, leading=20, textColor=C_BLACK)
            ),
            Paragraph(
                f'<font name="Helvetica-Bold" size="36" color="{ssu_color.hexval()}">{ssu:.0f}</font><br/>'
                f'<font name="Helvetica" size="9" color="#888780">SSU / 100</font>',
                ParagraphStyle("ssu_big", alignment=TA_CENTER, leading=38)
            ),
        ]]
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

        story.append(Paragraph("Desglose por Componente de Seguridad", styles["section"]))
        story.append(Spacer(1, 4))

        component_labels = {
            "iluminacion": ("💡 Iluminación", "35%"),
            "cobertura_camara": ("📷 Cobertura de Cámara", "30%"),
            "infraestructura": ("🏗️ Infraestructura", "20%"),
            "entorno": ("🏘️ Entorno Urbano", "15%"),
        }

        bd_headers = ["Componente", "Peso", "Score", "Ponderado", "Detalle"]
        bd_rows = [bd_headers]
        for comp_key, (comp_label, peso_str) in component_labels.items():
            comp = breakdown.get(comp_key, {})
            score_val = comp.get("score", 0)
            ponderado = comp.get("ponderado", 0)
            detalle = comp.get("detalle", "—")
            bd_rows.append([
                comp_label,
                peso_str,
                f"{score_val:.0f}/100",
                f"{ponderado:.1f}",
                Paragraph(detalle, styles["body"]),
            ])

        # Fila total
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
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [C_GRAY_LIGHT, C_WHITE]),
            # Fila TOTAL
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D6E4F0")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 10),
            # Grid
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

        story.append(Paragraph("Activos Verificados en Campo", styles["section_alt"]))
        story.append(Spacer(1, 4))

        ilum = breakdown.get("iluminacion", {})
        cam = breakdown.get("cobertura_camara", {})
        infra = breakdown.get("infraestructura", {})
        ent = breakdown.get("entorno", {})

        activos_data = [
            ["Indicador", "Valor", "Observaciones"],
            ["Luminarias totales", str(ilum.get("total", "—")),
             f"{ilum.get('ok', 0)} operativas, {ilum.get('mal', 0)} fuera de servicio"],
            ["Luminarias vandalizadas", str(ilum.get("vandalizadas", 0)),
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

        activos_table = Table(activos_data, colWidths=["28%", "15%", "57%"])
        activos_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
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
        story.append(Paragraph(
            "🔒 Todos los datos son verificados en campo por equipo XOLUM — no gubernamentales",
            ParagraphStyle("campo_note", fontName="Helvetica", fontSize=8,
                           textColor=C_GREEN, alignment=TA_LEFT)
        ))
        story.append(Spacer(1, 12))

        # ═══════════════════════════════════════════════════════════════════════
        # NARRATIVA IA
        # ═══════════════════════════════════════════════════════════════════════

        if narrativa_ia:
            story.append(Paragraph("Análisis de Inteligencia Artificial", styles["section"]))
            ia_label = "IBM Watsonx Granite 3-8B" if watsonx_usado else "Motor Algorítmico URBANIA"
            story.append(Paragraph(
                f'<font name="Helvetica-Oblique" size="8" color="#888780">Generado por: {ia_label}</font>',
                styles["body"]
            ))
            story.append(Spacer(1, 4))

            # Narrativa en recuadro
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

        if rec:
            titulo_rec = rec.get("titulo", f"Reporte para {cliente_labels.get(cliente, cliente)}")
            story.append(Paragraph(titulo_rec, styles["section"]))

            # Generado con
            gen_con = rec.get("generado_con", "—")
            story.append(Paragraph(
                f'<font name="Helvetica-Oblique" size="8" color="#888780">Análisis: {gen_con}</font>',
                styles["body"]
            ))
            story.append(Spacer(1, 6))

            # Oportunidad
            oportunidad = rec.get("oportunidad", "")
            if oportunidad:
                story.append(Paragraph("Oportunidad Identificada", styles["body_bold"]))
                story.append(Paragraph(oportunidad, styles["body"]))
                story.append(Spacer(1, 8))

            # Puntos clave
            puntos = rec.get("puntos_clave", [])
            if puntos:
                story.append(Paragraph("Puntos Clave", styles["body_bold"]))
                for i, p in enumerate(puntos, 1):
                    story.append(Paragraph(f"  {i}. {p}", styles["bullet"]))
                story.append(Spacer(1, 8))

            # Alerta
            alerta = rec.get("alerta")
            if alerta:
                alerta_data = [[Paragraph(f"⚠  ALERTA: {alerta}", styles["alert"])]]
                alerta_table = Table(alerta_data, colWidths=["100%"])
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

        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "Documento generado por URBANIA — Plataforma de Inteligencia de Seguridad Urbana",
            styles["small_center"]
        ))
        story.append(Paragraph(
            "XOLUM © 2026 · Datos verificados en campo · IBM Watsonx AI (Granite 3-8B)",
            styles["small_center"]
        ))
        story.append(Paragraph(
            "Este reporte es de uso interno y no constituye asesoría de seguridad certificada. "
            "Los datos presentados son capturados y verificados por equipo de campo XOLUM.",
            styles["small_center"]
        ))

        doc.build(story)
        return output_path
