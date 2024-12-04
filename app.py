import streamlit as st
import qrcode
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

# Función para generar el código QR
def generar_qr(link, fill_color="black", back_color="white"):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img

# Interfaz en Streamlit
st.title("Generador de Códigos QR")
link = st.text_input("Introduce el enlace:")
fill_color = st.color_picker("Elige el color del QR", "#000000")
back_color = st.color_picker("Elige el color de fondo", "#FFFFFF")

if st.button("Generar QR"):
    if link.strip():
        # Generar QR
        img = generar_qr(link, fill_color=fill_color, back_color=back_color)
        
        # Mostrar imagen QR
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        st.image(buffer, caption="Código QR generado")

        # Botón para descargar como imagen
        st.download_button(
            label="Descargar QR como imagen",
            data=buffer,
            file_name="codigo_qr.png",
            mime="image/png"
        )

        # Crear PDF
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        temp_image_path = "temp_qr.png"
        img.save(temp_image_path)  # Guardar la imagen temporalmente
        c.drawImage(temp_image_path, 100, 500, width=200, height=200)
        c.drawString(100, 450, f"Enlace: {link}")
        c.save()

        # Botón para descargar PDF
        pdf_buffer.seek(0)
        st.download_button(
            label="Descargar QR como PDF",
            data=pdf_buffer,
            file_name="codigo_qr.pdf",
            mime="application/pdf"
        )

        # Eliminar la imagen temporal
        os.remove(temp_image_path)
    else:
        st.error("Por favor, introduce un enlace válido.")
