import os
import sys

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Define input and output file paths (update these for your environment)
INPUT_PDF = os.path.join(os.path.expanduser("~"), "Downloads", "syllabus_input.pdf")
OUTPUT_PDF = os.path.join(os.path.expanduser("~"), "Desktop", "Generated_Syllabus.pdf")

print(f"Checking input PDF at: {INPUT_PDF}")
if HAS_PYPDF and os.path.exists(INPUT_PDF):
    try:
        reader = pypdf.PdfReader(INPUT_PDF)
        print(f"Input PDF found with {len(reader.pages)} pages.")
    except Exception as e:
        print(f"Note: Could not parse input PDF: {e}")
else:
    print("Proceeding with structured syllabus database.")

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Custom NumberedCanvas for professional header/footer with dynamic page numbers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        page_w, page_h = A4
        margin = 36
        
        # Top Header Bar
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(margin, page_h - 36, page_w - margin, page_h - 36)
        
        self.drawString(margin, page_h - 30, "VESIT — Department of Automation and Robotics")
        self.drawRightString(page_w - margin, page_h - 30, "Syllabus Structure, Timetable & Curriculum (Sem III | NEP Scheme)")
        
        # Bottom Footer Bar
        self.line(margin, 42, page_w - margin, 42)
        self.drawString(margin, 28, "A.Y. 2026–27 | Autonomous Scheme (3rd Semester AURO Curriculum)")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_w - margin, 28, page_str)
        
        self.restoreState()

