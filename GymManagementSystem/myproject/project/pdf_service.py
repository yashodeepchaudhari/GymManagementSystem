"""PDF generation for AI plans and payment receipts."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name='Heading', parent=base['Title'], fontSize=20, textColor=colors.HexColor('#007bff'),
        spaceAfter=10,
    ))
    base.add(ParagraphStyle(
        name='SubHeading', parent=base['Heading2'], fontSize=14, textColor=colors.HexColor('#222'),
        spaceBefore=12, spaceAfter=6,
    ))
    base.add(ParagraphStyle(name='Small', parent=base['BodyText'], fontSize=9, textColor=colors.grey))
    return base


def render_plan_pdf(member, workout, diet) -> bytes:
    """Render a 7-day plan PDF (workout + diet) for the given member."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Plan for {member.name}",
    )
    styles = _styles()
    story = []

    story.append(Paragraph("GymPro · AI Fitness Plan", styles['Heading']))
    story.append(Paragraph(
        f"<b>{member.name}</b> · {member.age}y, {member.gender or '-'} · "
        f"BMI {member.bmi or '-'} · Goal: {member.get_goal_display() or '-'}",
        styles['BodyText'],
    ))
    story.append(Paragraph(
        f"Generated {workout.created_at:%d %b %Y, %H:%M}" if workout else "",
        styles['Small'],
    ))
    story.append(Spacer(1, 0.4 * cm))

    if workout and workout.content.get('summary'):
        story.append(Paragraph("Summary", styles['SubHeading']))
        story.append(Paragraph(workout.content.get('summary', ''), styles['BodyText']))

    if workout and workout.content.get('workout'):
        story.append(Paragraph("7-Day Workout Split", styles['SubHeading']))
        for day in workout.content.get('workout', []):
            story.append(Paragraph(
                f"<b>{day.get('day','?')}</b> – {day.get('focus','-')}",
                styles['BodyText'],
            ))
            exercises = day.get('exercises') or []
            if not exercises:
                story.append(Paragraph("<i>Rest day</i>", styles['BodyText']))
            else:
                rows = [['Exercise', 'Sets', 'Reps']]
                for ex in exercises:
                    rows.append([ex.get('name', ''), str(ex.get('sets', '')), str(ex.get('reps', ''))])
                t = Table(rows, colWidths=[10 * cm, 2.5 * cm, 2.5 * cm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef')),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ]))
                story.append(t)
            story.append(Spacer(1, 0.25 * cm))

    if workout and workout.content.get('tips'):
        story.append(Paragraph("Coach's Tips", styles['SubHeading']))
        for tip in workout.content.get('tips', []):
            story.append(Paragraph(f"• {tip}", styles['BodyText']))

    if diet and diet.content.get('diet'):
        story.append(PageBreak())
        story.append(Paragraph("7-Day Diet Plan", styles['Heading']))
        for d in diet.content.get('diet', []):
            cals = d.get('calories_approx')
            story.append(Paragraph(
                f"<b>{d.get('day','?')}</b>" + (f" · ~{cals} kcal" if cals else ''),
                styles['BodyText'],
            ))
            meals = d.get('meals', {}) or {}
            rows = [['Meal', 'Food']]
            for k in ('breakfast', 'lunch', 'snack', 'dinner'):
                if k in meals:
                    rows.append([k.title(), meals[k]])
            t = Table(rows, colWidths=[3 * cm, 12 * cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#efe')),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.25 * cm))

    doc.build(story)
    return buf.getvalue()


def render_receipt_pdf(payment) -> bytes:
    """Render a single payment receipt."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Receipt #{payment.id}",
    )
    styles = _styles()
    story = []

    story.append(Paragraph("GymPro · Payment Receipt", styles['Heading']))
    story.append(Paragraph(f"Receipt #{payment.id}", styles['Small']))
    story.append(Spacer(1, 0.5 * cm))

    rows = [
        ['Member', payment.member.name],
        ['Email', payment.member.email],
        ['Plan', payment.subscription.plan.name if payment.subscription_id else '—'],
        ['Amount', f'INR {payment.amount}'],
        ['Mode', payment.get_mode_display()],
        ['Status', payment.get_status_display()],
        ['Reference', payment.reference or '—'],
        ['Paid at', payment.paid_at.strftime('%d %b %Y, %H:%M')],
    ]
    t = Table(rows, colWidths=[4 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Thank you for your payment!", styles['BodyText']))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "This is a computer-generated receipt and does not require a signature.",
        styles['Small'],
    ))

    doc.build(story)
    return buf.getvalue()
