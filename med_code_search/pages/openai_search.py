import pandas as pd
import streamlit as st
from datetime import datetime as dt
import uuid
from med_code_search.database import *

def app():
    st.header('Busca semântica de CIAP2 e CID10')
    st.write('Digite abaixo a condição clínica que deseja codificar e nós encontraremos para você os melhores códigos CIAP2 e CID10.')        
    with st.expander("Saiba mais sobre como isso tudo funciona..."):
        st.markdown("""
Esta versão utiliza uma **busca semântica** para encontrar o conceito mais próximo da sua busca. 
Mais especificamente, ela usa representações numéricas dos textos que são geradas a partir de redes neurais gigantescas. 

Neste caso, estamos utilizando a rede neural disponibilizada pela OpenAI, empresa que criou o chatGPT e gerou um marco na história do processamento de linguagem natural. 
Existem ainda imprecisões, porém também uma série de vantagens em relação aos modelos anteriores. 
Esta versão é **capaz de encontrar sinônimos e conceitos parecidos**, mesmo que estes não estejam escritos da maneiras semelhantes. Por isso o nome busca semântica. 
Ela também é **capaz de lidar alguns erros de digitação** sem prejuízo na qualidade dos resultados. 

Os resultados, porém, não são perfeitos. Talvez você veja que resultados numa ordem diferente do esperado. Também existem imprecisões no mapeamento entre os conceitos e os códigos CIAP-2 e CID-10. 
Qualquer estranhamento em relação aos resultados encontrados **não deixe de dar seu feedback**. Você pode fazer isso com apenas um clique no botão que aparece após os resultados. Assim, a sua busca e os resultados encontrados serão armazenados e revisados posteriormente. 

**Compartilhe** também com as pessoas que possam ver utilidade nesta ferramenta. Quanto mais pessoas usando, mais conseguimos deixar ela mais precisa e útil para todos.
""")

    st.text_input('Digite aqui o motivo de consulta', key="icpc_search_input", label_visibility='collapsed', on_change=save_on_change, args=["icpc_search_input", "ciap_search_input"])
    if st.session_state['icpc_search_input'] != "":
        query_vector = get_input_embedding(st.session_state['icpc_search_input'])

        # Use pinecone to retrieve the most similar vectors
        res = index.query(vector=query_vector, top_k=5, include_metadata=True, namespace="icpc-embeddings")

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

            #results_df = results_df.groupby(by='code').agg({'title': 'first', 'expression': ' | '.join}).reset_index()

        codes_data = get_code_data_from_firebase(results_df['code'].to_list())

        results = []
        for row in results_df.to_dict('records'):
            with st.expander(f"_{row['expression'].lower()}_"):
            #with st.expander(f"__{row['code']} - {row['title']}__"):
                st.write(f"**CIAP2:**  {row['code']} - {row['title']}")
                related_cids = get_cid_title(get_cid_from_expression(row['expression']))
                
                res = {}
                res["expression"] = row['expression']
                res["icpc_code"] = row['code']
                res["icpc_title"] = row['title']

                for i, cid in enumerate(related_cids):
                    st.write(f"**CID10:** {cid['CAT']} - {cid['DESCRICAO']}")
                    res[f"icd_code_{i+1}"] = cid['CAT']
                    res[f"icd_title_{i+1}"] = cid['DESCRICAO']
                
                st.write(f"**considerar:** {codes_data.loc[row['code'][0:3]]['considerar']}")
                st.write(f"**criterios de inclusão:** {codes_data.loc[row['code'][0:3]]['critérios de inclusão']}")
                st.write(f"**criterios de exclusão:** {codes_data.loc[row['code'][0:3]]['critérios de exclusão']}")

                res['consider'] = codes_data.loc[row['code'][0:3]]['considerar']
                res['inclusion_criteria'] = codes_data.loc[row['code'][0:3]]['critérios de inclusão']
                res['exclusion_criteria'] = codes_data.loc[row['code'][0:3]]['critérios de exclusão']

                results.append(res)

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
            st.success("Seu feedback foi registrado! Obrigado por contribuir com o projeto :)")
