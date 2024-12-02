import streamlit as st
import qrcode
from PIL import Image

# Título de la aplicación
st.title("Generador de Códigos QR")
st.write("Ingresa un enlace válido para generar un código QR.")

# Entrada de texto para el enlace
link = st.text_input("Introduce el enlace aquí:", placeholder="https://example.com")

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

        # Crear la imagen del código QR
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("codigo_qr.png")  # Guardar la imagen localmente

        # Mostrar la imagen en la app
        st.image("codigo_qr.png", caption="Código QR generado")
        st.success("¡Código QR generado exitosamente!")
    else:
        st.error("Por favor, ingresa un enlace válido.")
