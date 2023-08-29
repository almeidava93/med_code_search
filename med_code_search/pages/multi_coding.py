import pandas as pd
import streamlit as st
from datetime import datetime as dt
import uuid
import re
from typing import List, Dict
from med_code_search.database import *
import logging

# Create a logger
logger = logging.getLogger('AdvancedLogger')
logger.setLevel(logging.WARNING)

# Create a file handler
fh = logging.FileHandler('my_log.log')

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to file handler
fh.setFormatter(formatter)

# Add file handler to logger
logger.addHandler(fh)

# Log messages
logger.info("")


def query_vector_database(input: str, n_results: int) -> pd.DataFrame:
    """
    This function takes an string as input, generates an embedding through OpenAI embeddings API,\
    uses the resulting embedding to query a vector database hosted in Pinecone. It creates a\
    pandas dataframe with the results. 
    """

    query_vector = get_input_embedding(input)

    # Use pinecone to retrieve the most similar vectors
    res = index.query(vector=query_vector, top_k=n_results, include_metadata=True, namespace="icpc-embeddings")

    # Organizing results for visualization and grouping by code
    results_df = pd.DataFrame(columns=['code', 'title', 'expression'])
    for match in res['matches']:
        icpc_code = match['metadata']['code']
        icpc_code_title = match['metadata']['title']
        expression = match['metadata']['expression']
        
        row = pd.DataFrame.from_dict([{
            'code': icpc_code,
            'title': icpc_code_title,
            'expression': expression
        }])

        results_df = pd.concat([results_df, row])

    return results_df


def extract_results(results_df: pd.DataFrame, codes_data: pd.DataFrame) -> List[Dict[str, str]]:
    results = []
    for row in results_df.to_dict('records'):
        related_cids = get_cid_title(get_cid_from_expression(row['expression']))
        
        res = {}
        res["expression"] = row['expression'].lower().strip()
        res["icpc_code"] = row['code']
        res["icpc_title"] = row['title']

        res["icd_codes"] = []
        for i, cid in enumerate(related_cids):
            res["icd_codes"].append(
                {
                    "icd_code": cid['CAT'],
                    "icd_title": cid["DESCRICAO"]
                }
            )

        res['consider'] = codes_data.loc[row['code'][0:3]]['considerar']
        res['inclusion_criteria'] = codes_data.loc[row['code'][0:3]]['critérios de inclusão']
        res['exclusion_criteria'] = codes_data.loc[row['code'][0:3]]['critérios de exclusão']

        results.append(res)
    
    return results


def render_results(results: List[Dict[str, str]]) -> None:
    for result in results:
        with st.expander(f"_{result['expression']}_"):
            st.write(f"**CIAP2:**  {result['icpc_code']} - {result['icpc_title']}")

            for icd in result["icd_codes"]:
                st.write(f"**CID10:** {icd['icd_code']} - {icd['icd_title']}")

            st.write(f"**considerar:** {result['consider']}")
            st.write(f"**criterios de inclusão:** {result['inclusion_criteria']}")
            st.write(f"**criterios de exclusão:** {result['exclusion_criteria']}")


def app():
    st.header('Busca de CIAP2 e CID10')
    st.write('Digite abaixo a condição clínica que deseja codificar e nós encontraremos para você os melhores códigos CIAP2 e CID10.')        
    st.text_input('Digite aqui o motivo de consulta', 
                  key="icpc_search_input", 
                  label_visibility='collapsed', 
                  on_change=save_on_change, 
                  args=["icpc_search_input", "ciap_search_input"], 
                  )
    
    if 'show_multicoding_message' not in st.session_state:
        st.session_state['show_multicoding_message'] = True

    if st.session_state['show_multicoding_message']:
        st.info("Agora você pode buscar mais de uma condição por vez! Basta separar as buscas por vírgula ou pelo conectivo 'e'. Experimenta :)")
        st.session_state['show_multicoding_message'] = False

    if st.session_state['icpc_search_input'] != "":
        inputs = re.split(r',| e ', st.session_state['icpc_search_input'])
        logger.info(f"Inputs: {inputs}")
        results = []
        n_results = 1 if len(inputs) > 1 else 5
        logger.info(f"Number of results per input: {n_results}")
        for input in inputs:
            results_df = query_vector_database(input.strip(), n_results)
            codes_data = get_code_data_from_firebase(results_df['code'].to_list())
            current_input_results = extract_results(results_df, codes_data)
            logger.info(f"Current input: {input}\n Current input results: {current_input_results}")
            results = results + current_input_results
        
        render_results(results)

        report = st.button("Reportar resultado inadequado ou impreciso", 
                           type='primary',
                           help='Clicando aqui você envia a sua busca e os resultados que está vendo para que possamos revisar e ajustar se precisar. Assim você nos ajuda a melhorar com apenas um clique :)')            
        if report:
            input = st.session_state['icpc_search_input']
            data = {
                "input": input,
                "results": results,
                "timestamp": dt.now(),
                "reviewed": False,
            }
            report_id = "report_id_" + str(uuid.uuid4())
            doc_ref = firestore_client.collection("report").document(report_id)
            doc_ref.set(data)
            st.toast("Seu feedback foi registrado! Obrigado por contribuir com o projeto :)")

    st.divider()

    st.markdown("""**Em caso de dúvidas ou feedbacks,** temos um grupo de suporte no WhatsApp. Você pode acompanhar as novidades por lá também. Só clicar [aqui](https://chat.whatsapp.com/HvNJJ0Yf1xiD0P3lKrWgtp)""")