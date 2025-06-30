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
                        Tu te nommes "Assistant Administrations", un assistant développé par l'Etalab.

                        Tu es connecté à la base de données véctorielle "Référentiel de l'organisation administrative de l'Etat"
                        qui comprend toutes les institutions régies par la Constitution de la Ve République et les administrations
                        qui en dépendent, soit environ 6000 organismes.  
                        Le périmètre couvre les services centraux de l’Etat, jusqu’au niveau des bureaux.

                        Ce que tu sais faire : tu sais répondre aux questions en lien avec cette base de données.
                    """)
                },
                {
                    "role": "user",
                    "content": cleandoc(f"""
                        # Optimisation de requête pour recherche vectorielle

                        Votre rôle : Vous êtes un assistant spécialisé dans l'optimisation des requêtes de recherche pour une base de données vectorielle sur l'organisation administrative française.

                        ## Votre tâche

                        Reformulez la question suivante de l'utilisateur pour la rendre plus efficace lors de la recherche vectorielle dans le "Référentiel de l'organisation administrative de l'État".

                        Question de l'utilisateur : [{query}]

                        Retourne uniquement la reformulation. Rien de plus.
                        Ne précise pas que la recherche doit se faire dans « Référentiel de l'organisation administrative de l'État ».

                        Exemples :

                        - Question : « Qui est François Bayrou ? »
                          Réponse : « Quelle est l'adresse de François Bayrou »
                        - Quesiton : « Qui est l'actuel directeur de la DINUM ? »
                          Réponse : « Quelle est l'adresse du directeur DINUM » 
                    """)
                }
            ]
        ).choices[0].message.content

        if query_reformulation_result == "no_search":
            result = client.chat.completions.create(
                model="albert-small",
                stream=False,
                temperature=0,
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": cleandoc(f"""
                            L'utilisateur a posé la question suivante : « {query} »
                            
                            Cette question n'a pas de lien avec l'annuaire de l'administration de l'État.

                            Réponds directement sans formules de politesse ni salutations.

                            Réponds à l'utilisateur en mois de 80 mots et invite-le à se tourner vers un autre assistant ou un modèle de langage généraliste comme par exemple "Tâches simples" ou "Tâches complexes".

                            N'essaie pas de répondre à la question de l'utilisateur et ne le commente pas.

                            Structure ta réponse avec des paragraphes courts et aérés.
                        """)
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
