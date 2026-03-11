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

# ── GitHub storage ─────────────────────────────────────────
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

# ── QR helpers ──────────────────────────────────────────────
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
                       disk_shape="circle", disk_color=(255, 255, 255, 255),
                       ring_px=0, ring_color=(230, 230, 230, 255), drop_shadow=False):
    qr = qr_img.copy().convert("RGBA")
    W, H = qr.size
    side = min(W, H)
    D = int(side * disk_scale)
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
            draw.rounded_rectangle((ring_px, ring_px, D - 1 - ring_px, D - 1 - ring_px), radius=r, outline=ring_color, width=ring_px)
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

def pil_to_png_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def png_to_pdf_bytes(png_buf, page_size=letter, qr_size_pts=300, x=120, y=460, caption=None):
    pdf = BytesIO()
    c = canvas.Canvas(pdf, pagesize=page_size)
    c.drawImage(ImageReader(png_buf), x, y, width=qr_size_pts, height=qr_size_pts, mask="auto")
    if caption:
        c.setFont("Helvetica", 10)
        c.drawString(x, y - 18, caption)
    c.save()
    pdf.seek(0)
    return pdf

# ═══════════════════════════════════════════════════════════
#  APP CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="Frutto QR Studio", page_icon="🍃", layout="centered")

