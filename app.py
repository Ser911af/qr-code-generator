import streamlit as st
import qrcode
from PIL import Image
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Título de la aplicación
st.title("Generador de Códigos QR")
st.write("Ingresa un enlace válido para generar un código QR personalizado y descargarlo como imagen o PDF.")

# Entrada de texto para el enlace
link = st.text_input("Introduce el enlace aquí:", placeholder="https://example.com")

# Opciones de personalización de colores
st.write("Personaliza tu código QR:")
fill_color = st.color_picker("Color de relleno", "#000000")  # Negro por defecto
back_color = st.color_picker("Color de fondo", "#FFFFFF")  # Blanco por defecto

# Botón para generar el código QR
if st.button("Generar QR"):
    if link.strip():  # Validar que el enlace no esté vacío
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(link)
        qr.make(fit=True)

        # Crear la imagen del código QR con colores personalizados
        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Convertir la imagen a un formato compatible (bytes) para PNG
        buffer_png = BytesIO()
        img.save(buffer_png, format="PNG")
        buffer_png.seek(0)

        # Convertir la imagen a un formato PDF
        buffer_pdf = BytesIO()
        pdf_canvas = canvas.Canvas(buffer_pdf, pagesize=letter)
        img_temp = BytesIO()
        img.save(img_temp, format="PNG")
        img_temp.seek(0)
        pil_image = Image.open(img_temp)

        # Ajustar el tamaño en el PDF
        width, height = pil_image.size
        pdf_canvas.drawImage(img_temp, 100, 500, width=200, height=200)
        pdf_canvas.save()
        buffer_pdf.seek(0)

        # Mostrar la imagen en la app
        st.image(buffer_png, caption="Código QR generado")
        st.success("¡Código QR generado exitosamente!")

        # Botón para descargar como imagen PNG
        st.download_button(
            label="Descargar como Imagen (PNG)",
            data=buffer_png,
            file_name="codigo_qr.png",
            mime="image/png"
        )

        # Botón para descargar como PDF
        st.download_button(
            label="Descargar como PDF",
            data=buffer_pdf,
            file_name="codigo_qr.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Por favor, ingresa un enlace válido.")
