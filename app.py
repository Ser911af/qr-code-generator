import streamlit as st
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import requests
import json
import base64
import urllib.parse

try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    ROUNDED_OK = True
except Exception:
    ROUNDED_OK = False

# --- GitHub storage ---
GITHUB_API = "https://api.github.com"

def gh_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

def gh_get_links():
    repo = st.secrets.get("GITHUB_REPO", "")
    url = f"{GITHUB_API}/repos/{repo}/contents/links.json"
    r = requests.get(url, headers=gh_headers())
    if r.status_code == 404:
        return {}, None
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), data["sha"]

def gh_save_links(links: dict, sha=None):
    repo = st.secrets.get("GITHUB_REPO", "")
    url = f"{GITHUB_API}/repos/{repo}/contents/links.json"
    content = base64.b64encode(
        json.dumps(links, indent=2, ensure_ascii=False).encode()
    ).decode()
    payload = {"message": "update links.json", "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=payload)
    return r.status_code in (200, 201)

# --- QR helpers ---
def make_qr_matrix(text, version=None, error=qrcode.constants.ERROR_CORRECT_H, box_size=12, border=6):
    qr = qrcode.QRCode(version=version, error_correction=error, box_size=box_size, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    return qr

def render_qr_rounded(qr, fill="#000000", back="#FFFFFF"):
    return qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color=fill, back_color=back
    ).get_image().convert("RGBA")

def render_qr_square(qr, fill="#000000", back="#FFFFFF"):
    return qr.make_image(fill_color=fill, back_color=back, image_factory=PilImage).get_image().convert("RGBA")

def place_center_badge(qr_img, logo_img, disk_scale=0.30, logo_in_disk=0.72,
                       disk_shape="circle", disk_color=(255,255,255,255),
                       ring_px=0, ring_color=(230,230,230,255), drop_shadow=False):
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    side = min(W, H)
    D = int(side * disk_scale)
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
    logo = logo_img.convert("RGBA")
    logo_side = int(D * logo_in_disk)
    logo = ImageOps.contain(logo, (logo_side, logo_side))
    lx = (D - logo.width) // 2
    ly = (D - logo.height) // 2
    badge.alpha_composite(logo, (lx, ly))
    if drop_shadow:
        shadow = Image.new("RGBA", (D, D), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        if disk_shape == "circle":
            sd.ellipse((0, 0, D-1, D-1), fill=(0,0,0,90))
        else:
            r = int(D * 0.22)
            sd.rounded_rectangle((0, 0, D-1, D-1), radius=r, fill=(0,0,0,90))
        qr.alpha_composite(shadow, ((W - D)//2 + 2, (H - D)//2 + 2))
    x = (W - D) // 2
    y = (H - D) // 2
    qr.alpha_composite(badge, (x, y))
    return qr

def pil_to_png_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def png_to_pdf_bytes(png_buf, page_size=letter, qr_size_pts=300, x=120, y=460, caption=None):
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    c.drawImage(ImageReader(png_buf), x, y, width=qr_size_pts, height=qr_size_pts, mask='auto')
    if caption:
        c.setFont("Helvetica", 10)
        c.drawString(x, y - 18, caption)
    c.save()
    pdf.seek(0)
    return pdf

# ===================== APP =====================
st.set_page_config(page_title="QR Pro", page_icon="🧩", layout="centered")

# --- Redirect handler (antes de cualquier UI) ---
params = st.query_params
if "r" in params:
    slug = params["r"]
    links, _ = gh_get_links()
    dest = links.get(slug)
    if dest:
        st.markdown(f'<meta http-equiv="refresh" content="0; url={dest}">', unsafe_allow_html=True)
        st.info(f"Redirigiendo a {dest}...")
    else:
        st.error(f"El link '{slug}' no existe.")
    st.stop()

# --- Password gate ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("QR Pro")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar", use_container_width=True):
        if pwd == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# --- Main UI ---
st.title("QR Pro")
tab1, tab2, tab3 = st.tabs(["Generar QR", "Link de WhatsApp", "Links Dinámicos"])

# =================== TAB 1: QR Generator ===================
with tab1:
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
        rounded_modules = st.toggle("Módulos redondeados", value=True if ROUNDED_OK else False)
        shadow = st.toggle("Sombra sutil del badge", value=False)
        go = st.form_submit_button("Generar", use_container_width=True)

    if go:
        if not text.strip():
            st.error("Escribe un texto/URL válido.")
            st.stop()
        qr = make_qr_matrix(text, version=version, border=border, box_size=box_size)
        base = render_qr_rounded(qr, fill, back) if (rounded_modules and ROUNDED_OK) else render_qr_square(qr, fill, back)
        if logo_file is None:
            st.warning("Sin logo. Mostrando QR base.")
            final_img = base
        else:
            logo = Image.open(logo_file)
            final_img = place_center_badge(base, logo, disk_scale=disk_scale, logo_in_disk=logo_in_disk,
                                           disk_shape=shape, ring_px=ring_px, drop_shadow=shadow)
        st.image(final_img, caption="QR generado", use_container_width=True)
        png = pil_to_png_bytes(final_img)
        st.download_button("Descargar PNG", data=png, file_name="qr_pro.png", mime="image/png", use_container_width=True)
        pdf = png_to_pdf_bytes(pil_to_png_bytes(final_img), caption=f"Enlace: {text}")
        st.download_button("Descargar PDF", data=pdf, file_name="qr_pro.pdf", mime="application/pdf", use_container_width=True)

# =================== TAB 2: WhatsApp Link ===================
with tab2:
    st.subheader("Generador de link de WhatsApp")
    with st.form("wa"):
        phone = st.text_input("Número (con código de país, sin + ni espacios)", placeholder="5491112345678")
        message = st.text_area("Mensaje pre-cargado (opcional)", placeholder="Hola, me interesa...")
        go_wa = st.form_submit_button("Generar link y QR", use_container_width=True)

    if go_wa:
        if not phone.strip():
            st.error("Ingresa un número de teléfono.")
        else:
            wa_url = f"https://wa.me/{phone.strip()}"
            if message.strip():
                wa_url += f"?text={urllib.parse.quote(message.strip())}"
            st.success("Link generado:")
            st.code(wa_url)
            qr = make_qr_matrix(wa_url)
            img = render_qr_rounded(qr) if ROUNDED_OK else render_qr_square(qr)
            st.image(img, caption="QR del link de WhatsApp", use_container_width=True)
            png = pil_to_png_bytes(img)
            st.download_button("Descargar PNG", data=png, file_name="qr_whatsapp.png", mime="image/png", use_container_width=True)
            pdf = png_to_pdf_bytes(pil_to_png_bytes(img), caption=f"WhatsApp: {phone.strip()}")
            st.download_button("Descargar PDF", data=pdf, file_name="qr_whatsapp.pdf", mime="application/pdf", use_container_width=True)

# =================== TAB 3: Dynamic Links ===================
with tab3:
    st.subheader("Links Dinámicos")
    app_url = st.secrets.get("APP_URL", "https://tu-app.streamlit.app")

    links, sha = gh_get_links()

    if links:
        st.write("**Links activos:**")
        for slug, dest in list(links.items()):
            c1, c2, c3 = st.columns([2, 5, 1])
            with c1:
                st.code(f"?r={slug}", language=None)
            with c2:
                st.write(dest)
            with c3:
                if st.button("🗑", key=f"del_{slug}"):
                    del links[slug]
                    if gh_save_links(links, sha):
                        st.success("Eliminado.")
                        st.rerun()
                    else:
                        st.error("Error al guardar.")
    else:
        st.info("No hay links todavía. Crea uno abajo.")

    st.divider()
    st.write("**Nuevo link / Editar existente:**")
    with st.form("new_link"):
        new_slug = st.text_input("Slug", placeholder="frutto, menu, promo2026...")
        new_dest = st.text_input("URL destino", placeholder="https://fruttofoods.com/promo")
        save = st.form_submit_button("Guardar", use_container_width=True)

    if save:
        if not new_slug.strip() or not new_dest.strip():
            st.error("Completa ambos campos.")
        else:
            links[new_slug.strip()] = new_dest.strip()
            if gh_save_links(links, sha):
                full_url = f"{app_url}/?r={new_slug.strip()}"
                st.success(f"Guardado. URL del QR: `{full_url}`")
                st.rerun()
            else:
                st.error("Error al guardar en GitHub. Verifica el token.")

    if links:
        st.divider()
        st.write("**Generar QR de un link dinámico:**")
        selected = st.selectbox("Seleccionar slug", list(links.keys()))
        if st.button("Generar QR dinámico", use_container_width=True):
            qr_url = f"{app_url}/?r={selected}"
            qr = make_qr_matrix(qr_url)
            img = render_qr_rounded(qr) if ROUNDED_OK else render_qr_square(qr)
            st.image(img, caption=f"QR → {qr_url}", use_container_width=True)
            png = pil_to_png_bytes(img)
            st.download_button("Descargar PNG", data=png, file_name=f"qr_{selected}.png", mime="image/png", use_container_width=True)
            pdf = png_to_pdf_bytes(pil_to_png_bytes(img), caption=qr_url)
            st.download_button("Descargar PDF", data=pdf, file_name=f"qr_{selected}.pdf", mime="application/pdf", use_container_width=True)