# ── Brand CSS ───────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  /* Global font */
  html, body, [class*="css"] {
    font-family: 'Noto Sans', sans-serif !important;
  }

  /* Hide Streamlit default menu/footer */
  #MainMenu, footer { visibility: hidden; }

  /* Main background */
  .stApp { background-color: #F8F9F5; }

  /* Header brand bar */
  .brand-header {
    background: #A8CF39;
    border-radius: 16px;
    padding: 28px 32px 20px 32px;
    margin-bottom: 28px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  .brand-header h1 {
    color: #1a1a1a;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
  }
  .brand-header p {
    color: #2d2d2d;
    font-size: 0.95rem;
    margin: 0;
    opacity: 0.75;
  }

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
    border-bottom: 2px solid #e0e0d8;
    padding-bottom: 0;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    color: #666;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 10px 20px;
    border: none;
  }
  .stTabs [aria-selected="true"] {
    background: #A8CF39 !important;
    color: #1a1a1a !important;
    font-weight: 600;
  }

  /* Info cards */
  .info-card {
    background: #ffffff;
    border-left: 4px solid #A8CF39;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .info-card h4 {
    color: #1a1a1a;
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 6px 0;
  }
  .info-card p, .info-card li {
    color: #555;
    font-size: 0.88rem;
    margin: 0;
    line-height: 1.6;
  }
  .info-card ul { margin: 6px 0 0 0; padding-left: 18px; }

  /* Step cards */
  .step-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }
  .step-num {
    background: #A8CF39;
    color: #1a1a1a;
    font-weight: 700;
    font-size: 0.9rem;
    border-radius: 50%;
    min-width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .step-text strong { color: #1a1a1a; font-size: 0.9rem; }
  .step-text p { color: #666; font-size: 0.83rem; margin: 2px 0 0 0; line-height: 1.5; }

  /* Warning card */
  .warn-card {
    background: #FFF8E1;
    border-left: 4px solid #FEF303;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 20px;
  }
  .warn-card p { color: #5a4f00; font-size: 0.87rem; margin: 0; }

  /* Orange accent card */
  .accent-card {
    background: #FFF2EC;
    border-left: 4px solid #FF4800;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 20px;
  }
  .accent-card p { color: #7a2200; font-size: 0.87rem; margin: 0; }

  /* Section label */
  .section-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 10px;
  }

  /* Divider */
  .frutto-divider {
    border: none;
    border-top: 2px solid #e8edd8;
    margin: 24px 0;
  }

  /* Primary button */
  .stButton > button[kind="primary"],
  .stFormSubmitButton > button {
    background: #A8CF39 !important;
    color: #1a1a1a !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 10px 24px !important;
    transition: background 0.2s;
  }
  .stButton > button[kind="primary"]:hover,
  .stFormSubmitButton > button:hover {
    background: #96bb2a !important;
  }

  /* Download buttons */
  .stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
  }

  /* Inputs */
  .stTextInput input, .stTextArea textarea, .stSelectbox select {
    border-radius: 8px !important;
    border-color: #dde8c0 !important;
  }
  .stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #A8CF39 !important;
    box-shadow: 0 0 0 2px rgba(168,207,57,0.2) !important;
  }

  /* Slug pill */
  .slug-pill {
    display: inline-block;
    background: #eef6cc;
    color: #4a6b10;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    font-family: monospace;
  }

  /* Link row */
  .link-row {
    background: #fff;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #eee;
  }
  .link-dest {
    color: #555;
    font-size: 0.84rem;
    word-break: break-all;
  }
</style>
""", unsafe_allow_html=True)

# ── Redirect handler ────────────────────────────────────────
params = st.query_params
if "r" in params:
    slug = params["r"]
    links, _ = gh_get_links()
    dest = links.get(slug)
    if dest:
        st.markdown(f'<meta http-equiv="refresh" content="0; url={dest}">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-card">
          <h4>Redirigiendo...</h4>
          <p>Serás redirigido a <strong>{dest}</strong> en un momento.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"El link **'{slug}'** no existe o fue eliminado.")
    st.stop()

# ── Password gate ───────────────────────────────────────────
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("""
    <div class="brand-header">
      <h1>🍃 Frutto QR Studio</h1>
      <p>Herramienta interna de generación de QR y gestión de links</p>
    </div>
    """, unsafe_allow_html=True)
    pwd = st.text_input("Contraseña de acceso", type="password", placeholder="Ingresa la contraseña...")
    if st.button("Entrar", use_container_width=True):
        if pwd == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# ── Brand header ────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
  <h1>🍃 Frutto QR Studio</h1>
  <p>Generá QR con logo · Links de WhatsApp · QR dinámicos actualizables</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📱 Generar QR", "💬 Link de WhatsApp", "🔗 Links Dinámicos"])

# ═══════════════════════════════════════════════════════════
#  TAB 1 — QR GENERATOR
# ═══════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="info-card">
      <h4>¿Qué hace esta sección?</h4>
      <p>Genera un código QR personalizado a partir de cualquier texto o URL. Podés subir el logo de Frutto
      para que aparezca integrado en el centro del QR. Luego descargás el resultado en PNG o PDF.</p>
      <ul>
        <li><strong>URL corta</strong> → QR menos denso, más fácil de escanear.</li>
        <li><strong>Con logo</strong> → activá la corrección de error alta (ya viene activada por defecto).</li>
        <li><strong>Para impresión</strong> → usá box size 12 o más y descargá en PDF.</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)

    with st.form("qr"):
        text = st.text_input("Texto o URL a codificar", "https://fruttofoods.com",
                             placeholder="https://fruttofoods.com")

        st.markdown('<p class="section-label">Apariencia</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            fill = st.color_picker("Color del QR", "#000000")
            back = st.color_picker("Color de fondo", "#FFFFFF")
            version = st.selectbox("Versión QR (auto = recomendado)", ["Auto"] + list(range(1, 40)), index=0)
            version = None if version == "Auto" else int(version)
        with col2:
            border = st.slider("Borde en blanco (quiet zone)", 4, 10, 6,
                               help="Mínimo recomendado: 6 módulos para impresión limpia.")
            box_size = st.slider("Tamaño de módulo (box size)", 10, 18, 12,
                                 help="Más alto = imagen más grande y nítida.")
            disk_scale = st.slider("Tamaño del disco del logo (%)", 24, 36, 30) / 100.0
            logo_in_disk = st.slider("Logo dentro del disco (%)", 60, 85, 72) / 100.0

        ring_px = st.slider("Anillo decorativo alrededor del logo (px)", 0, 6, 2)
        logo_file = st.file_uploader("Logo (PNG con fondo transparente, ideal)", type=["png", "jpg", "jpeg"])

        col3, col4 = st.columns(2)
        with col3:
            shape = st.radio("Forma del disco del logo", ["circle", "rounded"],
                             index=0, horizontal=True,
                             captions=["Círculo", "Cuadrado redondeado"])
        with col4:
            rounded_modules = st.toggle("Módulos redondeados", value=True if ROUNDED_OK else False,
                                        help="Suaviza los módulos del QR para un look más moderno.")
            shadow = st.toggle("Sombra en el logo", value=False)

        go = st.form_submit_button("Generar QR", use_container_width=True)

    if go:
        if not text.strip():
            st.error("Escribí un texto o URL válido.")
            st.stop()
        with st.spinner("Generando QR..."):
            qr = make_qr_matrix(text, version=version, border=border, box_size=box_size)
            base = render_qr_rounded(qr, fill, back) if (rounded_modules and ROUNDED_OK) else render_qr_square(qr, fill, back)
            if logo_file is None:
                st.markdown('<div class="warn-card"><p>💡 <strong>Sin logo:</strong> Subí un PNG del logo para el acabado profesional. Mostrando QR base.</p></div>', unsafe_allow_html=True)
                final_img = base
            else:
                logo = Image.open(logo_file)
                final_img = place_center_badge(base, logo, disk_scale=disk_scale, logo_in_disk=logo_in_disk,
                                               disk_shape=shape, ring_px=ring_px, drop_shadow=shadow)
        st.image(final_img, caption="QR generado", use_container_width=True)
        png = pil_to_png_bytes(final_img)
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("⬇ Descargar PNG", data=png, file_name="frutto_qr.png",
                               mime="image/png", use_container_width=True)
        with col_b:
            pdf = png_to_pdf_bytes(pil_to_png_bytes(final_img), caption=f"Enlace: {text}")
            st.download_button("⬇ Descargar PDF", data=pdf, file_name="frutto_qr.pdf",
                               mime="application/pdf", use_container_width=True)

# ═══════════════════════════════════════════════════════════
#  TAB 2 — WHATSAPP LINK
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="info-card">
      <h4>¿Qué hace esta sección?</h4>
      <p>Genera un link especial de WhatsApp (<code>wa.me</code>) que al tocarlo abre un chat directo
      con el número indicado. Podés incluir un mensaje pre-cargado para que el cliente no tenga que escribir nada.</p>
      <ul>
        <li>Ideal para packaging, flyers o redes sociales.</li>
        <li>El QR generado acá es <strong>estático</strong>: si cambiás el número o mensaje, hay que rehacer el QR.</li>
        <li>Para un link que no cambie aunque el número cambie, usá <strong>Links Dinámicos</strong>.</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="warn-card">
      <p>📞 <strong>Formato del número:</strong> incluí el código de país sin + ni espacios.
      Ej: Argentina 54 11 → <code>5491112345678</code></p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("wa"):
        phone = st.text_input("Número de WhatsApp", placeholder="5491112345678",
                              help="Código de país + código de área + número. Sin +, sin espacios.")
        message = st.text_area("Mensaje pre-cargado (opcional)",
                               placeholder="Hola! Me comunico desde el packaging de Frutto Foods...",
                               help="El cliente verá este texto listo para enviar cuando abra el chat.")
        go_wa = st.form_submit_button("Generar link y QR", use_container_width=True)

    if go_wa:
        if not phone.strip():
            st.error("Ingresá un número de teléfono.")
        else:
            wa_url = f"https://wa.me/{phone.strip()}"
            if message.strip():
                wa_url += f"?text={urllib.parse.quote(message.strip())}"

            st.markdown(f"""
            <div class="info-card">
              <h4>✅ Link generado</h4>
              <p style="word-break:break-all;">{wa_url}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.spinner("Generando QR..."):
                qr = make_qr_matrix(wa_url)
                img = render_qr_rounded(qr) if ROUNDED_OK else render_qr_square(qr)

            st.image(img, caption="QR del link de WhatsApp", use_container_width=True)
            png = pil_to_png_bytes(img)
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button("⬇ Descargar PNG", data=png, file_name="frutto_whatsapp_qr.png",
                                   mime="image/png", use_container_width=True)
            with col_b:
                pdf = png_to_pdf_bytes(pil_to_png_bytes(img), caption=f"WhatsApp: +{phone.strip()}")
                st.download_button("⬇ Descargar PDF", data=pdf, file_name="frutto_whatsapp_qr.pdf",
                                   mime="application/pdf", use_container_width=True)

# ═══════════════════════════════════════════════════════════
#  TAB 3 — DYNAMIC LINKS
# ═══════════════════════════════════════════════════════════
with tab3:
    app_url = st.secrets.get("APP_URL", "https://tu-app.streamlit.app")

    # ── How it works ──
    st.markdown("""
    <div class="info-card">
      <h4>¿Qué son los Links Dinámicos?</h4>
      <p>Un QR dinámico siempre apunta a la misma URL fija (la de esta app), pero esa URL
      redirige automáticamente a la dirección real que vos configurás acá.</p>
      <p style="margin-top:8px;"><strong>La ventaja clave:</strong> si el destino cambia, sólo actualizás el link acá —
      el QR impreso en packaging o folletería <strong>no hay que rehacerlo</strong>.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-label">Cómo funciona — paso a paso</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="step-card">
      <div class="step-num">1</div>
      <div class="step-text">
        <strong>Creás un slug (nombre corto)</strong>
        <p>Por ejemplo: <code>promo</code>, <code>menu</code>, <code>frutto2026</code>. Este nombre nunca cambia.</p>
      </div>
    </div>
    <div class="step-card">
      <div class="step-num">2</div>
      <div class="step-text">
        <strong>Asociás el slug a una URL destino</strong>
        <p>Ej: slug <code>promo</code> → <code>https://fruttofoods.com/promo-verano</code></p>
      </div>
    </div>
    <div class="step-card">
      <div class="step-num">3</div>
      <div class="step-text">
        <strong>Generás e imprimís el QR del slug</strong>
        <p>El QR codifica: <code>{app_url}/?r=promo</code> — esta URL nunca va a cambiar.</p>
      </div>
    </div>
    <div class="step-card">
      <div class="step-num">4</div>
      <div class="step-text">
        <strong>Cuando el destino cambia, editás el slug acá</strong>
        <p>Cambiás la URL destino y guardás. El QR ya impreso sigue funcionando apuntando al nuevo destino.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="frutto-divider">', unsafe_allow_html=True)

    # ── Existing links ──
    links, sha = gh_get_links()

    st.markdown('<p class="section-label">Links activos</p>', unsafe_allow_html=True)

    if links:
        for slug, dest in list(links.items()):
            col_slug, col_dest, col_del = st.columns([2, 5, 1])
            with col_slug:
                st.markdown(f'<span class="slug-pill">?r={slug}</span>', unsafe_allow_html=True)
            with col_dest:
                st.markdown(f'<p class="link-dest">↳ {dest}</p>', unsafe_allow_html=True)
            with col_del:
                if st.button("🗑", key=f"del_{slug}", help=f"Eliminar slug '{slug}'"):
                    del links[slug]
                    if gh_save_links(links, sha):
                        st.success(f"Slug '{slug}' eliminado.")
                        st.rerun()
                    else:
                        st.error("Error al guardar en GitHub.")
    else:
        st.markdown("""
        <div class="accent-card">
          <p>Todavía no hay links dinámicos. Creá el primero abajo.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="frutto-divider">', unsafe_allow_html=True)

    # ── New / edit link ──
    st.markdown('<p class="section-label">Crear o editar link</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="warn-card">
      <p>💡 Si ingresás un slug que ya existe, se actualiza la URL destino (sin borrar el QR impreso).</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("new_link"):
        new_slug = st.text_input("Slug", placeholder="promo, menu, verano2026...",
                                 help="Solo letras, números y guiones. Sin espacios.")
        new_dest = st.text_input("URL destino", placeholder="https://fruttofoods.com/promo")
        save = st.form_submit_button("Guardar link", use_container_width=True)

    if save:
        if not new_slug.strip() or not new_dest.strip():
            st.error("Completá los dos campos.")
        else:
            clean_slug = new_slug.strip().lower().replace(" ", "-")
            links[clean_slug] = new_dest.strip()
            if gh_save_links(links, sha):
                full_url = f"{app_url}/?r={clean_slug}"
                st.markdown(f"""
                <div class="info-card">
                  <h4>✅ Link guardado</h4>
                  <p>URL del QR a imprimir:</p>
                  <p style="font-family:monospace; font-size:0.9rem; margin-top:6px;">{full_url}</p>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
            else:
                st.error("Error al guardar en GitHub. Verificá el token.")

    # ── Generate QR for a slug ──
    if links:
        st.markdown('<hr class="frutto-divider">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Generar QR de un link dinámico</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-card">
          <h4>Este es el QR que imprimís</h4>
          <p>Descargá este QR y usalo en packaging, flyers o donde necesites. Nunca vas a tener que rehacerlo
          aunque cambies la URL destino desde esta app.</p>
        </div>
        """, unsafe_allow_html=True)
        selected = st.selectbox("Seleccionar slug", list(links.keys()))
        if st.button("Generar QR dinámico", use_container_width=True):
            qr_url = f"{app_url}/?r={selected}"
            with st.spinner("Generando QR..."):
                qr = make_qr_matrix(qr_url)
                img = render_qr_rounded(qr) if ROUNDED_OK else render_qr_square(qr)
            st.image(img, caption=f"QR → {qr_url}", use_container_width=True)
            png = pil_to_png_bytes(img)
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button("⬇ Descargar PNG", data=png, file_name=f"frutto_qr_{selected}.png",
                                   mime="image/png", use_container_width=True)
            with col_b:
                pdf = png_to_pdf_bytes(pil_to_png_bytes(img), caption=qr_url)
                st.download_button("⬇ Descargar PDF", data=pdf, file_name=f"frutto_qr_{selected}.pdf",
                                   mime="application/pdf", use_container_width=True)
