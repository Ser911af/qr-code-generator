# app_qr_pro_plus.py
# — QR pro con limpieza de enlaces (WhatsApp), badge central y módulos redondeados —
import re
import unicodedata
import urllib.parse
from io import BytesIO

import streamlit as st
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageOps, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# Intentamos módulos redondeados (si tu versión de qrcode lo soporta)
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    ROUNDED_OK = True
except Exception:
    ROUNDED_OK = False


# =========================
# Utilidades de URL / WA
# =========================
def strip_emojis_and_smartquotes(text: str) -> str:
    """Quita emojis y caracteres no ASCII; normaliza comillas a ASCII."""
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    # Elimina cualquier no-ASCII (emojis, etc.)
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    return text.strip()


def compact_whatsapp_link(url: str) -> str:
    """
    Limpia un enlace de WhatsApp si aplica:
        https://wa.me/<number>?text=<...>
        https://api.whatsapp.com/send?phone=<number>&text=<...>
    - Quita emojis / comillas curvas
    - Codifica solo ASCII con quote_plus
    Devuelve el link limpio; si no es WhatsApp, lo deja igual.
    """
    if not (("wa.me" in url) or ("whatsapp.com" in url)):
        return url

    try:
        parsed = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(parsed.query)

        # Extraer número y texto según formato
        number = ""
        msg = ""

        # wa.me/<number>?text=...
        if "wa.me" in parsed.netloc:
            base_path = parsed.path.strip("/")  # <number>
            number = base_path
            msg = q.get("text", [""])[0]
        else:
            # api.whatsapp.com/send?phone=<number>&text=...
            number = q.get("phone", [""])[0]
            msg = q.get("text", [""])[0]

        # Decodificar, limpiar, re-codificar a ASCII
        msg = urllib.parse.unquote(msg or "")
        msg_clean = strip_emojis_and_smartquotes(msg)
        encoded = urllib.parse.quote_plus(msg_clean)

        # Reconstruir al formato compacto wa.me
        short = f"https://wa.me/{number}?text={encoded}" if number else url
        return short or url
    except Exception:
        return url


def qr_version_of(s: str, ec=qrcode.constants.ERROR_CORRECT_Q):
    """Retorna versión 1..40 estimada para comparar densidad."""
    qr = qrcode.QRCode(error_correction=ec, box_size=10, border=4)
    qr.add_data(s)
    qr.make(fit=True)
    return qr.version


# =========================
# Render del QR / Badge
# =========================
def make_qr_matrix(text, version=None, error=qrcode.constants.ERROR_CORRECT_Q, box_size=12, border=6):
    qr = qrcode.QRCode(version=version, error_correction=error, box_size=box_size, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def render_qr_rounded(qr, fill="#000000", back="#FFFFFF"):
    # Requiere qrcode>=7.x (StyledPilImage). Si no está, usa render_qr_square.
    return qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color=fill, back_color=back
    ).get_image().convert("RGBA")


def render_qr_square(qr, fill="#000000", back="#FFFFFF"):
    return qr.make_image(fill_color=fill, back_color=back, image_factory=PilImage).get_image().convert("RGBA")


