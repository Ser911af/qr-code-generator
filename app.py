import streamlit as st
import qrcode
from PIL import Image
from io import BytesIO

# Título de la aplicación
st.title("Generador de Códigos QR")
st.write("Ingresa un enlace válido para generar un código QR personalizado y descargarlo.")

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

        # Mostrar la imagen en la app
        st.image(img, caption="Código QR generado")
        st.success("¡Código QR generado exitosamente!")

        # Convertir la imagen a bytes para descarga
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Botón para descargar el código QR
        st.download_button(
            label="Descargar Código QR",
            data=buffer,
            file_name="codigo_qr.png",
            mime="image/png"
        )
    else:
        st.error("Por favor, ingresa un enlace válido.")

