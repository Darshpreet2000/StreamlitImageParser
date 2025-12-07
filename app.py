import streamlit as st
import io
from processor import process_image

st.set_page_config(page_title="Doc Fixer", layout="wide")
st.title("📄 Digital Document Restore")
st.markdown("Upload a document. We will detect text, white it out, and re-type it digitally.")

uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        st.image(uploaded_file, caption="Original")

    if st.button("Process Document"):
        with st.spinner("Processing..."):
            try:
                result = process_image(uploaded_file.getvalue())
                if result:
                    with col2:
                        st.image(result, caption="Digitized")
                        
                        buf = io.BytesIO()
                        result.save(buf, format="PNG")
                        st.download_button("Download Result", buf.getvalue(), "fixed.png", "image/png")
                else:
                    st.error("No text found.")
            except Exception as e:
                st.error(f"Error: {e}")