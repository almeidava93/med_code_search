import streamlit as st

# Custom imports 
from med_code_search.multipage import MultiPage
from med_code_search.pages import code_search, feedback, update_search, search_v4_test, classifier, openai_search, multi_coding # import your pages here

def app():
    # Create an instance of the app 
    app = MultiPage()

    # Title of the main page
    st.title("Codificação de condições clínicas")

    # Add all your applications (pages) here
    app.add_page("CIAP2 e CID10 - v4", multi_coding.app)
    app.add_page("CIAP2 e CID10 - v3", openai_search.app)
    app.add_page("CIAP2 - v2", search_v4_test.app)
    app.add_page("CIAP2 e CID10 - v1", code_search.app)
    app.add_page("Codificador de motivos de consulta", classifier.app)
    app.add_page("Não encontrou?", feedback.app)
    app.add_page("Atualize o tesauro", update_search.app)

    # The main app
    app.run()

    no_sidebar_style = r"""
        <style>
            div[data-testid="stSidebarNav"] {display: none;}
            div[class="css-1qw3w76 e1fqkh3o4"] {margin-top: 100px;}
        </style>
    """
    st.markdown(no_sidebar_style, unsafe_allow_html=True)