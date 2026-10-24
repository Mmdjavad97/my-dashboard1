"""Persian project ledger, per-transaction attachments, and printable reports."""
from __future__ import annotations

import base64
import copy
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import jdatetime
import streamlit as st

CATEGORIES = ["متریال", "اجرت", "خدمات", "سایر", "دریافتی"]
EXPENSE_CATEGORIES = CATEGORIES[:4]
TYPE_LABELS = {"Income": "دریافتی", "Expense": "هزینه"}
FONT_PATH = Path(__file__).with_name("B-NAZANIN.TTF")
REPORT_LOGO_PATH = Path(__file__).with_name("financial_report_logo.png")
ENGLISH_LABELS = {"بودجه پروژه": "Budget", "دریافتی": "Income", "هزینه‌ها": "Expenses", "مانده نقدی": "Cash balance", "بودجه باقی‌مانده": "Budget remaining", "متریال": "Material", "اجرت": "Wage", "خدمات": "Service", "سایر": "Other"}
DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
ASCII_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def fa(value):
    return str(value).translate(DIGITS)


def rial(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError("Amounts must be non-negative whole numbers.")
    return int(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def solar_date(value=None):
    """Normalize legacy Gregorian and Persian-digit dates into Solar Hijri."""
    if value is None:
        today = datetime.now(ZoneInfo("Asia/Tehran")).date()
        return jdatetime.date.fromgregorian(date=today).strftime("%Y/%m/%d")
    raw = str(value).strip().translate(ASCII_DIGITS).replace("-", "/")
    try:
        year, month, day = map(int, raw.split("/"))
        if year >= 1700:
            return jdatetime.date.fromgregorian(date=datetime(year, month, day).date()).strftime("%Y/%m/%d")
        return jdatetime.date(year, month, day).strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        raise ValueError("Enter a valid Solar Hijri date, for example 1405/08/02.") from None


def category_for(row):
    category = row.get("category", "").strip()
    if category in CATEGORIES:
        return category
    if row.get("type") == "Income":
        return "دریافتی"
    aliases = {"material": "متریال", "materials": "متریال", "متریال": "متریال", "wage": "اجرت", "wages": "اجرت", "labor": "اجرت", "labour": "اجرت", "service": "خدمات", "services": "خدمات"}
    return aliases.get(category.casefold(), "سایر")


def totals(project):
    income = sum(rial(row["amount"]) for row in project["transactions"] if row["type"] == "Income")
    expenses = sum(rial(row["amount"]) for row in project["transactions"] if row["type"] == "Expense")
    categories = {category: sum(rial(row["amount"]) for row in project["transactions"] if row["type"] == "Expense" and category_for(row) == category) for category in EXPENSE_CATEGORIES}
    budget = rial(project["budget"])
    return [("بودجه پروژه", budget), ("دریافتی", income), ("هزینه‌ها", expenses), ("مانده نقدی", income - expenses), ("بودجه باقی‌مانده", budget - expenses)], categories


def blank_row():
    return {"id": uuid4().hex, "date": solar_date(), "type": "Expense", "category": "سایر", "amount": "0", "description": "", "attachments": []}


def make_draft(project):
    rows = copy.deepcopy(project["transactions"])
    for row in rows:
        row.setdefault("id", uuid4().hex)
        row.setdefault("attachments", [])
        if row.get("category") != category_for(row):
            row.setdefault("original_category", row.get("category", ""))
        row["category"] = category_for(row)
        try:
            row["date"] = solar_date(row["date"])
        except ValueError:
            pass  # Keep an invalid legacy value visible for correction.
    return {"budget": rial(project["budget"]), "notes": project["notes"], "rows": rows or [blank_row()]}


def validate_rows(rows):
    result = []
    for index, row in enumerate(rows, 1):
        amount = rial(row["amount"])
        if not amount and not row["description"].strip() and not row.get("attachments"):
            continue
        if amount <= 0:
            raise ValueError(f"Row {index}: the amount must be greater than zero.")
        if row["category"] not in CATEGORIES or row["type"] not in TYPE_LABELS:
            raise ValueError(f"Row {index}: choose a transaction type and category.")
        if (row["type"] == "Income") != (row["category"] == "دریافتی"):
            raise ValueError(f"Row {index}: choose دریافتی for both type and category for income; other categories are expenses.")
        result.append({**row, "date": solar_date(row["date"]), "amount": str(amount), "description": row["description"].strip()})
    return result


def report_brand(logo_path=None):
    """Use the supplied logo's dominant ink color without altering the image."""
    from PIL import Image
    path = Path(logo_path) if logo_path is not None else REPORT_LOGO_PATH
    primary = (32, 63, 104)
    logo = None
    if path.is_file():
        logo = path
        with Image.open(path) as image:
            sample = image.convert("RGBA")
            sample.thumbnail((96, 96))
            pixels = [rgb[:3] for rgb in sample.getdata() if rgb[3] > 128 and min(rgb[:3]) < 235]
        colored = [rgb for rgb in pixels if max(rgb) - min(rgb) > 25]
        buckets = {}
        for rgb in colored or pixels:
            key = tuple(channel // 24 for channel in rgb)
            buckets.setdefault(key, []).append(rgb)
        if buckets:
            dominant = max(buckets.values(), key=len)
            primary = tuple(round(sum(rgb[index] for rgb in dominant) / len(dominant)) for index in range(3))
    def hex_color(rgb):
        return "#" + "".join(f"{round(channel):02x}" for channel in rgb)
    header = primary
    def luminance(rgb):
        values = [channel / 255 for channel in rgb]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in values]
        return sum(value * weight for value, weight in zip(linear, [.2126, .7152, .0722]))
    while 1.05 / (luminance(header) + .05) < 4.5:
        header = tuple(channel * .9 for channel in header)
    return {"logo": logo, "primary": hex_color(primary), "header": hex_color(header),
            "tint": hex_color(tuple(255 * .94 + channel * .06 for channel in primary)),
            "line": hex_color(tuple(255 * .78 + channel * .22 for channel in primary))}


def pdf_report(project, pdf_runs, logo_path=None):
    """A paginated A4 report with wrapped RTL cells and repeated table headers."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    # The shared helper registers Nazanin and supplies Helvetica for Latin data.
    pdf_runs("")
    sans_fonts = {"regular": "RNGFinancialSans", "bold": "RNGFinancialSansBold"}
    for name, filename in [(sans_fonts["regular"], "Vera.ttf"), (sans_fonts["bold"], "VeraBd.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(Path(reportlab.__file__).parent / "fonts" / filename)))
    brand = report_brand(logo_path)
    page_size = landscape(A4)
    width = page_size[0] - 72
    styles = {
        "title": ParagraphStyle("financial_title", fontName="RNGBNazanin", fontSize=20, leading=25, alignment=TA_RIGHT, textColor=colors.white),
        "body": ParagraphStyle("financial_body", fontName="RNGBNazanin", fontSize=13, leading=19, alignment=TA_RIGHT, textColor=colors.HexColor("#243e62")),
        "head": ParagraphStyle("financial_head", fontName="RNGBNazanin", fontSize=13, leading=19, alignment=TA_CENTER, textColor=colors.white),
        "center": ParagraphStyle("financial_center", fontName="RNGBNazanin", fontSize=13, leading=19, alignment=TA_CENTER, textColor=colors.HexColor("#243e62")),
    }

    def paragraph(text, available, kind="body"):
        lines = []
        font_size = styles[kind].fontSize
        has_persian = any("\u0600" <= ch <= "\u08ff" or "\ufb50" <= ch <= "\ufeff" for ch in str(text))
        def runs(visual):
            if not has_persian:
                return [(sans_fonts["bold"] if kind == "title" else sans_fonts["regular"], visual)]
            return [(sans_fonts["regular"] if name == "Helvetica" else name, part) for name, part in pdf_runs(visual)]
        for logical_line in str(text).splitlines() or [""]:
            current = ""
            # Split oversized tokens too, so references/filenames cannot overflow.
            for word in logical_line.split():
                fragments = [word]
                if sum(pdfmetrics.stringWidth(t, f, font_size) for f, t in runs(get_display(arabic_reshaper.reshape(word)))) > available - 12:
                    fragments = list(word)
                for fragment in fragments:
                    candidate = (current + (" " if current and len(fragments) == 1 else "") + fragment)
                    visual = get_display(arabic_reshaper.reshape(candidate))
                    if current and sum(pdfmetrics.stringWidth(t, f, font_size) for f, t in runs(visual)) > available - 12:
                        lines.append(current)
                        current = fragment
                    else:
                        current = candidate
            lines.append(current)
        markup = []
        for line in lines:
            visual = get_display(arabic_reshaper.reshape(line))
            markup.append("".join(f'<font name="{font}">{escape(part)}</font>' for font, part in runs(visual)))
        style = styles[kind]
        if not has_persian:
            style = ParagraphStyle(f"english_{kind}", parent=style, fontName=sans_fonts["regular"], alignment=0 if kind == "body" else style.alignment)
        return Paragraph("<br/>".join(markup) or " ", style)

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=36, rightMargin=36, topMargin=96, bottomMargin=42, title=f'Financial report - {project["title"]}', author="RNG Projects")
    story = []
    summary, category_totals = totals(project)
    for pairs in [summary, list(category_totals.items())]:
        column_width = width / len(pairs)
        cards = [paragraph(f'{ENGLISH_LABELS[label]}\n{amount:,} IRR', column_width, "center") for label, amount in pairs]
        table = Table([cards], colWidths=[column_width] * len(pairs))
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(brand["tint"])), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(brand["line"])), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
        story += [table, Spacer(1, 12)]
    widths = [width * ratio for ratio in [.055, .365, .20, .105, .09, .12, .065]]
    headers = ["پیوست", "شرح / مرجع", "مبلغ (ریال)", "دسته‌بندی", "نوع", "تاریخ", "ردیف"]
    data = [[paragraph(label, cell_width, "head") for label, cell_width in zip(headers, widths)]]
    for index, row in enumerate(project["transactions"], 1):
        try:
            date = solar_date(row["date"])
        except ValueError:
            date = row["date"]
        values = [fa(len(row.get("attachments", []))), row["description"], fa(f'{rial(row["amount"]):,}'), category_for(row), TYPE_LABELS[row["type"]], fa(date), fa(index)]
        data.append([paragraph(value, cell_width, "body" if index in (1, 2) else "center") for index, (value, cell_width) in enumerate(zip(values, widths))])
    if len(data) == 1:
        data.append([paragraph("هنوز تراکنشی ثبت نشده است." if index == 1 else "", cell_width) for index, cell_width in enumerate(widths)])
    ledger = Table(data, colWidths=widths, repeatRows=1, hAlign="RIGHT", splitInRow=1)
    ledger.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(brand["header"])), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(brand["tint"])]), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(brand["line"])), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.append(ledger)
    if project.get("notes"):
        story += [Spacer(1, 16), paragraph("Financial notes", width), paragraph(project["notes"], width)]

    def decorate(canvas, document):
        from reportlab.lib.utils import ImageReader
        canvas.setFillColor(colors.HexColor(brand["header"]))
        canvas.rect(0, page_size[1] - 78, page_size[0], 78, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(brand["primary"]))
        canvas.rect(0, page_size[1] - 81, page_size[0], 3, fill=1, stroke=0)
        title_x = 36
        title_width = width
        if brand["logo"] is not None:
            canvas.setFillColor(colors.white)
            canvas.roundRect(30, page_size[1] - 65, 132, 52, 6, fill=1, stroke=0)
            canvas.drawImage(ImageReader(str(brand["logo"])), 38, page_size[1] - 59, width=116, height=40, preserveAspectRatio=True, anchor="c", mask="auto")
            title_x = 182
            title_width = page_size[0] - title_x - 36
        title = paragraph(f'Financial report — {project["title"]}', title_width, "title")
        _, height = title.wrap(title_width, 52)
        while height > 52 and styles["title"].fontSize > 12:
            styles["title"].fontSize -= 1
            styles["title"].leading -= 1
            title = paragraph(f'Financial report — {project["title"]}', title_width, "title")
            _, height = title.wrap(title_width, 52)
        title.drawOn(canvas, title_x, page_size[1] - 20 - height)
        footer = paragraph(f'Solar Hijri: {solar_date()}   |   Page {document.page}   |   All amounts in IRR / Rial', width, "center")
        footer.wrap(width, 30)
        footer.drawOn(canvas, 36, 15)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()


def render_financial(projects, project_id, save, pdf_runs):
    project = projects[project_id]
    draft_key = f"rng_financial_draft_{project_id}"
    st.session_state.setdefault(draft_key, make_draft(project))
    draft = st.session_state[draft_key]
    font_data = base64.b64encode(FONT_PATH.read_bytes()).decode("ascii")
    st.markdown('<div id="rng-financial-ledger-marker"></div>', unsafe_allow_html=True)
    st.markdown('''<style>
    @font-face { font-family: 'Financial Nazanin'; src: url('data:font/ttf;base64,__FONT_DATA__') format('truetype'); font-display: swap; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace { direction: ltr; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace p,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace label,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace input,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace textarea,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace button,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace h3,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace [data-testid="stMarkdownContainer"] { font-family: Arial, Tahoma, sans-serif !important; color: #243e62 !important; font-size: 14px; font-style: normal !important; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace input,
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace textarea { direction: ltr; text-align: left; }
    .st-key-rng_financial_workspace [data-testid="stAlertContainer"] { background: #edf3fb; color: #243e62; }
    .st-key-rng_financial_workspace [data-testid="stFileUploaderDropzone"] { background: #edf3fb; color: #243e62; }
    .st-key-rng_financial_workspace button { background: #f2f6fc; color: #284f7f; border-color: #d6e2f2; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace button[kind^="primary"],
    .stApp:has(#rng-financial-ledger-marker) .st-key-rng_financial_workspace button[kind^="primary"] p { background: #214b7f; color: #fff !important; }
    .rng-finance-summary { display: grid; direction: ltr; text-align: left; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 8px 0 12px; }
    .rng-finance-summary.expenses { grid-template-columns: repeat(4, 1fr); margin-bottom: 24px; }
    .rng-finance-summary > div { background: #fff; border: 1px solid #d6e2f2; border-radius: 15px; padding: 16px; min-width: 0; }
    .rng-finance-summary.expenses > div { background: #eaf1fb; border-top: 3px solid #86a5cd; }
    .rng-finance-summary span, .rng-finance-summary small { display: block; font-family: Arial, Tahoma, sans-serif; color: #587193; font-size: 12px; line-height: 1.5; }
    .rng-finance-summary strong { display: block; font-family: Arial, Tahoma, sans-serif; font-size: 23px; color: #203f68; margin: 8px 0; overflow-wrap: anywhere; }
    .st-key-financial_grid { --finance-cols: 44px 116px 112px 126px 190px minmax(230px, 1fr) 56px 48px; overflow-x: auto; width: 100%; max-width: 100%; direction: rtl; border: 1px solid #d5e1ef; border-radius: 12px; background: #fff; gap: 0 !important; }
    .rng-finance-grid-head { display: grid; grid-template-columns: var(--finance-cols); direction: rtl; min-width: 1000px; min-height: 54px; align-items: center; background: #203f68; color: #fff; padding: 12px 8px; gap: 8px; font-family: 'Financial Nazanin', Tahoma, sans-serif; font-size: 20px; text-align: center; }
    .rng-finance-grid-head > div:nth-child(6) { text-align: right; padding-right: 12px; }
    [class*="st-key-finance_row_"] { min-width: 1000px; min-height: 66px; padding: 10px 8px; margin: 0 !important; border-bottom: 1px solid #e0e8f3; }
    [class*="st-key-finance_row_"]:nth-child(even) { background: #f4f7fc; }
    [class*="st-key-finance_row_"] [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: var(--finance-cols); direction: rtl; gap: 8px; align-items: center; }
    [class*="st-key-finance_row_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 0 !important; width: 100% !important; }
    [class*="st-key-finance_row_"] [data-testid="stElementContainer"] { margin-bottom: 0; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid input,
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid button,
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid p,
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid label,
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid [data-testid="stMarkdownContainer"] { font-family: 'Financial Nazanin', Tahoma, sans-serif !important; color: #243e62 !important; font-size: 20px; }
    .stApp:has(#rng-financial-ledger-marker) .st-key-financial_grid input { min-height: 44px !important; height: 44px; direction: rtl; text-align: right; }
    .st-key-financial_grid [data-testid="stNumberInput"] button { display: none; }
    .st-key-financial_grid [data-testid="stNumberInput"] input { width: 100% !important; font-size: 23px !important; }
    .st-key-financial_grid [data-testid="stSelectbox"] button { min-height: 44px; }
    .st-key-financial_grid [data-testid="stTextInput"] > div,
    .st-key-financial_grid [data-testid="stNumberInput"] > div { background: #f8faff; }
    .st-key-financial_grid [data-testid="stColumn"]:first-child p { text-align: center; line-height: 44px; margin: 0; }
    body:has(#rng-financial-ledger-marker) [role="option"] { font-family: 'Financial Nazanin', Tahoma, sans-serif !important; font-size: 20px; direction: rtl; color: #243e62; background: #fff; }
    .st-key-rng_financial_workspace [data-testid="stForm"] { min-width: 0; }
    @media(max-width: 900px) { .rng-finance-summary { grid-template-columns: repeat(3, 1fr); } .rng-finance-summary.expenses { grid-template-columns: repeat(2, 1fr); } }
    @media(max-width: 600px) { .rng-finance-summary { grid-template-columns: repeat(2, 1fr); gap: 8px; } .rng-finance-summary > div { padding: 12px; } .rng-finance-summary strong { font-size: 20px; } }
    </style>'''.replace('__FONT_DATA__', font_data), unsafe_allow_html=True)
    with st.container(key="rng_financial_workspace"):
        if st.session_state.pop(f"rng_financial_saved_{project_id}", False):
            st.success("Financial records and attachments saved.")
        summary, categories = totals(project)
        for pairs, extra_class in [(summary, ""), (list(categories.items()), "expenses")]:
            st.markdown(f'<div class="rng-finance-summary {extra_class}">' + ''.join(
                f'<div><span>{ENGLISH_LABELS[label]}</span><strong>{amount:,}</strong><small>IRR · Rial</small></div>' for label, amount in pairs
            ) + '</div>', unsafe_allow_html=True)
        requested_attachment = None
        requested_delete = None
        with st.form(f"financial_detail_{project_id}"):
            budget = st.number_input("Project budget (IRR / Rial)", min_value=0, value=int(draft["budget"]), step=1, format="%d", key=f"financial_budget_{project_id}")
            st.subheader("Income & expenses")
            st.caption("Dates use the Solar Hijri calendar. All amounts are in Rial. Use + beside a row to attach an image or PDF. Scroll sideways on smaller screens.")
            updated_rows = []
            with st.container(key="financial_grid"):
                st.markdown('<div class="rng-finance-grid-head"><div>ردیف</div><div>تاریخ</div><div>نوع</div><div>دسته‌بندی</div><div>مبلغ (ریال)</div><div>شرح / مرجع</div><div>پیوست</div><div>حذف</div></div>', unsafe_allow_html=True)
                for index, row in enumerate(draft["rows"], 1):
                    row_id = row["id"]
                    prefix = f"finance_{project_id}_{row_id}"
                    with st.container(key=f"finance_row_{row_id}"):
                        columns = st.columns([.4, 1.1, .9, 1, 1.2, 2.4, .45, .45])
                        with columns[0]: st.write(fa(index))
                        with columns[1]: date = st.text_input(f"تاریخ ردیف {fa(index)}", value=fa(row["date"]), key=f"{prefix}_date", label_visibility="collapsed")
                        with columns[2]: transaction_type = st.selectbox(f"نوع ردیف {fa(index)}", list(TYPE_LABELS), index=list(TYPE_LABELS).index(row["type"]), format_func=TYPE_LABELS.get, key=f"{prefix}_type", label_visibility="collapsed")
                        with columns[3]: category = st.selectbox(f"دسته‌بندی ردیف {fa(index)}", CATEGORIES, index=CATEGORIES.index(row["category"]), key=f"{prefix}_category", label_visibility="collapsed")
                        with columns[4]: amount = st.number_input(f"مبلغ ردیف {fa(index)}", min_value=0, value=rial(row["amount"]), step=1, format="%d", key=f"{prefix}_amount", label_visibility="collapsed")
                        with columns[5]: description = st.text_input(f"شرح ردیف {fa(index)}", value=row["description"], key=f"{prefix}_description", label_visibility="collapsed")
                        with columns[6]:
                            count = len(row.get("attachments", []))
                            if st.form_submit_button("+" + (f" {fa(count)}" if count else ""), key=f"{prefix}_attach", help=f"افزودن پیوست برای ردیف {fa(index)}", use_container_width=True): requested_attachment = row_id
                        with columns[7]:
                            if st.form_submit_button("×", key=f"{prefix}_delete", help=f"حذف ردیف {fa(index)}", use_container_width=True): requested_delete = row_id
                        updated_rows.append({**row, "date": date, "type": transaction_type, "category": category, "amount": str(amount), "description": description})
            notes = st.text_area("Financial notes", value=draft["notes"], key=f"financial_notes_{project_id}")
            add_row = st.form_submit_button("+ Add row", key=f"finance_add_row_{project_id}")
            submitted = st.form_submit_button("Save financial records", key=f"finance_save_{project_id}", type="primary", use_container_width=True)
        if requested_attachment or requested_delete or add_row or submitted:
            draft.update(budget=budget, notes=notes, rows=updated_rows)
        if requested_attachment:
            st.session_state[f"rng_financial_attachment_{project_id}"] = requested_attachment
            st.rerun()
        if requested_delete:
            st.session_state[f"rng_financial_delete_{project_id}"] = requested_delete
            st.rerun()
        if add_row:
            draft["rows"].append(blank_row())
            st.rerun()
        if submitted:
            try:
                records = validate_rows(draft["rows"])
                projects[project_id] = {**project, "currency": "IRR", "budget": str(rial(budget)), "notes": notes.strip(), "transactions": records}
                try:
                    save()
                except Exception:
                    projects[project_id] = project
                    st.error("Could not save. Your draft is still available; please try again.")
                else:
                    draft.update(budget=rial(budget), notes=notes.strip(), rows=copy.deepcopy(records) or [blank_row()])
                    st.session_state[f"rng_financial_saved_{project_id}"] = True
                    st.rerun()
            except (ValueError, InvalidOperation) as exc:
                st.error(str(exc))
        delete_id = st.session_state.get(f"rng_financial_delete_{project_id}")
        if delete_id:
            st.warning("Delete this row and its attachments? Save financial records to commit this change.")
            yes, cancel = st.columns(2)
            with yes:
                if st.button("Yes, delete row", key=f"finance_confirm_delete_{project_id}"):
                    draft["rows"] = [row for row in draft["rows"] if row["id"] != delete_id] or [blank_row()]
                    st.session_state[f"rng_financial_delete_{project_id}"] = None
                    st.rerun()
            with cancel:
                if st.button("Cancel", key=f"finance_cancel_delete_{project_id}"):
                    st.session_state[f"rng_financial_delete_{project_id}"] = None
                    st.rerun()
        active_id = st.session_state.get(f"rng_financial_attachment_{project_id}")
        active = next((row for row in draft["rows"] if row["id"] == active_id), None)
        if active:
            number = next(index for index, row in enumerate(draft["rows"], 1) if row["id"] == active_id)
            with st.container(border=True):
                st.subheader(f"Attachments for row {number}")
                st.caption("Choose images or PDFs from your computer or phone. Up to 2 MB per file and 20 MB total per project.")
                with st.form(f"finance_attachment_form_{project_id}_{active_id}", clear_on_submit=True):
                    uploads = st.file_uploader("Choose images or PDFs", type=["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"], accept_multiple_files=True, max_upload_size=2)
                    upload_submit = st.form_submit_button("Add attachments", type="primary")
                if upload_submit:
                    files = [{"id": uuid4().hex, "name": file.name, "mime": file.type or "application/octet-stream", "size": len(file.getvalue()), "data": base64.b64encode(file.getvalue()).decode("ascii")} for file in uploads]
                    total_size = sum(file["size"] for row in draft["rows"] for file in row.get("attachments", []))
                    if not files:
                        st.error("Choose a file first.")
                    elif any(file["size"] > 2 * 1024 * 1024 for file in files) or total_size + sum(file["size"] for file in files) > 20 * 1024 * 1024:
                        st.error("The selected files exceed the upload limit.")
                    else:
                        active["attachments"].extend(files)
                        st.success("Attachments added. Click Save financial records to commit your changes.")
                for file in active.get("attachments", []):
                    st.download_button(f'Download {file["name"]}', data=base64.b64decode(file["data"]), file_name=file["name"], mime=file["mime"], key=f'finance_download_{file["id"]}')
                    if st.button("Remove attachment", key=f'finance_remove_file_{file["id"]}'):
                        active["attachments"] = [item for item in active["attachments"] if item["id"] != file["id"]]
                        st.rerun()
                if st.button("Close attachments", key=f"finance_close_upload_{project_id}"):
                    st.session_state[f"rng_financial_attachment_{project_id}"] = None
                    st.rerun()
        st.caption("The PDF report uses your latest saved financial records.")
        try:
            pdf = pdf_report(project, pdf_runs)
            st.download_button("Download financial report (PDF)", data=pdf, file_name=f"financial-report-{project_id}.pdf", mime="application/pdf", key=f"finance_pdf_{project_id}", use_container_width=True)
        except Exception:
            st.error("Could not create the PDF report. Please try again.")
