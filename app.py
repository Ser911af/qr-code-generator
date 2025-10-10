# app_qr_logo.py
import streamlit as st
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# -------------------------
# Utilidades
# -------------------------
def generar_qr(
    link: str,
    fill_color: str = "#000000",
    back_color: str = "#FFFFFF",
    version: int | None = None,
    box_size: int = 10,
    border: int = 4,
    error_correction=qrcode.constants.ERROR_CORRECT_H,  # H para tolerar logo al centro
) -> Image.Image:
    qr = qrcode.QRCode(
        version=version,  # None/auto si version es None
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img: PilImage = qr.make_image(fill_color=fill_color, back_color=back_color, image_factory=PilImage)
    pil_img: Image.Image = img.get_image()  # Asegura objeto PIL puro
    return pil_img.convert("RGBA")

def preparar_logo(
    logo_img: Image.Image,
    target_side: int,
    circular: bool,
    add_outline: bool,
    outline_pad_px: int,
    outline_color: str = "white",
) -> Image.Image:
    """
    - target_side: lado mayor del logo final (px) antes de halo/outline
    - circular: si True, recorta en círculo
    - add_outline: si True, añade halo/blanco de seguridad
    """
    # Convertimos a RGBA y redimensionamos
    logo = logo_img.convert("RGBA")
    logo = ImageOps.contain(logo, (target_side, target_side))  # preserva proporción

    # Máscara para forma circular (o rectangular con canal alfa)
    if circular:
        mask = Image.new("L", logo.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, logo.size[0], logo.size[1]), fill=255)
    else:
        # borde suave para esquinas si no circular
        mask = Image.new("L", logo.size, 255)

    # Aplicamos máscara a logo para bordes limpios
    logo = Image.composite(logo, Image.new("RGBA", logo.size, (0, 0, 0, 0)), mask)

    if add_outline:
        # Creamos un lienzo más grande con halo blanco (mejora legibilidad del QR)
        W, H = logo.size
        bg = Image.new("RGBA", (W + 2 * outline_pad_px, H + 2 * outline_pad_px), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg)
        if circular:
            bg_draw.ellipse(
                (0, 0, bg.size[0] - 1, bg.size[1] - 1),
                fill=outline_color,
            )
        else:
            # rectángulo con esquinas redondeadas
            radius = int(min(bg.size) * 0.18)
            bg_draw.rounded_rectangle(
                (0, 0, bg.size[0] - 1, bg.size[1] - 1),
                radius=radius,
                fill=outline_color,
            )
        bg.paste(logo, (outline_pad_px, outline_pad_px), logo)
        return bg

    return logo

