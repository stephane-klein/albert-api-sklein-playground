#!/usr/bin/env python3
import os
from typing import List, Union, Generator, Iterator, Optional
from inspect import cleandoc
import argparse

from pydantic import BaseModel
from openai import OpenAI
from jinja2 import Template
import requests

# This script contains boilerplate code that may seem unnecessary or obscure at first glance,
# but it plays an essential role depending on the context of use.

# In fact, this code can be used in three different ways:

# 1. As a standalone program:  
#    It can be run directly from the command line,  
#    via the standard entry point `if __name__ == “__main__”:`.
#
# 2. For unit testing purposes:  
#    Automated tests are available in the file `./test_rag_annuaire.py`.
#
# 3. In integration with a Web UI interface:  
#    The script is also designed to be usable as a component 
#    in Open WebUI pipelines.

class Pipeline:
    class Valves(BaseModel):
        ALBERT_OPENAI_API_KEY: Optional[str] = None

    async def on_startup(self):
        print(f"on_startup: {__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown: {__name__}")

    def __init__(self):
        self.valves = self.Valves(**{
            "ALBERT_OPENAI_API_KEY": os.getenv("ALBERT_OPENAI_API_KEY", "your-albert-openai-api-key-here")
        })
        self.name = "search annuaire RAG"

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict
    ) -> Union[str, Generator, Iterator]:
        query = user_message

        client = OpenAI(
            api_key=self.valves.ALBERT_OPENAI_API_KEY,
            base_url="https://albert.api.etalab.gouv.fr/v1/"
        )

        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Je cherche...",
                    "done": False,
                },
            }
        }

        # Step1: Query Reformulation
        query_reformulation_result = client.chat.completions.create(
            model="albert-small",
            stream=False,
            temperature=0,
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

                        QUESTION ACTUELLE: "{query}"

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

        if query_reformulation_result == "no_search":
            print("pas de recherche")
        else:
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": f"Recherche en cours pour '{ query_reformulation_result }'",
                        "done": False,
                    },
                }
            }

            # Launch search in "State administrations directory" collection of
            # the Albert API Vector database.
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.valves.ALBERT_OPENAI_API_KEY}'
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

            rerank_response = session.post(
                'https://albert.api.etalab.gouv.fr/v1/rerank',
                json={
                    "prompt": query,
                    "input": [row["chunk"]["content"] for row in search_response],
                    "model": "BAAI/bge-reranker-v2-m3"
                }
            ).json()['data']

            # Reorder search_response with rerank order
            search_response = [
                search_response[row['index']] for row in rerank_response
            ]


            # Final step, response generation
            generate_response_prompt = Template(cleandoc("""
                <context trouvé dans la base>
                {%- for response in search_response -%}
                    {%- if response.chunk.metadata.people_in_charge[0].personne.prenom %}
                - {{ response.chunk.metadata.people_in_charge[0].personne.prenom }} {{ response.chunk.metadata.people_in_charge[0].personne.nom }} {{ response.chunk.metadata.people_in_charge[0].fonction }} {{ response.chunk.metadata.name }} du {{ response.chunk.metadata.types }}
                    - Mail : {{ response.chunk.metadata.mails[0] }}
                    - Adresse : {{ response.chunk.metadata.addresses[0].adresse }} {{ response.chunk.metadata.addresses[0].code_postal }} {{ response.chunk.metadata.addresses[0].commune }}
                    - Urls des sites Internet : {{ response.chunk.metadata.urls | join(",") }}
                    {% endif %}
                {%- endfor %}
                </context trouvé dans la base>

                En t'aidant si besoin du le contexte ci-dessus, réponds à cette question :

                <question>
                {{query}}
                </question>

                Ne précise pas "Selon le contexte fourni".

                Donne le maximum d'information que tu trouves dans le contexte, comme son mail, adresse, urls du département, etc.
                Corrige les erreurs gramaticales et de ponctruation sans donner d'explication sur tes choix.
                Corrige l'erreur de contraction avec l'article défini.
            """)).render(
                search_response=search_response,
                query=query
            )

            result = client.chat.completions.create(
                model="albert-small",
                stream=False,
                temperature=0,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": generate_response_prompt
                    }
                ]
            )

            yield f"{result.choices[0].message.content}"

            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "",
                        "done": True,
                    },
                }
            }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='search annuaire RAG',
        description="Ce script utilise un RAG pour effectuer une recherche dans l'annuaire des administrations d'État",
    )
    parser.add_argument('query')
    args = parser.parse_args()
    pipeline = Pipeline()
    for chunk in pipeline.pipe(
        user_message=args.query,
        model_id=None,
        messages=None,
        body=None
    ):
        if isinstance(chunk, str):
            print(chunk)
        elif 'event' in chunk:
            print(f"info: {chunk['event']['data']['description']}")
        else:
            print(f"Error unknown chunk type: {chunk}")

        print()
