# app_qr_logo_badge.py
import streamlit as st
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# ----------------- Utilidades -----------------
def render_qr_base(text, fill="#000000", back="#FFFFFF", version=None, box_size=12, border=4):
    qr = qrcode.QRCode(
        version=version,  # None -> auto
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # tolera logo/disco central
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    pil = qr.make_image(fill_color=fill, back_color=back, image_factory=PilImage).get_image()
    return pil.convert("RGBA")

def place_center_badge(qr_img: Image.Image, logo_img: Image.Image,
                       disk_scale=0.30,       # 30% del lado del QR (disco blanco)
                       logo_in_disk=0.72,     # 72% del diámetro del disco (logo)
                       disk_shape="circle",   # circle | rounded
                       disk_color=(255,255,255,255)):
    """
    disk_scale = fracción del lado del QR ocupada por el disco blanco central.
    logo_in_disk = fracción del diámetro del disco ocupada por el logo.
    """
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    side = min(W, H)

    # 1) Disco blanco
    D = int(side * disk_scale)  # diámetro disco
    disk = Image.new("RGBA", (D, D), (0,0,0,0))
    draw = ImageDraw.Draw(disk)
    if disk_shape == "circle":
        draw.ellipse((0, 0, D-1, D-1), fill=disk_color)
    else:
        r = int(D * 0.22)
        draw.rounded_rectangle((0, 0, D-1, D-1), radius=r, fill=disk_color)

    # 2) Logo dentro del disco (conservar proporción y anti alias)
    logo = logo_img.convert("RGBA")
    logo_side = int(D * logo_in_disk)
    logo = ImageOps.contain(logo, (logo_side, logo_side))
    # centrar logo sobre el disco
    lx = (D - logo.width) // 2
    ly = (D - logo.height) // 2
    disk.alpha_composite(logo, (lx, ly))

    # 3) Componer al centro del QR
    x = (W - D) // 2
    y = (H - D) // 2
    qr.alpha_composite(disk, (x, y))
    return qr

def pil_to_png_bytes(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0); return buf

def png_to_pdf_bytes(png_buf: BytesIO, page_size=letter, qr_size_pts=280, x=100, y=470, caption=None):
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    c.drawImage(ImageReader(png_buf), x, y, width=qr_size_pts, height=qr_size_pts, mask='auto')
    if caption:
        c.setFont("Helvetica", 10)
        c.drawString(x, y-18, caption)
    c.save(); pdf.seek(0); return pdf

# ----------------- UI -----------------
st.set_page_config(page_title="QR tipo badge (logo centrado)", page_icon="🟢")

st.title("QR con logo centrado estilo ‘badge’")

with st.form("qr"):
    text = st.text_input("Texto/URL", "https://fruttofoods.com")
    colA, colB = st.columns(2)
    with colA:
        fill = st.color_picker("Color del QR", "#000000")
        back = st.color_picker("Fondo", "#FFFFFF")
        version = st.selectbox("Versión (auto recomendado)", ["Auto"] + list(range(1, 40)), index=0)
        version = None if version == "Auto" else int(version)
    with colB:
        box_size = st.slider("Box size (módulo)", 8, 16, 12)
        border = st.slider("Borde (módulos)", 3, 8, 4)
        disk_scale = st.slider("Tamaño del disco central (%)", 20, 38, 30) / 100.0
        logo_in_disk = st.slider("Logo dentro del disco (%)", 60, 85, 72) / 100.0

    logo_file = st.file_uploader("Sube tu logo (PNG con transparencia ideal)", type=["png","jpg","jpeg"])
    shape = st.radio("Forma del disco", ["circle", "rounded"], horizontal=True, index=0)

    go = st.form_submit_button("Generar", use_container_width=True)

if go:
    if not text.strip():
        st.error("Dame un texto o URL válido, por fa.")
        st.stop()

    qr_base = render_qr_base(text, fill=fill, back=back, version=version, box_size=box_size, border=border)

    if logo_file is None:
        st.warning("Sube el logo verde para ver el badge completo. Por ahora muestro solo el QR.")
        final_img = qr_base
    else:
        logo_img = Image.open(logo_file)
        final_img = place_center_badge(qr_base, logo_img, disk_scale=disk_scale, logo_in_disk=logo_in_disk, disk_shape=shape)

    st.image(final_img, caption="QR generado", use_column_width=True)

    png_buf = pil_to_png_bytes(final_img)
    st.download_button("Descargar PNG", data=png_buf, file_name="qr_badge.png", mime="image/png", use_container_width=True)

    pdf_buf = png_to_pdf_bytes(png_buf, caption=f"Enlace: {text}")
    st.download_button("Descargar PDF", data=pdf_buf, file_name="qr_badge.pdf", mime="application/pdf", use_container_width=True)

st.markdown("""
**Notas rápidas**
- EC=**H** ya está activado para tolerar el disco/logo central.
- Si el lector falla, reduce `disk_scale` o aumenta `border`/`box_size`.
- Para impresión: sube `box_size` (p. ej. 14–16) y exporta PNG grande.
""")