def place_center_badge(qr_img: Image.Image, logo_img: Image.Image,
                       disk_scale=0.30,    # 30% del lado del QR
                       logo_in_disk=0.72,  # 72% del diámetro del disco
                       disk_shape="circle",
                       disk_color=(255, 255, 255, 255),
                       ring_px=2,
                       ring_color=(230, 230, 230, 255),
                       drop_shadow=False):
    """Disco + anillo opcional + logo centrado, todo proporcional al lado del QR."""
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    side = min(W, H)
    D = int(side * disk_scale)  # diámetro del disco

    badge = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)

    if disk_shape == "circle":
        draw.ellipse((0, 0, D - 1, D - 1), fill=disk_color)
        if ring_px > 0:
            draw.ellipse((ring_px, ring_px, D - 1 - ring_px, D - 1 - ring_px), outline=ring_color, width=ring_px)
    else:
        r = int(D * 0.22)
        draw.rounded_rectangle((0, 0, D - 1, D - 1), radius=r, fill=disk_color)
        if ring_px > 0:
            draw.rounded_rectangle((ring_px, ring_px, D - 1 - ring_px, D - 1 - ring_px),
                                   radius=r, outline=ring_color, width=ring_px)

    logo = logo_img.convert("RGBA")
    logo_side = int(D * logo_in_disk)
    logo = ImageOps.contain(logo, (logo_side, logo_side))
    lx = (D - logo.width) // 2
    ly = (D - logo.height) // 2
    badge.alpha_composite(logo, (lx, ly))

    if drop_shadow:
        shadow = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        if disk_shape == "circle":
            sd.ellipse((0, 0, D - 1, D - 1), fill=(0, 0, 0, 90))
        else:
            r = int(D * 0.22)
            sd.rounded_rectangle((0, 0, D - 1, D - 1), radius=r, fill=(0, 0, 0, 90))
        qr.alpha_composite(shadow, ((W - D) // 2 + 2, (H - D) // 2 + 2))

    x = (W - D) // 2
    y = (H - D) // 2
    qr.alpha_composite(badge, (x, y))
    return qr


def pil_to_png_bytes(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def png_to_pdf_bytes(png_buf: BytesIO, page_size=letter, qr_size_pts=300, x=120, y=460, caption=None):
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    c.drawImage(ImageReader(png_buf), x, y, width=qr_size_pts, height=qr_size_pts, mask='auto')
    if caption:
        c.setFont("Helvetica", 10)
        c.drawString(x, y - 18, caption)
    c.save()
    pdf.seek(0)
    return pdf


# =========================
# UI
# =========================
st.set_page_config(page_title="QR Pro (WhatsApp Clean + Badge)", page_icon="🧩", layout="centered")
st.title("QR Pro con limpieza de enlaces y logo integrado")

with st.form("qr"):
    text = st.text_input("Texto / URL", "https://fruttofoods.com")
    col1, col2 = st.columns(2)

    with col1:
        fill = st.color_picker("Color QR", "#000000")
        back = st.color_picker("Fondo", "#FFFFFF")
        version_opt = st.selectbox("Versión (Auto recomendado)", ["Auto"] + list(range(1, 40)), index=0)
        version = None if version_opt == "Auto" else int(version_opt)
        border = st.slider("Quiet zone (borde en módulos)", 4, 10, 6)

    with col2:
        box_size = st.slider("Box size (módulo)", 10, 18, 12)
        disk_scale = st.slider("Diámetro del disco (%)", 24, 36, 30) / 100.0
        logo_in_disk = st.slider("Logo dentro del disco (%)", 60, 85, 72) / 100.0
        ring_px = st.slider("Anillo fino (px)", 0, 6, 2)

    logo_file = st.file_uploader("Logo (PNG con transparencia ideal)", type=["png", "jpg", "jpeg"])
    shape = st.radio("Forma del disco", ["circle", "rounded"], index=0, horizontal=True)
    rounded_modules = st.toggle("Módulos redondeados", value=True if ROUNDED_OK else False,
                                help="Requiere qrcode.styledpil. Si no está, se usa fallback cuadrado.")
    shadow = st.toggle("Sombra sutil del badge", value=False)

    # Si NO hay logo, te dejo escoger el nivel de corrección. Con logo, lo fuerzo a H.
    if logo_file is None:
        ec_label = st.selectbox("Nivel de corrección de error (sin logo)",
                                ["Q (recomendado)", "H", "M", "L"], index=0)
        ec_map = {"L": qrcode.constants.ERROR_CORRECT_L,
                  "M": qrcode.constants.ERROR_CORRECT_M,
                  "Q": qrcode.constants.ERROR_CORRECT_Q,
                  "H": qrcode.constants.ERROR_CORRECT_H}
        error_corr = ec_map[ec_label.split()[0]]
    else:
        error_corr = qrcode.constants.ERROR_CORRECT_H  # con logo siempre H

    go = st.form_submit_button("Generar", use_container_width=True)

if go:
    if not text.strip():
        st.error("Escribe un texto/URL válido."); st.stop()

    # 1) LIMPIEZA y OPTIMIZACIÓN del enlace
    original_text = text.strip()
    cleaned_text = compact_whatsapp_link(original_text)

    # 2) Mostrar impacto de la limpieza en versión QR
    try:
        v_orig = qr_version_of(original_text, ec=error_corr)
        v_clean = qr_version_of(cleaned_text, ec=error_corr)
        if "wa.me" in original_text or "whatsapp.com" in original_text:
            st.info("🔗 Enlace WhatsApp detectado. Se aplicó limpieza automática "
                    "(sin emojis / comillas curvas).")
        st.caption(f"Versión QR original: **{v_orig}** → optimizada: **{v_clean}** (EC={['L','M','Q','H'][[qrcode.constants.ERROR_CORRECT_L,qrcode.constants.ERROR_CORRECT_M,qrcode.constants.ERROR_CORRECT_Q,qrcode.constants.ERROR_CORRECT_H].index(error_corr)]})")
    except Exception:
        pass

    # 3) Generar QR con el enlace optimizado
    qr = make_qr_matrix(cleaned_text, version=version, error=error_corr, box_size=box_size, border=border)
    base = render_qr_rounded(qr, fill, back) if (rounded_modules and ROUNDED_OK) else render_qr_square(qr, fill, back)

    # 4) Badge central si hay logo
    if logo_file is not None:
        logo = Image.open(logo_file)
        final_img = place_center_badge(base, logo,
                                       disk_scale=disk_scale,
                                       logo_in_disk=logo_in_disk,
                                       disk_shape=shape,
                                       ring_px=ring_px,
                                       drop_shadow=shadow)
    else:
        final_img = base

    # 5) Preview + Descargas
    st.image(final_img, caption="QR generado", use_column_width=True)
    png_buf = pil_to_png_bytes(final_img)
    st.download_button("Descargar PNG", data=png_buf, file_name="qr_pro.png",
                       mime="image/png", use_container_width=True)
    pdf_buf = png_to_pdf_bytes(png_buf, caption=f"Enlace: {cleaned_text}")
    st.download_button("Descargar PDF", data=pdf_buf, file_name="qr_pro.pdf",
                       mime="application/pdf", use_container_width=True)

    # Tips
    st.markdown("""
**Tips**
- Para WhatsApp ultra-limpio, usa una **redirección corta** en tu dominio (p. ej. `https://fruttofoods.com/wj`)
  que haga 301 al `wa.me?text=...`. Así el QR codifica solo la URL corta y queda como el de fruttofoods.com.
- Con logo: mantén `EC = H`, `disk_scale ≈ 0.30`, `logo_in_disk ≈ 0.72`.
- Impresión: `box_size ≥ 12` y `border ≥ 6` para buena legibilidad.
""")
