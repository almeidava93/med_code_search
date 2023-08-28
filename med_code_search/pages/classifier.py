#source: https://newscatcherapi.com/blog/how-to-annotate-entities-with-spacy-phrase-macher

from multiprocessing.spawn import prepare
import streamlit as st
from unidecode import unidecode

import spacy
from spacy.matcher import PhraseMatcher
from spacy.matcher import Matcher
from spacy.tokens import Span

import pandas as pd
import pickle
import time
import pkg_resources
from pathlib import Path

#Custom packages
from med_code_search.database import *

# Next steps:
# - combine phrase matcher with matcher for more accuracy and generalizability in specific cases

firestore_client = load_firestore_client()

@st.cache_resource
def load_matcher():
    file_stream = pkg_resources.resource_stream(__name__, 'data/tk_matcher.pkl')
    pickle_in = open(file_stream,"rb")
    matcher = pickle.load(pickle_in)
    return matcher


@st.cache_data
def join_columns(dataframe, column_names, delimiter=' | ', drop_duplicates=False):
  df = dataframe[column_names].agg(delimiter.join, axis=1)
  if drop_duplicates==True: df.drop_duplicates()
  return df


@st.cache_data
def get_code_data_from_firebase(code, fields=['codigo','`titulo original`','`considerar`','`critérios de inclusão`', '`critérios de exclusão`']) -> pd.DataFrame:
    if type(code)==str:
        code = [code]

    if type(code)==pd.core.series.Series:
        code = list(code)

    if type(code)==pd.DataFrame:
        try:
            code = list(code['code'])
        except KeyError:
            code = list(code['CIAP2_Código1'])

    if type(code)==list:
        query = firestore_client.collection('ciap_data').select(field_paths=fields).where('codigo','in', code).get()
        docs_list = [doc.to_dict() for doc in query]
        docs_df = pd.DataFrame.from_records(docs_list)
        docs_df.index = docs_df['codigo']
        docs_df.drop('codigo', axis=1, inplace=True)
        return docs_df
    else:
        raise TypeError("This function expects a string with one ICPC-2 code or a iterable (list, pandas series, dataframe with 'code' column) of strings, each one corresponding to an ICPC-2 code")


def test_matcher(text, matcher):
    nlp = spacy.blank("pt")
    text = unidecode(text)
    doc = nlp(text)
    matches = matcher(doc)
    ents = []
    for match_id, start, end in matches:
        span = doc[start:end]
        #print(span.text, match_id, start, end, nlp.vocab.strings[match_id])
        ents.append({'text': span.text, 'match_id': match_id, 'start': start, 'end': end, 'ciap': matcher.vocab.strings[match_id]})
    
    # Organizing results for visualization and grouping by code
    results_df = pd.DataFrame(columns=['ciap', 'titulo original', 'text'])
    for ent in ents:
        row = pd.DataFrame.from_dict({'ciap': [ent['ciap']], 'titulo original': get_code_data_from_firebase(ent['ciap'])['titulo original'], 'text': [ent['text']]})
        results_df = pd.concat([results_df, row])
    results_df = results_df.drop_duplicates().groupby(['ciap'], as_index=False, sort=False).agg({'titulo original': 'first', 'text': ' | '.join})
    if len(results_df)>0:
        results_df['ciap'] = join_columns(results_df, ['ciap','titulo original'], delimiter=' | ', drop_duplicates=False)
        st.write(f'Para o motivo de consulta acima, os códigos mais compatíveis que encontramos são:')
        for row in results_df[['ciap', 'text']].to_numpy().tolist():
            with st.expander(f"{row[0]}"):
                st.write(f"_{row[1]}_")


def app():
    matcher = load_matcher()
    with st.container():
        st.header('Classificador de motivos de consulta')
        st.write('Digite abaixo o texto referente ao motivo de consulta de um atendimento. Nós te ajudaremos a encontrar a melhor codificação para o seu atendimento.')
        st.text_area('Motivo de consulta:', key="text", on_change=save_on_change, args=["text", "classifier"])
        if st.session_state['text'] != "":
            t0 = time.time()
            test_matcher(st.session_state['text'], matcher)
            t1 = time.time()
            search_time = round(t1-t0,3)
            st.text(f'Texto analisado em {search_time} seconds \n')