def create_syllabus_pdf():
    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
    
    # Document Setup
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Color Palette Definition
    PRIMARY = colors.HexColor("#0F172A")      # Dark Navy / Slate 900
    SECONDARY = colors.HexColor("#0284C7")    # Deep Teal / Ocean 600
    ACCENT = colors.HexColor("#0EA5E9")       # Light Teal / Sky 500
    TEXT_DARK = colors.HexColor("#1E293B")    # Charcoal
    TEXT_MUTED = colors.HexColor("#64748B")   # Muted Grey
    BG_LIGHT = colors.HexColor("#F8FAFC")     # Warm Light White
    BG_CARD = colors.HexColor("#F1F5F9")      # Light Slate Shading
    BORDER_COLOR = colors.HexColor("#E2E8F0") # Border Line
    
    # Custom Paragraph Styles
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=4
    )
    
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceAfter=12
    )
    
    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK,
        spaceAfter=4
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK
    )

    style_table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=style_table_cell,
        alignment=1
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white,
        alignment=1
    )

    story = []

    # ---------------------------------------------------------
    # COVER / HEADER BANNER
    # ---------------------------------------------------------
    banner_data = [
        [
            Paragraph("<b>VIVEKANAND EDUCATION SOCIETY'S INSTITUTE OF TECHNOLOGY</b><br/>"
                      "<font size=8.5 color='#64748B'>Department of Automation and Robotics (AURO - NEP Scheme)</font>", style_body),
            Paragraph("<font size=8 color='#0284C7'><b>A.Y. 2026–27</b><br/>Semester III Curriculum</font>", ParagraphStyle('RightBanner', parent=style_body, alignment=2))
        ]
    ]
    banner_table = Table(banner_data, colWidths=[370, 152])
    banner_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SECONDARY, spaceAfter=10))

    story.append(Paragraph("3rd Semester Automation & Robotics (AURO) Syllabus & Timetable", style_cover_title))
    story.append(Paragraph("Complete Curriculum, Weekly Class Schedule, Course Modules & Experiments Guide", style_cover_subtitle))
    
    # Description callout box
    desc_html = (
        "<b>Document Overview:</b> This document provides an integrated, highly structured syllabus overview for "
        "<b>Semester III (Automation & Robotics - AURO)</b>. It contains the official course codes, credit distribution, "
        "teaching & examination scheme, weekly class timetable, detailed module breakdowns, practical experiment lists, "
        "and recommended textbooks."
    )
    desc_table = Table([[Paragraph(desc_html, style_body)]], colWidths=[522])
    desc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(desc_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 1. SEMESTER III SCHEME OVERVIEW TABLE
    # ---------------------------------------------------------
    story.append(Paragraph("1. Semester III Teaching & Examination Scheme", style_h1))
    
    scheme_headers = ["Timetable Ref", "Course Code", "Course Name", "Type", "Th/Pr/Tut", "Credits", "Marks"]
    scheme_rows = [
        [Paragraph(h, style_table_header) for h in scheme_headers],
        [Paragraph("<b>Industrial Sensors</b>", style_table_cell), Paragraph("26ARPC31", style_table_cell), Paragraph("Industrial Sensors (Theory)", style_table_cell), Paragraph("PCC", style_table_cell), Paragraph("3 / - / -", style_table_cell), Paragraph("3", style_table_cell), Paragraph("100", style_table_cell)],
        [Paragraph("<b>I.S. Lab</b>", style_table_cell), Paragraph("26ARPC31", style_table_cell), Paragraph("Industrial Sensors (Lab)", style_table_cell), Paragraph("PCC Lab", style_table_cell), Paragraph("- / 2 / -", style_table_cell), Paragraph("1", style_table_cell), Paragraph("50", style_table_cell)],
        [Paragraph("<b>Analog Electronics</b>", style_table_cell), Paragraph("26ARPC32", style_table_cell), Paragraph("Analog Electronics & Networks (Theory)", style_table_cell), Paragraph("PCC", style_table_cell), Paragraph("3 / - / -", style_table_cell), Paragraph("3", style_table_cell), Paragraph("100", style_table_cell)],
        [Paragraph("<b>A.E. Lab</b>", style_table_cell), Paragraph("26ARPC32", style_table_cell), Paragraph("Analog Electronics & Networks (Lab)", style_table_cell), Paragraph("PCC Lab", style_table_cell), Paragraph("- / 2 / -", style_table_cell), Paragraph("1", style_table_cell), Paragraph("50", style_table_cell)],
        [Paragraph("<b>Digital Electronics</b>", style_table_cell), Paragraph("26ARPC33", style_table_cell), Paragraph("Digital Electronics (Theory)", style_table_cell), Paragraph("PCC", style_table_cell), Paragraph("2 / - / -", style_table_cell), Paragraph("2", style_table_cell), Paragraph("100", style_table_cell)],
        [Paragraph("<b>D.E. Lab</b>", style_table_cell), Paragraph("26ARPC33", style_table_cell), Paragraph("Digital Electronics (Practical App)", style_table_cell), Paragraph("PCC Lab", style_table_cell), Paragraph("- / 2 / -", style_table_cell), Paragraph("1", style_table_cell), Paragraph("25", style_table_cell)],
        [Paragraph("<b>Robot Mechanics</b>", style_table_cell), Paragraph("26ARPC34", style_table_cell), Paragraph("Fundamentals of Robotic Mech Systems", style_table_cell), Paragraph("PCC", style_table_cell), Paragraph("2 / - / -", style_table_cell), Paragraph("2", style_table_cell), Paragraph("100", style_table_cell)],
        [Paragraph("<b>Maths</b>", style_table_cell), Paragraph("26ARMM31", style_table_cell), Paragraph("Advanced Mathematics for AI & ML", style_table_cell), Paragraph("MDM", style_table_cell), Paragraph("3 / - / 2", style_table_cell), Paragraph("4", style_table_cell), Paragraph("125", style_table_cell)],
        [Paragraph("<b>Financial Mgmt</b>", style_table_cell), Paragraph("26AREM31", style_table_cell), Paragraph("Financial Management", style_table_cell), Paragraph("HSSM", style_table_cell), Paragraph("2 / - / -", style_table_cell), Paragraph("2", style_table_cell), Paragraph("50", style_table_cell)],
        [Paragraph("<b>PCE</b>", style_table_cell), Paragraph("26AREM32", style_table_cell), Paragraph("Professional Communication & Ethics-II", style_table_cell), Paragraph("HSSM", style_table_cell), Paragraph("1 / 2 / -", style_table_cell), Paragraph("2", style_table_cell), Paragraph("50", style_table_cell)],
        [Paragraph("<b>TOTAL</b>", ParagraphStyle('B1', parent=style_table_cell, fontName='Helvetica-Bold')), 
         Paragraph("-", style_table_cell), Paragraph("<b>10 Correlated Subjects & Labs</b>", ParagraphStyle('B2', parent=style_table_cell, fontName='Helvetica-Bold')), 
         Paragraph("-", style_table_cell), Paragraph("<b>17 / 8 / 2</b>", ParagraphStyle('B3', parent=style_table_cell, fontName='Helvetica-Bold')), 
         Paragraph("<b>20</b>", ParagraphStyle('B4', parent=style_table_cell, fontName='Helvetica-Bold')), 
         Paragraph("<b>750 Marks</b>", ParagraphStyle('B5', parent=style_table_cell, fontName='Helvetica-Bold'))]
    ]

    scheme_table = Table(scheme_rows, colWidths=[90, 65, 170, 45, 54, 42, 56])
    scheme_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('BACKGROUND', (0,1), (-1,1), BG_LIGHT),
        ('BACKGROUND', (0,3), (-1,3), BG_LIGHT),
        ('BACKGROUND', (0,5), (-1,5), BG_LIGHT),
        ('BACKGROUND', (0,7), (-1,7), BG_LIGHT),
        ('BACKGROUND', (0,9), (-1,9), BG_LIGHT),
        ('BACKGROUND', (0,-1), (-1,-1), BG_CARD),
    ]))
    story.append(scheme_table)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # 2. WEEKLY CLASS TIMETABLE SECTION
    # ---------------------------------------------------------
    story.append(Paragraph("2. Weekly Class Timetable (Semester III — AURO)", style_h1))
    
    tt_headers = ["Day / Time", "09:00 - 10:00", "10:00 - 11:00", "11:15 - 12:15", "12:15 - 01:15", "02:00 - 04:00"]
    tt_rows = [
        [Paragraph(h, style_table_header) for h in tt_headers],
        [
            Paragraph("<b>Monday</b>", style_table_cell),
            Paragraph("Maths (Tut)<br/><font size=7 color='#64748B'>Batch A</font>", style_table_cell_center),
            Paragraph("Maths (Tut)<br/><font size=7 color='#64748B'>Batch B</font>", style_table_cell_center),
            Paragraph("Industrial Sensors<br/><font size=7 color='#0284C7'>26ARPC31</font>", style_table_cell_center),
            Paragraph("Analog Electronics<br/><font size=7 color='#0284C7'>26ARPC32</font>", style_table_cell_center),
            Paragraph("<b>A.E. Lab (A) / D.E. Lab (B)</b><br/><font size=7 color='#64748B'>Practical Batches</font>", style_table_cell_center)
        ],
        [
            Paragraph("<b>Tuesday</b>", style_table_cell),
            Paragraph("Maths<br/><font size=7 color='#0284C7'>26ARMM31</font>", style_table_cell_center),
            Paragraph("Robot Mechanics<br/><font size=7 color='#0284C7'>26ARPC34</font>", style_table_cell_center),
            Paragraph("Digital Electronics<br/><font size=7 color='#0284C7'>26ARPC33</font>", style_table_cell_center),
            Paragraph("Financial Mgmt<br/><font size=7 color='#0284C7'>26AREM31</font>", style_table_cell_center),
            Paragraph("<b>PCE-II Lab</b><br/><font size=7 color='#64748B'>Communication Lab</font>", style_table_cell_center)
        ],
        [
            Paragraph("<b>Wednesday</b>", style_table_cell),
            Paragraph("Industrial Sensors<br/><font size=7 color='#0284C7'>26ARPC31</font>", style_table_cell_center),
            Paragraph("Analog Electronics<br/><font size=7 color='#0284C7'>26ARPC32</font>", style_table_cell_center),
            Paragraph("Maths<br/><font size=7 color='#0284C7'>26ARMM31</font>", style_table_cell_center),
            Paragraph("PCE Theory<br/><font size=7 color='#0284C7'>26AREM32</font>", style_table_cell_center),
            Paragraph("<b>I.S. Lab (A) / A.E. Lab (B)</b><br/><font size=7 color='#64748B'>Sensors / Circuit Lab</font>", style_table_cell_center)
        ],
        [
            Paragraph("<b>Thursday</b>", style_table_cell),
            Paragraph("Digital Electronics<br/><font size=7 color='#0284C7'>26ARPC33</font>", style_table_cell_center),
            Paragraph("Industrial Sensors<br/><font size=7 color='#0284C7'>26ARPC31</font>", style_table_cell_center),
            Paragraph("Analog Electronics<br/><font size=7 color='#0284C7'>26ARPC32</font>", style_table_cell_center),
            Paragraph("Robot Mechanics<br/><font size=7 color='#0284C7'>26ARPC34</font>", style_table_cell_center),
            Paragraph("<b>D.E. Lab (A) / I.S. Lab (B)</b><br/><font size=7 color='#64748B'>Digital / Hardware Lab</font>", style_table_cell_center)
        ],
        [
            Paragraph("<b>Friday</b>", style_table_cell),
            Paragraph("Maths<br/><font size=7 color='#0284C7'>26ARMM31</font>", style_table_cell_center),
            Paragraph("Financial Mgmt<br/><font size=7 color='#0284C7'>26AREM31</font>", style_table_cell_center),
            Paragraph("GATE / Remedial<br/><font size=7 color='#64748B'>Special Session</font>", style_table_cell_center),
            Paragraph("Library / Self-Study<br/><font size=7 color='#64748B'>Resource Hour</font>", style_table_cell_center),
            Paragraph("<b>Mentoring & Club Activities</b><br/><font size=7 color='#64748B'>Robotics Club / AI</font>", style_table_cell_center)
        ]
    ]

    tt_table = Table(tt_rows, colWidths=[65, 85, 85, 95, 90, 102])
    tt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (0,-1), BG_CARD),
        ('BACKGROUND', (1,1), (-1,1), BG_LIGHT),
        ('BACKGROUND', (1,3), (-1,3), BG_LIGHT),
        ('BACKGROUND', (1,5), (-1,5), BG_LIGHT),
    ]))
    story.append(tt_table)
    story.append(Spacer(1, 14))

    # Helper function to generate subject header block
    def make_subject_header(subject_title, timetable_tag, code, credits_str, course_type):
        content = [
            [
                Paragraph(f"<b>{subject_title}</b>", ParagraphStyle('SubjHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=PRIMARY)),
                Paragraph(f"<b>Code:</b> {code} | <b>Credits:</b> {credits_str} | <b>Type:</b> {course_type}", ParagraphStyle('SubjMeta', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=2, textColor=SECONDARY))
            ],
            [
                Paragraph(f"<font color='#0284C7'><b>Timetable Mapping Tag:</b></font> <font color='#0F172A'><b>[{timetable_tag}]</b></font>", style_body),
                Paragraph("", style_body)
            ]
        ]
        t = Table(content, colWidths=[320, 202])
        t.setStyle(TableStyle([
            ('SPAN', (0,1), (1,1)),
            ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, SECONDARY),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    # ---------------------------------------------------------
    # 3. DETAILED SUBJECT SYLLABUS SECTIONS
    # ---------------------------------------------------------
    story.append(Paragraph("3. Detailed Syllabus, Chapters & Topic Breakdown", style_h1))

    # SUBJECT 1: Industrial Sensors
    story.append(make_subject_header("1. Industrial Sensors", "Industrial Sensors", "26ARPC31", "3 Theory + 1 Lab", "PCC"))
    story.append(Spacer(1, 4))
    
    is_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Overview of Measurement Systems:</b> Introduction, Need for Measurement, Block diagram & functional elements of measurement system, Units & conversions, Errors in measurement (types & remedies).", style_table_cell), Paragraph("04", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Industrial Sensors Principles:</b> Need, definition & classification of sensors/transducers, Engineering units & conversions, Static & dynamic characteristics, Physical principles of sensing, Material selection & guidelines.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Temperature & Pressure Sensors:</b><br/>"
                                                "• <i>Temperature:</i> RTD, Thermocouples, Thermistors, Pyrometers, Industrial thermometers, Temperature switches.<br/>"
                                                "• <i>Pressure:</i> Bourdon tube, Diaphragm, Bellows, Capacitive, Piezoelectric, LVDT, Strain gauge, McLeod gauge, Pirani gauge, Vacuum & Differential pressure measurement.", style_table_cell), Paragraph("08", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Level & Flow Sensors:</b><br/>"
                                                "• <i>Level:</i> Displacer, Float system, Bubbler, DP Cell, Ultrasonic, Capacitive, Radar, Radioactive, Laser, Fiber optic level detectors.<br/>"
                                                "• <i>Flow:</i> Orifice, Venturi, Nozzle, Pitot tube, Rotameter, Turbine, Electromagnetic, Ultrasonic, Mass flow meters.", style_table_cell), Paragraph("08", style_table_cell_center)],
        [Paragraph("<b>M5</b>", style_table_cell), Paragraph("<b>SMART Sensors, IoT & IIoT:</b> Features & applications of SMART sensors, Overview of IoT & IIoT in industry, Accelerometers, Air Quality sensors, Biomedical sensors, Gyroscopes, Gas safety & Fire detection.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M6</b>", style_table_cell), Paragraph("<b>Robotic Sensors:</b> Need & significance, Proximity sensors (Inductive, Capacitive, Optical, Ultrasonic, Hall Effect), Digital Transcoders/Encoders (Absolute & Incremental), Vision, Touch, Force/Torque sensors.", style_table_cell), Paragraph("07", style_table_cell_center)],
    ]
    t_is = Table(is_modules, colWidths=[35, 447, 40])
    t_is.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_is)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>[I.S. Lab] Industrial Sensors Laboratory Experiments</b>", style_h2))
    is_lab_text = (
        "<b>Lab Scheme (26ARPC31):</b> Minimum 8 experiments required (TW: 25 Marks, PR/OR: 25 Marks).<br/>"
        "• <b>Exp 1:</b> Study static and dynamic characteristics of sensors.<br/>"
        "• <b>Exp 2:</b> Temperature measurement using Bi-metal thermometer, RTD & Thermocouple.<br/>"
        "• <b>Exp 3:</b> Construction and working of pressure gauges & Dead Weight Testers.<br/>"
        "• <b>Exp 4:</b> Differential Pressure (DP) measurement using U-Tube Manometer.<br/>"
        "• <b>Exp 5:</b> Level measurement using Tubular Level Gauges & Float/Buoyancy sensors.<br/>"
        "• <b>Exp 6:</b> Flow measurement using Variable Head & Variable Area (Rotameter) flow meters.<br/>"
        "• <b>Exp 7:</b> Electromagnetic Flow Meter & Transmitter velocity analysis.<br/>"
        "• <b>Exp 8:</b> Familiarization & testing of SMART / IoT / IIoT Sensors and DMM/Calibrators.<br/>"
        "• <b>Exp 9:</b> Operation and testing of Robotic Proximity & Position Sensors."
    )
    story.append(Paragraph(is_lab_text, style_body))
    story.append(Spacer(1, 10))

    # SUBJECT 2: Analog Electronics & Networks
    story.append(make_subject_header("2. Analog Electronics & Networks", "Analog Electronics", "26ARPC32", "3 Theory + 1 Lab", "PCC"))
    story.append(Spacer(1, 4))

    ae_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Network Theorems:</b> Mesh and Nodal analysis with dependent sources, Supermesh and Supernode concepts, Superposition theorem, Thevenin’s theorem, Norton’s theorem, Maximum Power Transfer theorem.", style_table_cell), Paragraph("08", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Transient Analysis:</b> Initial conditions in circuit elements, First and Second order differential equations, Transients & steady state response in R-L, R-C and RLC Circuits.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Fundamentals of Network Synthesis:</b> Causality & stability, Hurwitz polynomials, Positive real functions, Synthesis of one port networks with two kinds of elements (L-C, R-C, R-L driving point impedances).", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Diode Applications & BJT:</b> Clipper & Clamper circuits, BJT device structure, physical operation, CE characteristics, BJT as an amplifier and switch, DC biasing & stability analysis.", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M5</b>", style_table_cell), Paragraph("<b>Field Effect Transistors & MOSFET:</b> JFET construction, operation, static characteristics, CS amplifier biasing & analysis, MOSFET structure, physical operation & characteristics.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M6</b>", style_table_cell), Paragraph("<b>Power Amplifiers & Regulators:</b> Series fed Class A & Class B power amplifiers, Push-Pull operation, Amplifier distortion, Power supply design using 78xx, 79xx, and LM317 IC regulators.", style_table_cell), Paragraph("06", style_table_cell_center)],
    ]
    t_ae = Table(ae_modules, colWidths=[35, 447, 40])
    t_ae.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_ae)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>[A.E. Lab] Analog Electronics & Networks Laboratory Experiments</b>", style_h2))
    ae_lab_text = (
        "<b>Lab Scheme (26ARPC32):</b> Minimum 8 experiments required (TW: 25 Marks, PR/OR: 25 Marks).<br/>"
        "• <b>Exp 1:</b> Verification of Network Theorems using constant & dependent sources.<br/>"
        "• <b>Exp 2:</b> Transient analysis for RL, RC, and RLC circuits.<br/>"
        "• <b>Exp 3:</b> Synthesis and realization of RC, RL, and LC networks.<br/>"
        "• <b>Exp 4:</b> Design and testing of Diode Clipper and Clamper circuits.<br/>"
        "• <b>Exp 5:</b> BJT CE input-output characteristics & biasing circuit parameter estimation.<br/>"
        "• <b>Exp 6:</b> JFET and MOSFET transfer and drain characteristics analysis.<br/>"
        "• <b>Exp 7:</b> Simulation of Class A Power Amplifier using software tools.<br/>"
        "• <b>Exp 8:</b> Design of fixed (78xx/79xx) and adjustable (LM317) voltage regulators."
    )
    story.append(Paragraph(ae_lab_text, style_body))
    story.append(Spacer(1, 10))

    # SUBJECT 3: Digital Electronics
    story.append(make_subject_header("3. Digital Electronics", "Digital Electronics", "26ARPC33", "2 Theory (+ Practical)", "PCC"))
    story.append(Spacer(1, 4))

    de_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Binary Systems & Boolean Reduction:</b> Binary Arithmetic, Binary codes (BCD, 8421, Gray, Excess-3, Hamming error correcting code), Boolean laws, De-Morgan’s Theorems, SOP & POS minimization, K-Map reduction, Don't care conditions.", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Combinational Logic Design:</b> Adders, Subtractors, Code converters, Parity checkers, Magnitude comparators, Multiplexer (MUX), Demultiplexer (DEMUX), Encoders & Decoders, MUX implementation.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Sequential Logic Circuits:</b> Flip Flops (SR, D, JK, Master-Slave JK, T), Flip-flop excitation & conversion, Asynchronous & Synchronous counters, Shift Registers (SISO, SIPO, PIPO, PISO, Ring, Twisted Ring).", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Programmable Logic & IC Families:</b> Introduction to FPGA architecture & programming, Digital IC operational parameters, Logic families (TTL, CMOS, MOS comparison).", style_table_cell), Paragraph("06", style_table_cell_center)],
    ]
    t_de = Table(de_modules, colWidths=[35, 447, 40])
    t_de.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_de)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>[D.E. Lab] Digital Electronics Practical & Simulation Work</b>", style_h2))
    de_lab_text = (
        "<b>Lab Mapping Tag [D.E. Lab]:</b> Practical applications & hardware experiments corresponding to 26ARPC33.<br/>"
        "• <b>Exp 1:</b> Realization of basic and universal logic gates.<br/>"
        "• <b>Exp 2:</b> Design and implementation of Code Converters (Binary to Gray, BCD to Excess-3).<br/>"
        "• <b>Exp 3:</b> Half/Full Adder and Subtractor circuits using logic gates & ICs.<br/>"
        "• <b>Exp 4:</b> Realization of boolean functions using MUX / DEMUX ICs.<br/>"
        "• <b>Exp 5:</b> Realization of Flip-Flops and conversion between SR, JK, D, T types.<br/>"
        "• <b>Exp 6:</b> Design of Asynchronous Mod-N Counter and Synchronous Up/Down Counter.<br/>"
        "• <b>Exp 7:</b> Shift Register operations (Serial/Parallel In/Out, Ring & Johnson counter).<br/>"
        "• <b>Exp 8:</b> Basic FPGA programming and digital logic simulation."
    )
    story.append(Paragraph(de_lab_text, style_body))
    story.append(Spacer(1, 10))

    # SUBJECT 4: Robot Mechanics
    story.append(make_subject_header("4. Fundamentals of Robotic Mechanical Systems", "Robot Mechanics", "26ARPC34", "2 Theory", "PCC"))
    story.append(Spacer(1, 4))

    rm_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Mechanical Foundations for Robotics:</b> Links, joints, frames, manipulators, Stress-strain relations, Hooke's law, Young's modulus, Poisson's ratio, Factor of safety, Engineering materials in robotics (steel, aluminum, composites, plastics, elastomers).", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Kinematics & Mechanisms:</b> Kinematic pairs, chains, Grubler's criterion, Degrees of freedom, Planar vs spatial mechanisms, Four-bar and Slider-crank mechanisms, Relative velocity polygon method, Instantaneous Centre of Rotation (ICR).", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Gear Systems for Robotics:</b> Spur, bevel, worm gears, Gear tooth profiles, Law of gearing, Velocity ratios, Simple and compound gear trains, Applications in robotic manipulators & mobile robots.", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Belt Drives & Power Transmission:</b> Flat, V-belts, Timing belt drives, Velocity ratio, Slip and creep, Belt tension ratio, Power transmission calculations in robotic motion systems & conveyors.", style_table_cell), Paragraph("06", style_table_cell_center)],
    ]
    t_rm = Table(rm_modules, colWidths=[35, 447, 40])
    t_rm.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_rm)
    story.append(Spacer(1, 10))

    # SUBJECT 5: Maths (Advanced Mathematics for AI & ML)
    story.append(make_subject_header("5. Advanced Mathematics for AI & ML", "Maths", "26ARMM31", "3 Theory + 1 Tut", "MDM"))
    story.append(Spacer(1, 4))

    math_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Probability & Random Variables:</b> Bayes' theorem, Discrete & continuous random variables, PMF/PDF, Expectation, Variance, Binomial, Poisson & Normal distributions in sensor data & robotics.", style_table_cell), Paragraph("10", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Hypothesis Testing & Statistical Inference:</b> Testing of hypothesis, Z-tests (proportions, means), Student's t-test, F-test, Chi-square test for goodness of fit & independence.", style_table_cell), Paragraph("07", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Eigenvalues, Eigenvectors & Matrix Theory:</b> Characteristic equation, Cayley-Hamilton theorem, Matrix diagonalisation, System stability in robotic control.", style_table_cell), Paragraph("05", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Laplace & Z-Transform Techniques:</b> Laplace transform properties, Shifting theorems, Z-transforms, Region of Convergence (ROC), Inverse transforms for control system analysis.", style_table_cell), Paragraph("08", style_table_cell_center)],
        [Paragraph("<b>M5</b>", style_table_cell), Paragraph("<b>Fourier Series & Fourier Transforms:</b> Euler's formulae, Fourier series for even/odd functions, Fourier transforms, Signal filtering & sensor noise reduction.", style_table_cell), Paragraph("05", style_table_cell_center)],
        [Paragraph("<b>M6</b>", style_table_cell), Paragraph("<b>Graph Theory & Robotic Navigation:</b> Graph isomorphism, Breadth First Search (BFS), Depth First Search (DFS), Path planning & autonomous navigation algorithms.", style_table_cell), Paragraph("04", style_table_cell_center)],
    ]
    t_math = Table(math_modules, colWidths=[35, 447, 40])
    t_math.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_math)
    story.append(Spacer(1, 10))

    # SUBJECT 6: Financial Management
    story.append(make_subject_header("6. Financial Management", "Financial Management", "26AREM31", "2 Theory", "HSSM"))
    story.append(Spacer(1, 4))

    fm_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Indian Financial System:</b> Financial instruments (Shares, Debentures, T-Bills, Commercial Papers), Capital Markets, Money Markets, Foreign Exchange, Commercial Banks & Stock Exchanges.", style_table_cell), Paragraph("08", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Financial Risk & Returns:</b> Single & Portfolio Risk/Return calculations, Time Value of Money (PV, FV, Ordinary Annuity, Continuous Compounding).", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M3</b>", style_table_cell), Paragraph("<b>Corporate Finance & Ratio Analysis:</b> Balance Sheet, P&L Account, Cash Flow Statement, Financial Ratio Analysis (Liquidity, Profitability, Solvency, Turnover ratios).", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M4</b>", style_table_cell), Paragraph("<b>Introduction to Personal Taxation:</b> Assessment Year, Previous Year, Heads of Income, Gross Total Income, Individual Tax Calculation Schemes.", style_table_cell), Paragraph("06", style_table_cell_center)],
    ]
    t_fm = Table(fm_modules, colWidths=[35, 447, 40])
    t_fm.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_fm)
    story.append(Spacer(1, 10))

    # SUBJECT 7: Professional Communication and Ethics-II (PCE)
    story.append(make_subject_header("7. Professional Communication & Ethics-II", "PCE", "26AREM32", "1 Theory + 1 TW", "HSSM"))
    story.append(Spacer(1, 4))

    pce_modules = [
        [Paragraph("Module", style_table_header), Paragraph("Chapter & Content Description", style_table_header), Paragraph("Hrs", style_table_header)],
        [Paragraph("<b>M1</b>", style_table_cell), Paragraph("<b>Advanced Technical Writing:</b> Project/Problem Based Learning (PBL), Solicited & Unsolicited Proposals, Structure of Formal Reports (Prefatory, Main body, Back matter), APA/MLA/IEEE Referencing, Plagiarism checks.", style_table_cell), Paragraph("06", style_table_cell_center)],
        [Paragraph("<b>M2</b>", style_table_cell), Paragraph("<b>Employment Skills & Professional Ethics:</b> Resumes (Chronological/Functional), Cover Letters, Statement of Purpose (SOP), Group Discussions (GD) etiquette, Personal Interviews (Structured, Behavioral, Case-based).", style_table_cell), Paragraph("06", style_table_cell_center)],
    ]
    t_pce = Table(pce_modules, colWidths=[35, 447, 40])
    t_pce.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_pce)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # 4. REFERENCE BOOKS & TEXTBOOKS SUMMARY
    # ---------------------------------------------------------
    story.append(Paragraph("4. Recommended Textbooks & Reference Books", style_h1))
    
    books_data = [
        [Paragraph("Subject", style_table_header), Paragraph("Key Recommended Books & Authors", style_table_header)],
        [Paragraph("<b>Industrial Sensors</b>", style_table_cell), Paragraph("1. B.C. Nakra, K.K. Chaudhary — <i>Instrumentation, Measurement and Analysis</i> (Tata McGraw-Hill).<br/>2. D. Patranabis — <i>Sensors and Transducers</i> (PHI).<br/>3. A.K. Sawhney — <i>Electrical & Electronic Measurement & Instrumentation</i>.", style_table_cell)],
        [Paragraph("<b>Analog Electronics</b>", style_table_cell), Paragraph("1. Franklin F. Kuo — <i>Network Analysis and Synthesis</i> (Wiley).<br/>2. Robert L. Boylestad — <i>Electronic Devices and Circuit Theory</i> (PHI).<br/>3. M.E. Van Valkenburg — <i>Network Analysis</i>.", style_table_cell)],
        [Paragraph("<b>Digital Electronics</b>", style_table_cell), Paragraph("1. M. Morris Mano — <i>Digital Design</i> (Prentice Hall).<br/>2. R.P. Jain — <i>Modern Digital Electronics</i> (Tata McGraw-Hill).<br/>3. A. Anand Kumar — <i>Fundamentals of Digital Circuits</i>.", style_table_cell)],
        [Paragraph("<b>Robot Mechanics</b>", style_table_cell), Paragraph("1. S.S. Rattan — <i>Theory of Machines</i> (Tata McGraw-Hill).<br/>2. V.B. Bhandari — <i>Design of Machine Elements</i>.<br/>3. Saeed B. Niku — <i>Introduction to Robotics</i>.", style_table_cell)],
        [Paragraph("<b>Maths (AI/ML)</b>", style_table_cell), Paragraph("1. R.E. Walpole, R.H. Myers — <i>Probability & Statistics for Engineers</i> (Pearson).<br/>2. B.S. Grewal — <i>Higher Engineering Mathematics</i> (Khanna).<br/>3. Erwin Kreyszig — <i>Advanced Engineering Mathematics</i>.", style_table_cell)],
        [Paragraph("<b>Financial Mgmt</b>", style_table_cell), Paragraph("1. Eugene F. Brigham, Joel F. Houston — <i>Fundamentals of Financial Management</i> (Cengage).<br/>2. M.Y. Khan — <i>Indian Financial System</i> (McGraw-Hill).", style_table_cell)],
        [Paragraph("<b>PCE</b>", style_table_cell), Paragraph("1. Lesiker & Petit — <i>Report Writing for Business</i> (McGraw-Hill).<br/>2. Bovee & Thill — <i>Business Communication Today</i> (Pearson).", style_table_cell)],
    ]
    t_books = Table(books_data, colWidths=[120, 402])
    t_books.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_books)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # 5. EXAMINATION & EVALUATION SCHEME SUMMARY
    # ---------------------------------------------------------
    story.append(Paragraph("5. Examination & Evaluation Scheme Rules", style_h1))
    
    eval_text = (
        "<b>Internal Assessment (IA):</b> Total 40 Marks per course (20 Marks Mid-Term Test + 20 Marks Continuous Assessment).<br/>"
        "• <i>Mid-Term Test:</i> 1 Hour duration, conducted upon ~50% completion of syllabus.<br/>"
        "• <i>Continuous Assessment Rubrics (20 Marks):</i> MOOC/NPTEL certificates (10m), Hackathon/Competition wins (10m), "
        "Content beyond syllabus (10m), Proof of Concept (10m), Mini-Project/Virtual Lab (10m), GATE Assignments/Tutorials (10m), Quiz/MCQs (5m).<br/><br/>"
        "<b>End Semester Examination (ESE):</b><br/>"
        "• 60 Marks theory paper (3 Hours) consisting of 5 questions carrying 20 marks each (3 to be solved).<br/>"
        "• For 2-credit courses (Financial Management / Robot Mechanics), ESE paper is 30/60 marks accordingly."
    )
    story.append(Paragraph(eval_text, style_body))

    # Build PDF with dynamic header/footer
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {OUTPUT_PDF}")

if __name__ == '__main__':
    create_syllabus_pdf()
