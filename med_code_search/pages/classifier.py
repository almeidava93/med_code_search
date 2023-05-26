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

#Custom packages
from med_code_search.database import *

# Next steps:
# - combine phrase matcher with matcher for more accuracy and generalizability in specific cases

firestore_client = load_firestore_client()

@st.cache_data
def load_data():
    pickle_in = open("matcher.pickle","rb")
    matcher1 = pickle.load(pickle_in)

    pickle_in = open("ciap_dict.pickle","rb")
    ciap_dict = pickle.load(pickle_in)
    
    nlp = spacy.load('pt_core_news_lg')

    return nlp, ciap_dict, matcher1


@st.cache_data
def join_columns(dataframe, column_names, delimiter=' | ', drop_duplicates=False):
  df = dataframe[column_names].agg(delimiter.join, axis=1)
  if drop_duplicates==True: df.drop_duplicates()
  return df

def prepare_matcher():
    nlp, ciap_dict, matcher1 = load_data()
    
    #Adding some customised patterns to the matcher
    matcher2 = Matcher(matcher1.vocab)

    label = '-47' # Ex.: encaminhamento para ginecologia, deseja/quer/gostaria ser encaminhado para cardio, quer fazer acompanhamento com especialista
    pattern = [[{'POS': 'VERB', 'LEMMA': {'IN': ['gostar', 'querer', 'desejar']}}, {'OP':'?'}, {'OP':'?'}, {'OP':'?'},
                {'LEMMA': {'IN':['encaminhamento','encaminhar', 'acompanhamento']}}, {'POS': 'ADP', 'OP': '?'}, {'POS': 'NOUN'}]
        ]
    matcher2.add(label, pattern)

    label = '-60' # Ex.: resultados de um exame qualquer ou de exames
    patterns = [
        [{'LEMMA': 'resultar', 'POS': 'NOUN'}, {'POS': 'ADP', 'OP': '?'}, {'POS': 'NOUN'}],
        [{'LEMMA': {'IN': ['avaliação', 'avaliar']}}, {'OP':'*'}, {'LEMMA': {'IN':['realizar']}}],
        [{'LEMMA': {'IN': ['avaliação', 'avaliar']}}, {'OP':'*'}, {'LEMMA': {'IN':['exame']}}]
    ]
    matcher2.add(label, patterns)

    label = 'K85' # Ex.: pico hipertensivo
    patterns = [
        [{'LEMMA': 'pico', 'POS': 'NOUN', 'DEP': 'obj'}, {'LEMMA': 'hipertensivo', 'POS': 'ADJ', 'DEP': 'amod'}],
        [{'LEMMA': 'descontrolar', 'POS': {'IN': ['NOUN', 'VERB']}}, {'OP': '*'}, {'LEMMA': {'IN': ['pressão', 'pressao']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L01' # Ex.: dor pescoço, desconforto, incômodo, tensão
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'tensão', 'rigidez']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'rigidez']}}, {'LEMMA': {'IN':['coluna']}, 'OP': '?'}, {'LEMMA': {'IN':['pescoço', 'cervical']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L02' # Ex.: dor nas costas, na dorsal, no dorso
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'tensão']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao']}}, {'LEMMA': {'IN':['coluna']}, 'OP': '?'}, {'LEMMA': {'IN':['costa', 'dorsal', 'dorso']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L03' # Ex.: dor lombar, desconforto na lombar, na coluna lombar
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao']}}, {'LEMMA': {'IN':['coluna']}, 'OP': '?'}, {'LEMMA': {'IN':['lombar', 'sacral', 'sacroiliaca', 'coccix', 'lombo-sacra', 'lombossacra', 'costo-lombar', 'costolombar']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L04' # Ex.: dor torácica, desconforto
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'aperto', 'opressao']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao']}}, {'LEMMA': {'IN':['peito', 'torax', 'toracico', 'toracica', 'toracicos', 'toracicas', 'esternal', 'pleural', 'pleuritica', 'costal']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L05' # Ex.: dor axilar, desconforto na axila
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao']}}, {'LEMMA': {'IN':['axila', 'axilar']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L07' # Ex.: dor mandíbula
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'tensao', 'disfuncao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'disfuncao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'LEMMA': {'IN':['mandíbula', 'mandibula', 'mandibular', 'ATM', 'temporo-mandibular']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L08' # Ex.: dor ombro, desconforto ombro
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'inchaco', 'rigidez', 'derrame', 'edema', 'tumefacao']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'inchaco', 'rigidez']}}, {'LEMMA': {'IN':['ombro', 'acromioclavicular', 'esternoclavicular']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L09' # Ex.: dor braço
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao']}}, {'LEMMA': {'IN':['membro']}, 'OP': '?'}, {'LEMMA': {'IN':['braço', 'braco', 'bracos', 'superior']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L10' # Ex.: dor cotovelo
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'LEMMA': {'IN':['cotovelo']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L11' # Ex.: dor punho
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'LEMMA': {'IN':['punho']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L15' # Ex.: dor joelho, desconforto no joelho
    patterns = [
        [{'LEMMA': {'IN':['dor', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['dor', '.', 'desconfortar', 'incomodar', 'tensão', 'tensao', 'derrame', 'edema', 'tumefacao', 'inchaco', 'rigidez']}}, {'LEMMA': {'IN':['joelho', 'joelhar', 'patela']}}]
    ]
    matcher2.add(label, patterns)

    label = 'L80' # Ex.: luxação/luxou patela, ombro etc
    patterns = [
        [{'LEMMA': {'IN':['luxar', 'luxacao', 'luxação']}}, {'OP':'*'}, {'POS': 'NOUN'}]
    ]
    matcher2.add(label, patterns)

    label = 'N07' # Ex.: crise convulsiva, convulsão, crise de ausência
    patterns = [
        [{'LEMMA': 'crise', 'POS': 'NOUN'}, {'POS': 'ADP', 'OP': '?'}, {'POS': 'NOUN', 'LEMMA': {'IN':['ausencia', 'ausência']}}],
        [{'LEMMA': 'crise', 'POS': 'NOUN', 'OP': '?'}, {'LEMMA': {'IN':['convulsivo', 'convulsão']}}],
        [{'LEMMA': {'IN': ['crise', 'convulsão', 'convulsao', 'convulsoes']}}, {'LEMMA': {'IN': ['tonico', 'tonico-clonica', 'tonico-clonico', 'tonico-clonicos', 'tonico-clonicas']}}, {'LEMMA': {'IN': ['clonica', 'clonico']}, 'OP': '?'}, {'LEMMA': {'IN': ['generalizar']}, 'OP': '?'}]
    ]
    matcher2.add(label, patterns)

    label = 'P01' # Ex.: sentir-se agitado, nervoso
    patterns = [
        [{'LEMMA': {'IN': ['sentir']}}, {'LEMMA': {'IN': ['agitar', 'nervoso']}}]
    ]
    matcher2.add(label, patterns)
    
    label = 'P15' # Ex.: etilismo, consumo de álcool
    patterns = [
        [{'LEMMA':{'IN': ['consumir']}}, {'OP':'*', 'IS_PUNCT': False}, {'LEMMA':{'IN': ['álcool', 'alcool']}}],
        [{'LEMMA':{'IN': ['consumir']}}, {'OP':'*', 'IS_PUNCT': False}, {'LEMMA':{'IN': ['bebido']}}, {'LEMMA':{'IN': ['alcoolica','alcoolicas']}}]
    ]
    matcher2.add(label, patterns)

    label = 'P17' # Ex.: tabagismo, consumo de cigarro
    patterns = [
        [{'LEMMA':{'IN': ['consumir']}}, {'OP':'*', 'IS_PUNCT': False}, {'LEMMA':{'IN': ['cigarrar']}}]
    ]
    matcher2.add(label, patterns)

    label = 'P74' # Ex.: crise de ansiedade, crise ansiosa
    patterns = [
        [{'LEMMA': {'IN': ['crise']}, 'POS': {'IN': ['NOUN']}}, {'OP':'*', 'LEMMA':{'NOT_IN':['crise']}, 'IS_PUNCT': False}, {'LEMMA':{'IN': ['ansiedade', 'ansioso']}}]
    ]
    matcher2.add(label, patterns)

    label = 'P77' # Ex.: tentativa de suicídio
    patterns = [
        [{'LEMMA': {'IN': ['tentativo', 'tentar', 'pensar', 'pensamento', 'desejar', 'querer']}, 'POS': {'IN': ['NOUN', 'VERB']}}, {'OP':'*'}, {'LEMMA': 'se', 'OP': '?'}, {'LEMMA':{'IN': ['suicidio', 'suicidios', 'suicidar-se', 'suicidar', 'matar', 'morrer', 'morte']}}],
        [{'LEMMA': {'IN': ['ideacao', 'ideacoes', 'ideação']}, 'POS': 'NOUN'}, {'LEMMA': 'suicidar', 'POS': 'ADJ'}]
    ]
    matcher2.add(label, patterns)

    label = 'S08' # Ex.: manchas na pele, nos pés, no rosto
    patterns = [
        [{'LEMMA': 'manchar', 'POS': 'NOUN'}, {'OP':'*'}, {'POS': 'NOUN'}]
    ]
    matcher2.add(label, patterns)

    label = 'S21' # Ex.: queda de cabelo
    patterns = [
        [{'LEMMA': 'pelar', 'POS': 'NOUN'}, {'OP':'*'}, {'LEMMA': {'IN': ['descamar']},'POS': 'VERB'}],
        [{'LEMMA': {'IN': ['descamação', 'descamacao']}}, {'OP':'*'}, {'LEMMA': 'pelar', 'POS': 'NOUN'}]
    ]
    matcher2.add(label, patterns)

    label = 'S23' # Ex.: queda de cabelo
    patterns = [
        [{'LEMMA': 'cabelo', 'POS': 'NOUN'}, {'OP':'*'}, {'LEMMA': {'IN': ['cair']},'POS': 'VERB'}]
    ]
    matcher2.add(label, patterns)

    label = 'T07' # Ex.: ganho de peso, aumento de peso
    patterns = [
        [{'LEMMA': {'IN':['aumentar', 'ganhar']}, 'POS': {'IN':['NOUN', 'VERB']}}, {'OP':'*'}, {'LEMMA': {'IN': ['peso']},'POS':{'IN': ['NOUN']}, 'DEP': 'nmod'}]
    ]
    matcher2.add(label, patterns)

    label = 'X04' # Ex.: dor na relação sexual, dor no sexo
    patterns = [
        [{'LEMMA': 'dor', 'POS': 'NOUN'}, {'OP':'*'}, {'LEMMA': {'IN': ['sexo', 'sexual']},'POS':{'IN': ['ADJ', 'NOUN']}}]
    ]
    matcher2.add(label, patterns)

    label = 'X18' # Ex.: dor nas mamas
    patterns = [
        [{'LEMMA': 'dor', 'POS': 'NOUN'}, {'OP':'*'}, {'LEMMA': {'IN': ['mamar', 'mamário']},'POS':{'IN': ['ADJ', 'VERB', 'NOUN']}}]
    ]
    matcher2.add(label, patterns)

    return matcher2



def test_matcher(text):
    text = unidecode(text)
    doc = nlp(text)
    matches1 = matcher1(doc)
    ents = []
    for match_id, start, end in matches1:
        span = doc[start:end]
        #print(span.text, match_id, start, end, nlp.vocab.strings[match_id])
        ents.append({'text': span.text, 'match_id': match_id, 'start': start, 'end': end, 'ciap': matcher1.vocab.strings[match_id]})
    matches2 = matcher2(doc)
    for match_id, start, end in matches2:
        span = doc[start:end]
        #print(span.text, match_id, start, end, nlp.vocab.strings[match_id])
        ents.append({'text': span.text, 'match_id': match_id, 'start': start, 'end': end, 'ciap': matcher2.vocab.strings[match_id]})
    # Organizing results for visualization and grouping by code
    results_df = pd.DataFrame(columns=['ciap', 'titulo original', 'text'])
    for ent in ents:
        row = pd.DataFrame.from_dict({'ciap': [ent['ciap']], 'titulo original': [ciap_dict.get(ent['ciap']).get('titulo original')], 'text': [ent['text']]})
        results_df = pd.concat([results_df, row])
    results_df = results_df.drop_duplicates().groupby(['ciap'], as_index=False, sort=False).agg({'titulo original': 'first', 'text': ' | '.join})
    results_df['ciap'] = join_columns(results_df, ['ciap','titulo original'], delimiter=' | ', drop_duplicates=False)
    st.write(f'Para o motivo de consulta acima, os códigos mais compatíveis que encontramos são:')
    for row in results_df[['ciap', 'text']].to_numpy().tolist():
      with st.expander(f"{row[0]}"):
        st.write(f"_{row[1]}_")

# def save_on_change(key: str):
#     doc_ref = firestore_client.collection("classifier")
#     input_id = 'input_id_' + str(uuid.uuid4()) #id for document name
#     datetime = dt.now() #date and time of search
#     doc_ref.document(input_id).set(
#             {
#                 key: st.session_state[key],
#                 "timestamp": datetime
#             },
#             merge=True
#         )

def app():
    global nlp, ciap_dict, matcher1, matcher2
    nlp, ciap_dict, matcher1 = load_data()
    matcher2 = prepare_matcher()
    with st.container():
        st.header('Classificador de motivos de consulta')
        st.write('Digite abaixo o texto referente ao motivo de consulta de um atendimento. Nós te ajudaremos a encontrar a melhor codificação para o seu atendimento.')
        st.text_area('Motivo de consulta:', key="text", on_change=save_on_change, args=["text", "classifier"])
        if st.session_state['text'] != "":
            t0 = time.time()
            test_matcher(st.session_state['text'])
            t1 = time.time()
            search_time = round(t1-t0,3)
            st.text(f'Texto analisado em {search_time} seconds \n')
