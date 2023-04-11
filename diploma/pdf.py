from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


def text_lines(text, value_map):
    for key,value in value_map.items():
        text = text.replace(key, value)
    return [l.strip() for l in text.split("\n")] # noqa: E741


def render_diploma(request, response, diploma): # pylint: disable=too-many-locals
    design = diploma.design

    c = canvas.Canvas(response)

    marginLeft = 2 * cm
    marginTop = 2 * cm
    marginBottom = 2.5 * cm
    cTop = 29.7 * cm - marginTop
    cLeft = marginLeft
    cMiddle = 21 * cm / 2
    logoHeight = 1.4 * cm

    text_value_map = {
        '$grade': str(diploma.grade),
    }

    if design.logo:
        c.drawImage(
            design.logo.path,
            cLeft,
            cTop - logoHeight,
            height=logoHeight,
            preserveAspectRatio=True,
            anchor="nw"
        )

    c.setFont("Helvetica-Bold", 30)
    c.setFillColorRGB(0, 0.25, 0.5)
    c.drawCentredString(10.5 * cm, cTop - 5 * cm, diploma.name)

    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0, 0, 0)
    for i,line in enumerate(text_lines(design.title, text_value_map)):
        c.drawCentredString(cMiddle, cTop - 7 * cm - (i * 0.8 * cm), line)

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)
    for i,line in enumerate(text_lines(design.body, text_value_map)):
        c.drawString(cLeft, cTop - 10 * cm - (i * 0.6 * cm), line)

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(cLeft, cTop - 21 * cm, design.date)

    c.drawString(cLeft, cTop - 23.5 * cm, design.signature_name)
    c.drawString(cLeft, cTop - 24 * cm, design.signature_title)

    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0, 0, 0)
    for i,line in enumerate(text_lines(design.small_print, text_value_map)):
        c.drawString(cLeft, marginBottom - (i * 0.3 * cm), line)

    qr_code = qr.QrCodeWidget(request.build_absolute_uri(diploma.get_absolute_url()))
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    d = Drawing(1200, 1200, transform=[60./width,0,0,60./height,0,0])
    d.add(qr_code)
    renderPDF.draw(d, c, 16.7 * cm, cTop - 24.3 * cm)

    c.showPage()
    #c.setAuthor("A+")
    c.setTitle("Course Diploma")
    #c.setSubject("")
    c.save()
