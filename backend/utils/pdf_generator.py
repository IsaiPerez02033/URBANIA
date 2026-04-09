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
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


C_BLUE = colors.HexColor("#185FA5")
C_GREEN = colors.HexColor("#1D9E75")
C_AMBER = colors.HexColor("#EF9F27")
C_RED = colors.HexColor("#E24B4A")
C_GRAY_LIGHT = colors.HexColor("#F1EFE8")
C_GRAY_MID = colors.HexColor("#888780")
C_BLACK = colors.HexColor("#2C2C2A")
C_WHITE = colors.white


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
    custom["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, textColor=C_BLACK, spaceAfter=4,
        fontName="Helvetica", leading=14,
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
    custom["small_gray"] = ParagraphStyle(
        "small_gray", parent=base["Normal"],
        fontSize=8, textColor=C_GRAY_MID, fontName="Helvetica",
        alignment=TA_RIGHT,
    )
    return custom


class URBANIAReportGenerator:
    def generate(self, data: dict, output_path: str) -> str:
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
