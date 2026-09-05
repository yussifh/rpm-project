"""
PDF report builder — pure function, no ORM/FastAPI dependency (same
decoupling principle as app.ai_engine: takes a plain dict, returns raw PDF
bytes, so it's independently testable and reusable outside the API, e.g.
a scheduled nightly report job).

The caller (ReportService) is responsible for gathering ORM data into the
plain `ReportData` shape this module expects.
"""

import io
from typing import TypedDict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SEVERITY_COLORS = {
    "critical": colors.HexColor("#C0463C"),
    "warning": colors.HexColor("#E2A63B"),
    "high": colors.HexColor("#C0463C"),
    "moderate": colors.HexColor("#E2A63B"),
    "low": colors.HexColor("#3E8E5B"),
}
BRAND_COLOR = colors.HexColor("#14555A")


class VitalRow(TypedDict):
    recorded_at: str
    blood_pressure: str
    heart_rate: str
    glucose: str
    spo2: str


class MedicationRow(TypedDict):
    name: str
    dosage: str
    frequency: str
    status: str


class AlertRow(TypedDict):
    title: str
    severity: str
    status: str
    created_at: str


class PredictionRow(TypedDict):
    disease_type: str
    risk_level: str
    risk_score: str
    predicted_at: str


class ReportData(TypedDict):
    patient_name: str
    date_of_birth: str
    gender: str
    blood_group: str
    generated_at: str
    vitals: list[VitalRow]
    medications: list[MedicationRow]
    alerts: list[AlertRow]
    predictions: list[PredictionRow]


def _section_title(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["SectionTitle"])


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontSize=20,
            leading=24,
            textColor=BRAND_COLOR,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontSize=13,
            leading=16,
            textColor=BRAND_COLOR,
            spaceBefore=16,
            spaceAfter=8,
        )
    )
    return styles


def _table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E6E5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F7F7")]),
            ]
        )
    )
    return table


def build_patient_summary_pdf(data: ReportData) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = _styles()
    elements = []

    elements.append(Paragraph("Patient Health Summary Report", styles["ReportTitle"]))
    elements.append(
        Paragraph(
            f"Generated {data['generated_at']} &mdash; AI-Integrated Remote Patient Monitoring System",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    profile_table = _table(
        [
            ["Patient", data["patient_name"]],
            ["Date of Birth", data["date_of_birth"]],
            ["Gender", data["gender"]],
            ["Blood Group", data["blood_group"] or "Not recorded"],
        ],
        col_widths=[1.8 * inch, 4.2 * inch],
    )
    elements.append(profile_table)

    elements.append(_section_title("Recent Vitals", styles))
    if data["vitals"]:
        rows = [["Recorded At", "Blood Pressure", "Heart Rate", "Glucose", "SpO2"]]
        rows += [[v["recorded_at"], v["blood_pressure"], v["heart_rate"], v["glucose"], v["spo2"]] for v in data["vitals"]]
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("No vitals recorded yet.", styles["Normal"]))

    elements.append(_section_title("Active Medications", styles))
    if data["medications"]:
        rows = [["Name", "Dosage", "Frequency", "Status"]]
        rows += [[m["name"], m["dosage"], m["frequency"], m["status"]] for m in data["medications"]]
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("No medications recorded.", styles["Normal"]))

    elements.append(_section_title("Recent Alerts", styles))
    if data["alerts"]:
        rows = [["Title", "Severity", "Status", "Date"]]
        rows += [[a["title"], a["severity"], a["status"], a["created_at"]] for a in data["alerts"]]
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("No alerts recorded.", styles["Normal"]))

    elements.append(_section_title("Latest AI Risk Predictions", styles))
    if data["predictions"]:
        rows = [["Disease", "Risk Level", "Score", "Predicted At"]]
        rows += [
            [p["disease_type"], p["risk_level"], p["risk_score"], p["predicted_at"]]
            for p in data["predictions"]
        ]
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("No AI risk predictions generated yet.", styles["Normal"]))

    elements.append(Spacer(1, 20))
    elements.append(
        Paragraph(
            "This report is generated by an AI-assisted monitoring system and is intended to support, "
            "not replace, clinical judgment. All risk predictions are based on a demonstration model "
            "trained on synthetic data and require clinical validation before real-world use.",
            styles["Italic"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()
