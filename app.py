# app_qr_pro.py
import streamlit as st
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# Intentamos módulo redondeado (si tu versión de qrcode lo soporta)
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    ROUNDED_OK = True
except Exception:
    ROUNDED_OK = False

def make_qr_matrix(text, version=None, error=qrcode.constants.ERROR_CORRECT_H, box_size=12, border=6):
    qr = qrcode.QRCode(version=version, error_correction=error, box_size=box_size, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    return qr

def render_qr_rounded(qr, fill="#000000", back="#FFFFFF"):
    # Requiere qrcode>=7.x
    return qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),  # módulos redondeados
        fill_color=fill, back_color=back
    ).get_image().convert("RGBA")

def render_qr_square(qr, fill="#000000", back="#FFFFFF"):
    return qr.make_image(fill_color=fill, back_color=back, image_factory=PilImage).get_image().convert("RGBA")

def place_center_badge(qr_img: Image.Image, logo_img: Image.Image,
                       disk_scale=0.30,    # 30% del lado del QR
                       logo_in_disk=0.72,  # 72% del diámetro del disco
                       disk_shape="circle",
                       disk_color=(255,255,255,255),
                       ring_px=0, ring_color=(230,230,230,255),  # opcional: anillo gris fino
                       drop_shadow=False):
    """
    Crea un "badge" central: disco blanco + (opcional) anillo + logo centrado.
    Todo en proporción al lado del QR para consistencia visual.
    """
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    side = min(W, H)
    D = int(side * disk_scale)  # diámetro del disco

    # Lienzo del badge
    badge = Image.new("RGBA", (D, D), (0,0,0,0))
    draw = ImageDraw.Draw(badge)

    if disk_shape == "circle":
        draw.ellipse((0, 0, D-1, D-1), fill=disk_color)
        if ring_px > 0:
            draw.ellipse((ring_px, ring_px, D-1-ring_px, D-1-ring_px), outline=ring_color, width=ring_px)
    else:
        r = int(D * 0.22)
        draw.rounded_rectangle((0, 0, D-1, D-1), radius=r, fill=disk_color)
        if ring_px > 0:
            draw.rounded_rectangle((ring_px, ring_px, D-1-ring_px, D-1-ring_px), radius=r, outline=ring_color, width=ring_px)

    # Logo dentro
    logo = logo_img.convert("RGBA")
    logo_side = int(D * logo_in_disk)
    logo = ImageOps.contain(logo, (logo_side, logo_side))
    lx = (D - logo.width) // 2
    ly = (D - logo.height) // 2
    badge.alpha_composite(logo, (lx, ly))

    # Sombra sutil opcional (para sensación “integrada”)
    if drop_shadow:
        shadow = Image.new("RGBA", (D, D), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        if disk_shape == "circle":
            sd.ellipse((0, 0, D-1, D-1), fill=(0,0,0,90))
        else:
            r = int(D * 0.22)
            sd.rounded_rectangle((0, 0, D-1, D-1), radius=r, fill=(0,0,0,90))
        # pequeño desplazamiento
        qr.alpha_composite(shadow, ((W - D)//2 + 2, (H - D)//2 + 2))

    # Componer al centro
    x = (W - D) // 2
    y = (H - D) // 2
    qr.alpha_composite(badge, (x, y))
    return qr

def pil_to_png_bytes(img: Image.Image) -> BytesIO:
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return buf

def png_to_pdf_bytes(png_buf: BytesIO, page_size=letter, qr_size_pts=300, x=120, y=460, caption=None):
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    c.drawImage(ImageReader(png_buf), x, y, width=qr_size_pts, height=qr_size_pts, mask='auto')
    if caption:
        c.setFont("Helvetica", 10); c.drawString(x, y-18, caption)
    c.save(); pdf.seek(0); return pdf

# ----------------- UI -----------------
st.set_page_config(page_title="QR Pro (logo integrado)", page_icon="🧩", layout="centered")
st.title("QR con logo integrado (estilo profesional)")

with st.form("qr"):
    text = st.text_input("Texto / URL", "https://fruttofoods.com")
    col1, col2 = st.columns(2)
    with col1:
        fill = st.color_picker("Color QR", "#000000")
        back = st.color_picker("Fondo", "#FFFFFF")
        version = st.selectbox("Versión (auto)", ["Auto"] + list(range(1, 40)), index=0)
        version = None if version == "Auto" else int(version)
        border = st.slider("Quiet zone (borde en módulos)", 4, 10, 6)
    with col2:
        box_size = st.slider("Box size (módulo)", 10, 18, 12)
        disk_scale = st.slider("Diámetro del disco (%)", 24, 36, 30) / 100.0
        logo_in_disk = st.slider("Logo dentro del disco (%)", 60, 85, 72) / 100.0
        ring_px = st.slider("Anillo fino (px)", 0, 6, 2)

    logo_file = st.file_uploader("Logo (PNG con transparencia ideal)", type=["png","jpg","jpeg"])
    shape = st.radio("Forma del disco", ["circle", "rounded"], index=0, horizontal=True)
    rounded_modules = st.toggle("Módulos redondeados", value=True if ROUNDED_OK else False,
                                help="Requiere qrcode.styledpil. Si no está, se usa fallback cuadrado.")
    shadow = st.toggle("Sombra sutil del badge", value=False)

    go = st.form_submit_button("Generar", use_container_width=True)

if go:
    if not text.strip():
        st.error("Escribe un texto/URL válido.")
        st.stop()
    qr = make_qr_matrix(text, version=version, border=border, box_size=box_size)
    base = render_qr_rounded(qr, fill, back) if (rounded_modules and ROUNDED_OK) else render_qr_square(qr, fill, back)

    if logo_file is None:
        st.warning("Sube el logo para ver el acabado ‘badge’. Muestro el QR base.")
        final_img = base
    else:
        logo = Image.open(logo_file)
        final_img = place_center_badge(base, logo,
                                       disk_scale=disk_scale,
                                       logo_in_disk=logo_in_disk,
                                       disk_shape=shape,
                                       ring_px=ring_px,
                                       drop_shadow=shadow)

    st.image(final_img, caption="QR generado", use_column_width=True)
    png = pil_to_png_bytes(final_img)
    st.download_button("Descargar PNG", data=png, file_name="qr_pro.png", mime="image/png", use_container_width=True)
    pdf = png_to_pdf_bytes(png, caption=f"Enlace: {text}")
    st.download_button("Descargar PDF", data=pdf, file_name="qr_pro.pdf", mime="application/pdf", use_container_width=True)

st.markdown("""
**Checklist de calidad**
- URL corta o con redirección → menos saturación visual.
- `border ≥ 6` y `box_size ≥ 12` → impresión limpia.
- Disco ≈ **30%** del lado y logo ≈ **72%** del disco → look pro y decodificación estable.
- Módulos **redondeados** suavizan la sensación de “ruido”.
- Exporta PNG grande (o **SVG** si no incrustas logo) y reescala fuera de la app.
""")
