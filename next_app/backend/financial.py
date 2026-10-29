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
CATEGORIES = ['متریال', 'اجرت', 'خدمات', 'سایر', 'دریافتی']
EXPENSE_CATEGORIES = CATEGORIES[:4]
TYPE_LABELS = {'Income': 'دریافتی', 'Expense': 'هزینه'}
FONT_PATH = Path(__file__).resolve().parents[2] / "B-NAZANIN.TTF"
REPORT_LOGO_PATH = Path(__file__).resolve().parents[2] / 'assets' / 'RNG Logo.png'
ENGLISH_LABELS = {'بودجه پروژه': 'Budget', 'دریافتی': 'Income', 'هزینه\u200cها': 'Expenses', 'مانده نقدی': 'Cash balance', 'بودجه باقی\u200cمانده': 'Budget remaining', 'متریال': 'Material', 'اجرت': 'Wage', 'خدمات': 'Service', 'سایر': 'Other'}
DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
ASCII_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def fa(value):
    return str(value).translate(DIGITS)

def rial(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError('Amounts must be non-negative whole numbers.')
    return int(number.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def solar_date(value=None):
    """Normalize legacy Gregorian and Persian-digit dates into Solar Hijri."""
    if value is None:
        today = datetime.now(ZoneInfo('Asia/Tehran')).date()
        return jdatetime.date.fromgregorian(date=today).strftime('%Y/%m/%d')
    raw = str(value).strip().translate(ASCII_DIGITS).replace('-', '/')
    try:
        year, month, day = map(int, raw.split('/'))
        if year >= 1700:
            return jdatetime.date.fromgregorian(date=datetime(year, month, day).date()).strftime('%Y/%m/%d')
        return jdatetime.date(year, month, day).strftime('%Y/%m/%d')
    except (ValueError, TypeError):
        raise ValueError('Enter a valid Solar Hijri date, for example 1405/08/02.') from None

def category_for(row):
    category = row.get('category', '').strip()
    if category in CATEGORIES:
        return category
    if row.get('type') == 'Income':
        return 'دریافتی'
    aliases = {'material': 'متریال', 'materials': 'متریال', 'متریال': 'متریال', 'wage': 'اجرت', 'wages': 'اجرت', 'labor': 'اجرت', 'labour': 'اجرت', 'service': 'خدمات', 'services': 'خدمات'}
    return aliases.get(category.casefold(), 'سایر')

def totals(project):
    income = sum((rial(row['amount']) for row in project['transactions'] if row['type'] == 'Income'))
    expenses = sum((rial(row['amount']) for row in project['transactions'] if row['type'] == 'Expense'))
    categories = {category: sum((rial(row['amount']) for row in project['transactions'] if row['type'] == 'Expense' and category_for(row) == category)) for category in EXPENSE_CATEGORIES}
    budget = rial(project['budget'])
    return ([('بودجه پروژه', budget), ('دریافتی', income), ('هزینه\u200cها', expenses), ('مانده نقدی', income - expenses), ('بودجه باقی\u200cمانده', budget - expenses)], categories)

def blank_row():
    return {'id': uuid4().hex, 'date': solar_date(), 'type': 'Expense', 'category': 'سایر', 'amount': '0', 'description': '', 'payer': '', 'counterparty': '', 'attachments': []}

def make_draft(project):
    rows = copy.deepcopy(project['transactions'])
    for row in rows:
        row.setdefault('id', uuid4().hex)
        row.setdefault('attachments', [])
        row.setdefault('payer', '')
        row.setdefault('counterparty', '')
        if row.get('category') != category_for(row):
            row.setdefault('original_category', row.get('category', ''))
        row['category'] = category_for(row)
        try:
            row['date'] = solar_date(row['date'])
        except ValueError:
            pass
    return {'budget': rial(project['budget']), 'notes': project['notes'], 'rows': rows or [blank_row()]}

def validate_rows(rows):
    result = []
    for index, row in enumerate(rows, 1):
        amount = rial(row['amount'])
        if not amount and (not any((str(row.get(field, '')).strip() for field in ['description', 'payer', 'counterparty']))) and (not row.get('attachments')):
            continue
        if amount <= 0:
            raise ValueError(f'Row {index}: the amount must be greater than zero.')
        if row['category'] not in CATEGORIES or row['type'] not in TYPE_LABELS:
            raise ValueError(f'Row {index}: choose a transaction type and category.')
        if (row['type'] == 'Income') != (row['category'] == 'دریافتی'):
            raise ValueError(f'Row {index}: choose دریافتی for both type and category for income; other categories are expenses.')
        result.append({**row, 'date': solar_date(row['date']), 'amount': str(amount), 'description': row['description'].strip(), 'payer': row.get('payer', '').strip(), 'counterparty': row.get('counterparty', '').strip()})
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
            sample = image.convert('RGBA')
            sample.thumbnail((768, 768), resample=Image.Resampling.NEAREST)
            pixels = [rgb[:3] for rgb in sample.getdata() if rgb[3] > 128 and min(rgb[:3]) < 235]
        from collections import Counter
        colored = [rgb for rgb in pixels if max(rgb) - min(rgb) > 40 and min(rgb) < 180]
        if colored or pixels:
            primary = Counter(colored or pixels).most_common(1)[0][0]

    def hex_color(rgb):
        return '#' + ''.join((f'{round(channel):02x}' for channel in rgb))
    header = primary

    def luminance(rgb):
        values = [channel / 255 for channel in rgb]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
        return sum((value * weight for value, weight in zip(linear, [0.2126, 0.7152, 0.0722])))
    while 1.05 / (luminance(header) + 0.05) < 4.5:
        header = tuple((channel * 0.9 for channel in header))
    return {'logo': logo, 'primary': hex_color(primary), 'header': hex_color(header), 'tint': hex_color(tuple((255 * 0.94 + channel * 0.06 for channel in primary))), 'line': hex_color(tuple((255 * 0.78 + channel * 0.22 for channel in primary)))}

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
    pdf_runs('')
    sans_fonts = {'regular': 'RNGFinancialSans', 'bold': 'RNGFinancialSansBold'}
    for name, filename in [(sans_fonts['regular'], 'Vera.ttf'), (sans_fonts['bold'], 'VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(Path(reportlab.__file__).parent / 'fonts' / filename)))
    brand = report_brand(logo_path)
    page_size = landscape(A4)
    width = page_size[0] - 72
    styles = {'title': ParagraphStyle('financial_title', fontName='RNGBNazanin', fontSize=21, leading=27, alignment=TA_CENTER, textColor=colors.HexColor('#242124')), 'group': ParagraphStyle('financial_group', fontName='RNGBNazanin', fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor(brand['header'])), 'body': ParagraphStyle('financial_body', fontName='RNGBNazanin', fontSize=12, leading=16, alignment=TA_RIGHT, textColor=colors.HexColor('#242124')), 'head': ParagraphStyle('financial_head', fontName='RNGBNazanin', fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#242124')), 'center': ParagraphStyle('financial_center', fontName='RNGBNazanin', fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#242124'))}

    def paragraph(text, available, kind='body'):
        lines = []
        font_size = styles[kind].fontSize
        has_persian = any(('\u0600' <= ch <= 'ࣿ' or 'ﭐ' <= ch <= '\ufeff' for ch in str(text)))

        def runs(visual):
            if not has_persian:
                return [(sans_fonts['bold'] if kind == 'title' else sans_fonts['regular'], visual)]
            return [(sans_fonts['regular'] if name == 'Helvetica' else name, part) for name, part in pdf_runs(visual)]
        for logical_line in str(text).splitlines() or ['']:
            current = ''
            for word in logical_line.split():
                fragments = [word]
                if sum((pdfmetrics.stringWidth(t, f, font_size) for f, t in runs(get_display(arabic_reshaper.reshape(word))))) > available - 12:
                    fragments = list(word)
                for fragment in fragments:
                    candidate = current + (' ' if current and len(fragments) == 1 else '') + fragment
                    visual = get_display(arabic_reshaper.reshape(candidate))
                    if current and sum((pdfmetrics.stringWidth(t, f, font_size) for f, t in runs(visual))) > available - 12:
                        lines.append(current)
                        current = fragment
                    else:
                        current = candidate
            lines.append(current)
        markup = []
        for line in lines:
            visual = get_display(arabic_reshaper.reshape(line))
            markup.append(''.join((f'<font name="{font}">{escape(part)}</font>' for font, part in runs(visual))))
        style = styles[kind]
        if not has_persian:
            style = ParagraphStyle(f'english_{kind}', parent=style, fontName=sans_fonts['regular'], alignment=0 if kind == 'body' else style.alignment)
        return Paragraph('<br/>'.join(markup) or ' ', style)
    from reportlab.platypus import KeepTogether
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=page_size, leftMargin=28, rightMargin=28, topMargin=108, bottomMargin=34, title=f"صورت مالی پروژه - {project['title']}", author='راه نیا گستر')
    width = page_size[0] - 56
    story = []
    summary, category_totals = totals(project)
    summary_values = dict(summary)
    sections = [('اجرت پیمانکار', 'اجرت'), ('اجرت خدماتی', 'خدمات'), ('خرید متریال', 'متریال'), ('سایر هزینه\u200cها', 'سایر'), ('دریافتی\u200cها', 'دریافتی')]
    widths = [width * ratio for ratio in [0.055, 0.15, 0.12, 0.12, 0.225, 0.08, 0.07, 0.12, 0.06]]
    headers = ['پیوست', 'مبلغ (ریال)', 'طرف حساب', 'پرداخت کننده', 'شرح', 'دسته بندی', 'نوع', 'تاریخ', 'ردیف']
    for title, category in sections:
        indexed_rows = []
        for index, row in enumerate(project['transactions'], 1):
            row_category = 'دریافتی' if row['type'] == 'Income' else category_for(row)
            if row['type'] == 'Expense' and row_category not in EXPENSE_CATEGORIES:
                row_category = 'سایر'
            if row_category == category:
                indexed_rows.append((index, row))
        if not indexed_rows:
            continue
        data = [[paragraph(title, width, 'group')] + [''] * (len(widths) - 1), [paragraph(label, cell_width, 'head') for label, cell_width in zip(headers, widths)]]
        for index, row in indexed_rows:
            try:
                date = solar_date(row['date'])
            except ValueError:
                date = row['date']
            attachment_count = len(row.get('attachments', []))
            values = [fa(attachment_count) if attachment_count else '—', fa(f"{rial(row['amount']):,}"), row.get('counterparty', ''), row.get('payer', ''), row['description'], category_for(row), TYPE_LABELS[row['type']], fa(date), fa(index)]
            data.append([paragraph(value, cell_width, 'body' if column == 4 else 'center') for column, (value, cell_width) in enumerate(zip(values, widths))])
        subtotal = sum((rial(row['amount']) for _, row in indexed_rows))
        data.append(['', paragraph(fa(f'{subtotal:,}'), widths[1], 'center'), paragraph('جمع کل (ریال)', sum(widths[2:]), 'body')] + [''] * (len(widths) - 3))
        ledger = Table(data, colWidths=widths, repeatRows=2, hAlign='RIGHT', splitInRow=1)
        ledger.setStyle(TableStyle([('SPAN', (0, 0), (-1, 0)), ('SPAN', (2, -1), (-1, -1)), ('NOSPLIT', (0, -2), (-1, -1)), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(brand['tint'])), ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f1f1f1')), ('ROWBACKGROUNDS', (0, 2), (-1, -2), [colors.white, colors.HexColor('#fafafa')]), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(brand['tint'])), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#706b6b')), ('BOX', (0, 0), (-1, -1), 0.9, colors.HexColor('#302b2b')), ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor(brand['primary'])), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5)]))
        story.append(KeepTogether([ledger, Spacer(1, 8)]))
    if not project['transactions']:
        story += [paragraph('هنوز تراکنشی ثبت نشده است.', width, 'center'), Spacer(1, 15)]
    final_pairs = [('بودجه پروژه', rial(project['budget'])), ('اجرت پیمانکار', category_totals['اجرت']), ('اجرت خدماتی', category_totals['خدمات']), ('خرید متریال', category_totals['متریال']), ('سایر هزینه\u200cها', category_totals['سایر']), ('جمع هزینه\u200cها', summary_values['هزینه\u200cها']), ('کل دریافتی', summary_values['دریافتی']), ('مانده نقدی', summary_values['مانده نقدی']), ('بودجه باقی\u200cمانده', summary_values['بودجه باقی\u200cمانده'])]
    summary_width = width * 0.58
    summary_rows = [[paragraph(f"{fa(f'{amount:,}')} ریال", summary_width * 0.46, 'center'), paragraph(label, summary_width * 0.54, 'body')] for label, amount in final_pairs]
    final_table = Table(summary_rows, colWidths=[summary_width * 0.46, summary_width * 0.54], hAlign='LEFT')
    final_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('LINEBELOW', (0, 0), (-1, -1), 0.35, colors.HexColor(brand['line'])), ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor(brand['tint'])), ('LINEABOVE', (0, -2), (-1, -2), 1.2, colors.HexColor(brand['primary']))]))
    story.append(KeepTogether([paragraph('خلاصه مالی پروژه', width, 'group'), Spacer(1, 8), final_table]))
    if project.get('notes'):
        story += [Spacer(1, 15), paragraph('یادداشت\u200cهای مالی', width), paragraph(project['notes'], width)]

    def decorate(canvas, document):
        from reportlab.lib.utils import ImageReader
        x, bottom, box_width, height = (28, page_size[1] - 90, width, 70)
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(colors.HexColor('#302b2b'))
        canvas.setLineWidth(0.9)
        canvas.rect(x, bottom, box_width, height, fill=1, stroke=1)
        canvas.setStrokeColor(colors.HexColor(brand['primary']))
        canvas.setLineWidth(2)
        canvas.line(x, bottom, x + box_width, bottom)
        if brand['logo'] is not None:
            canvas.drawImage(ImageReader(str(brand['logo'])), page_size[0] - 218, bottom + 8, width=178, height=54, preserveAspectRatio=True, anchor='c', mask='auto')
        title_x, title_width = (215, page_size[0] - 448)
        title = paragraph(f"صورت مالی پروژه\n{project['title']}", title_width, 'title')
        _, title_height = title.wrap(title_width, 58)
        while title_height > 58 and styles['title'].fontSize > 12:
            styles['title'].fontSize -= 1
            styles['title'].leading -= 1
            title = paragraph(f"صورت مالی پروژه\n{project['title']}", title_width, 'title')
            _, title_height = title.wrap(title_width, 58)
        title.drawOn(canvas, title_x, bottom + (height - title_height) / 2)
        metadata = paragraph(f'تاریخ: {fa(solar_date())}\nصفحه: {fa(document.page)}\nواحد مبالغ: ریال', 172, 'body')
        _, meta_height = metadata.wrap(172, 58)
        metadata.drawOn(canvas, 38, bottom + (height - meta_height) / 2)
        footer = paragraph(f'گزارش مالی پروژه  •  صفحه {fa(document.page)}', width, 'center')
        footer.wrap(width, 24)
        footer.drawOn(canvas, 28, 12)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()
