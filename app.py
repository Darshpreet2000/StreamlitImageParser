import streamlit as st
import io
from processor import process_image

st.set_page_config(page_title="DocuRevive: Digital Document Restoration", layout="wide")
st.markdown("""
# 📝 DocuRevive
#### Professional Document Restoration & Digitization
Effortlessly restore, clean, and digitize scanned documents. Our tool detects text, removes artifacts, and re-types content for a crisp, digital result.
""")

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
                        
                        # Dynamic filename logic
                        import time
                        base_name = getattr(uploaded_file, 'name', None)
                        if base_name:
                            name_no_ext = base_name.rsplit('.', 1)[0]
                            download_name = f"{name_no_ext}_digitized.png"
                        else:
                            download_name = f"digitized_{int(time.time())}.png"
                        
                        st.download_button("Download Result", buf.getvalue(), download_name, "image/png")
                else:
                    st.error("No text found.")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by Darshpreet Singh</div>", unsafe_allow_html=True)