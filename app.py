import streamlit as st
import qrcode
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image

# Título de la app
st.title("Generador de Códigos QR")

# Entrada para el enlace
link = st.text_input("Introduce un enlace para generar el código QR:")

# Opciones de personalización
color_frontal = st.color_picker("Elige el color del código QR:", "#000000")
color_fondo = st.color_picker("Elige el color de fondo del código QR:", "#FFFFFF")

# Botón para generar el código QR
if st.button("Generar QR"):
    if link.strip():  # Verificar que el enlace no esté vacío
        # Crear el código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color=color_frontal, back_color=color_fondo)
        
        # Mostrar la imagen en Streamlit
        st.image(img, caption="Código QR generado")

        # Guardar la imagen en memoria (PNG)
        buffer_png = BytesIO()
        img.save(buffer_png, format="PNG")
        buffer_png.seek(0)

        # Crear un archivo PDF con la imagen del QR
        buffer_pdf = BytesIO()
        pdf_canvas = canvas.Canvas(buffer_pdf, pagesize=letter)
        img_temp = BytesIO()
        img.save(img_temp, format="PNG")
        img_temp.seek(0)
        pdf_canvas.drawImage(img_temp, 100, 500, width=200, height=200)
        pdf_canvas.save()
        buffer_pdf.seek(0)

        # Opciones de descarga
        st.download_button(
            label="Descargar como Imagen (PNG)",
            data=buffer_png,
            file_name="codigo_qr.png",
            mime="image/png"
        )

        st.download_button(
            label="Descargar como PDF",
            data=buffer_pdf,
            file_name="codigo_qr.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Por favor, introduce un enlace válido.")