def incrustar_logo(qr_img: Image.Image, logo_img: Image.Image, logo_scale: float = 0.22,
                   circular: bool = True, add_outline: bool = True, outline_pad_px: int = 8) -> Image.Image:
    """
    - logo_scale: proporción del lado del QR que ocupará el logo (0.15–0.30 recomendado con EC=H)
    """
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    target_side = int(min(W, H) * logo_scale)

    logo_ready = preparar_logo(
        logo_img=logo_img,
        target_side=target_side,
        circular=circular,
        add_outline=add_outline,
        outline_pad_px=outline_pad_px,
        outline_color="white",
    )

    lw, lh = logo_ready.size
    pos = ((W - lw) // 2, (H - lh) // 2)
    qr.alpha_composite(logo_ready, dest=pos)
    return qr

def pil_to_png_bytes(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def png_to_pdf_bytes(png_buf: BytesIO, page_size=letter, qr_size_pts=200, x=100, y=500, caption: str | None = None) -> BytesIO:
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    img_reader = ImageReader(png_buf)
    c.drawImage(img_reader, x, y, width=qr_size_pts, height=qr_size_pts, mask='auto')
    if caption:
        c.setFont("Helvetica", 10)
        c.drawString(x, y - 18, caption)
    c.save()
    pdf.seek(0)
    return pdf

# -------------------------
# UI Streamlit
# -------------------------
st.set_page_config(page_title="Generador de QR con Logo", page_icon="🍏", layout="centered")
st.title("Generador de Códigos QR con Logo")

with st.form("qr_form"):
    link = st.text_input("Enlace o texto a codificar", placeholder="https://fruttofoods.com/...")
    col1, col2 = st.columns(2)
    with col1:
        fill_color = st.color_picker("Color del QR", "#000000")
        box_size = st.slider("Tamaño de módulo (box_size)", 6, 16, 10)
        border = st.slider("Borde (módulos)", 2, 8, 4)
    with col2:
        back_color = st.color_picker("Color de fondo", "#FFFFFF")
        version = st.selectbox("Versión del QR (auto recomendado)", options=["Auto"] + list(range(1, 40)), index=0)
        version = None if version == "Auto" else int(version)

    st.markdown("### Logo (opcional)")
    logo_file = st.file_uploader("Sube tu logo (PNG/JPG con fondo transparente recomendado)", type=["png", "jpg", "jpeg"])
    col3, col4, col5 = st.columns([1,1,1])
    with col3:
        logo_scale = st.slider("Escala del logo", 10, 35, 22, help="Porcentaje del lado del QR (recomendado 15–30).") / 100.0
    with col4:
        circular = st.toggle("Logo circular", value=True)
    with col5:
        add_outline = st.toggle("Halo blanco", value=True)
    outline_pad = st.slider("Grosor halo (px)", 0, 24, 8, help="Anillo/blanco de seguridad alrededor del logo.")

    generar = st.form_submit_button("Generar QR", use_container_width=True)

if generar:
    if not link.strip():
        st.error("Por favor, introduce un enlace o texto válido.")
        st.stop()

    # 1) Generar QR base con alta tolerancia de error
    qr_img = generar_qr(
        link,
        fill_color=fill_color,
        back_color=back_color,
        version=version,
        box_size=box_size,
        border=border,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )

    # 2) Incrustar logo si hay archivo
    final_img = qr_img
    if logo_file is not None:
        try:
            logo = Image.open(logo_file)
            final_img = incrustar_logo(
                qr_img=qr_img,
                logo_img=logo,
                logo_scale=logo_scale,
                circular=circular,
                add_outline=add_outline,
                outline_pad_px=outline_pad,
            )
        except Exception as e:
            st.warning(f"No se pudo procesar el logo ({e}). Se mostrará el QR sin logo.")

    # 3) Mostrar preview
    st.image(final_img, caption="Código QR generado", use_column_width=True)

    # 4) Descargas (PNG y PDF) – sin archivos temporales
    png_buf = pil_to_png_bytes(final_img)
    st.download_button(
        "Descargar PNG",
        data=png_buf,
        file_name="codigo_qr.png",
        mime="image/png",
        use_container_width=True,
    )

    pdf_buf = png_to_pdf_bytes(
        png_buf,
        page_size=letter,
        qr_size_pts=260,  # tamaño del QR en el PDF (points)
        x=100, y=480,
        caption=f"Enlace: {link}",
    )
    st.download_button(
        "Descargar PDF",
        data=pdf_buf,
        file_name="codigo_qr.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

# -------------------------
# Tips técnicos (render rápido y legibilidad)
# -------------------------
st.markdown(
"""
**Sugerencias de uso**
- Mantén **ERROR_CORRECT_H** (ya configurado) cuando incrustes logos ≥15% del lado.
- El **halo blanco** ayuda a que el lector de QR no se confunda con los píxeles del logo.
- Usa colores con **alto contraste** (QR oscuro sobre fondo claro). Si usas fondo oscuro, que el QR sea claro.
- Para impresión nítida, aumenta `box_size` (ej. 14–16) y luego reescala la imagen fuera de la app si lo necesitas.
"""
)
