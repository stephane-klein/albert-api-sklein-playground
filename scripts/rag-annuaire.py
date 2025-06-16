#!/usr/bin/env python3
import os
from inspect import cleandoc
from openai import OpenAI
import requests

client = OpenAI(
    api_key=os.environ['ALBERT_OPENAI_API_KEY'],
    base_url="https://albert.api.etalab.gouv.fr/v1/"
)

history = []
# question = "De quel couleur est le soleil ?"
question = "Qui est François Bayrou ?"

# Step1: Query Reformulation
query_reformulation_result = client.chat.completions.create(
    model="albert-small",
    stream=False,
    temperature=0.1,
    max_tokens=50,
    messages=[
        {
            "role": "system",
            "content": cleandoc("""
                Tu es Assistant Administrations, un assistant développé par l'Etalab qui répond à des
                questions en te basant sur un contexte.

                Tu parles en français. Tu es précis et poli.

                Tu es connecté aux collections suivantes : "annuaire-administrations-etat" sur AlbertAPI.

                Ce que tu sais faire : Tu sais répondre aux questions et chercher dans les bases de connaissance de Albert API
                qui concerne les administrations publiques.

                Pour les questions sur des sujets spécifiques autres que les administrations publiques,
                invites l'utilisateur à se tourner vers un autre assistant spécialisé.

                Ne donnes pas de sources si tu réponds à une question meta ou sur toi.
            """)
        },
        {
            "role": "user",
            "content": cleandoc(f"""
                Tu es un assistant qui cherche des documents pour répondre à une question.

                Tu peux chercher des informations sur les administrations publiques ou les personnes y travaillant en utilisant les mots clés suivants :

                - nom et prénom de la personne
                - nom de l'administration
                - code postal
                - ville
                - pays

                Pour une recherche sur une personne, tu peux répondre avec uniquement le nom et prénom.

                Analyse cette question d'utilisateur et détermine si elle nécessite une recherche dans la base de données.

                HISTORIQUE:

                {history}

                QUESTION ACTUELLE: "{question}"

                TÂCHE:

                - Si la question nécessite une recherche documentaire (informations factuelles, procédures, tarifs, etc.),
                  reformule-la en une question complète et autonome qui intègre si besoin le contexte de l'historique.
                - Réponds uniquement par la question reformulée.
                - Si la question N'A PAS BESOIN de recherche documentaire, réponds exactement: no_search

                Exemple de CAS de no_search:

                - Salutations (bonjour, merci, au revoir)
                - Questions sur ton fonctionnement
                - Demandes de clarification vagues sans contexte suffisant
                - Conversations générales
                - Questions d'opinion

                EXEMPLES:

                - Historique: "USER: Quel est le prix du renouvellement de carte d'identité ?"
                - Question: "Comment faire ?" → Comment renouveler une carte d'identité ?
                - Question: "Bonjour" → no_search
                - Question: "Tu peux m'aider ?" → no_search
            """)
        }
    ]
).choices[0].message.content
print(query_reformulation_result)

if query_reformulation_result == "no_search":
    print("pas de recherche")
else:
    # Launch search in "State administrations directory" collection of
    # the Albert API Vector database.
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ['ALBERT_OPENAI_API_KEY']}'
    })
    search_response = session.post(
        'https://albert.api.etalab.gouv.fr/v1/search',
        json={
            'collections': [783],         # Annuaire des administrations d'état
            'rff_k': 20,                  # for now I don't know what this is
            'k': 3,                       # Top K
            'method': 'semantic',         # for now I don't know the functional consequences
            'score_threshold': 0.35,      # for now I don't know what this is
            'web_search': False,
            'prompt': query_reformulation_result,
            'additionalProp1': {}
        }
    ).json()["data"]
    # import pprint
    # pprint.pprint([row["chunk"]["content"] for row in search_response])

    rerank_response = session.post(
        'https://albert.api.etalab.gouv.fr/v1/rerank',
        json={
            "prompt": question,
            "input": [row["chunk"]["content"] for row in search_response],
            "model": "BAAI/bge-reranker-v2-m3"
        }
    ).json()['data']
    # Reorder search_response with rerank order
    search_response = [
        search_response[row['index']] for row in rerank_response
    ]
    import pprint
    pprint.pprint([row["chunk"]["content"] for row in search_response])
    

    # result = client.chat.completions.create(
    #     model="albert-small",
    #     stream=False,
    #     temperature=0.2,
    #     max_tokens=2000,
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": cleandoc(f"""
    #                 <context trouvé dans la base>
    #                 {context}
    #                 </context trouvé dans la base>
    #
    #                 En t'aidant si besoin du le contexte ci-dessus, réponds à cette question :
    #
    #                 <question>
    #                 {question}
    #                 </question>
    #             """)
    #         }
    #     ]
    # )
