import requests
import re
import time
from typing import List, Dict, Any, Optional, Iterator, Union, Generator
from pydantic import BaseModel, Field
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Default model for LLM interpretation
default_model = "meta-llama/Llama-3.1-8B-Instruct"

CLASSIFY_REQUEST_PROMPT = """Tu es un assistant strict qui détermine si une question concerne UNIQUEMENT la recherche de définitions officielles dans la terminologie financière française.

CRITÈRES STRICTS pour répondre "OUI" :
- L'utilisateur demande explicitement une DÉFINITION d'un terme financier/fiscal français
- L'utilisateur utilise des mots comme "définition", "signifie", "qu'est-ce que", "que veut dire"
- Il se peut que l'utilisateur demande une première définition d'un terme, puis demande par la suite "et ce terme [terme] ?", dans ce cas, réponds "OUI"

RÉPONDS "NON" dans TOUS les autres cas, notamment :
- Questions sur des calculs, procédures, ou conseils
- Demandes de services ou d'aide pratique
- Questions générales sans demande de définition spécifique
- Conversations générales ou hors sujet
- Questions sur comment faire quelque chose

RÉPONSE : Un seul mot : "OUI" ou "NON"

Exemples STRICTS :
Utilisateur: "Qu'est-ce que la location meublée ?"
Réponse: OUI

Utilisateur: "Définition de TVA"
Réponse: OUI

Utilisateur: "Que signifie accès hyperphagique ?"
Réponse: OUI

Utilisateur: "Qui est Ulrich Tan ?"
Réponse: NON

Utilisateur: "Quelles sont les étapes pour créer une entreprise ?"
Réponse: NON

Utilisateur: "Bonjour, comment allez-vous ?"
Réponse: NON

Utilisateur: "Quel temps fait-il ?"
Réponse: NON

Basé sur le contexte de la conversation, réponds "OUI" ou "NON" à la question de l'utilisateur.

Contexte de la conversation:
{messages}
"""

EXTRACT_TERMS_PROMPT = """Tu es un assistant spécialisé dans l'extraction de termes à rechercher dans une base de données terminologique française du ministère des finances.

À partir du message de l'utilisateur, identifie les termes clés qui doivent être recherchés dans la terminologie financière française.

Instructions :
- Extrais uniquement les termes pertinents liés aux finances, à la fiscalité, à l'administration
- Ignore les mots de liaison et les expressions de politesse
- Retourne maximum 3 termes
- Si l'utilisateur demande une définition spécifique, extrais ce terme exact
- Réponds uniquement avec les termes séparés par des virgules, sans explication

Exemples :
Utilisateur: "Qu'est-ce que la location meublée ?"
Réponse: location meublée

Utilisateur: "Peux-tu me définir l'accès hyperphagique et la TVA ?"
Réponse: accès hyperphagique, TVA

Utilisateur: "Je cherche des informations sur les impôts et la fiscalité"
Réponse: impôts, fiscalité"""

RESPONSE_PROMPT = """Tu es un assistant spécialisé en terminologie financière française. Tu vas recevoir des définitions officielles trouvées dans la base de données du Ministère des Finances français.

Ton rôle est de présenter ces informations de manière claire et pédagogique en français, en gardant l'exactitude des définitions officielles.

Instructions :
- Utilise un ton professionnel mais accessible
- Conserve la précision des définitions officielles
- Ajoute du contexte utile si nécessaire
- Structure ta réponse clairement
- Cite toujours la source officielle

Voici les définitions trouvées :

{definitions}

Réponds à l'utilisateur de manière claire et complète."""


class Pipeline:
    class Valves(BaseModel):
        # Pipeline configuration
        name: str = Field(default="Terminologie Financière Française (Stéphane Klein)", description="Nom du pipeline")
        openai_api_base_url: str = Field(default="https://albert.api.etalab.gouv.fr/v1", description="URL de base de l'API OpenAI/Albert")
        openai_api_keys: str = Field(
            default="secret",
            description="Clé API OpenAI/Albert",
        )
        terminology_api_endpoint: str = Field(
            default="https://terminologie.finances.gouv.fr/search",
            description="Endpoint de l'API de terminologie française",
        )
        search_size: int = Field(default=5, description="Nombre de résultats de recherche")
        language: str = Field(default="FR", description="Langue de recherche")
        search_mode: str = Field(default="begin", description="Mode de recherche: begin, contain, exact")
        max_results_display: int = Field(default=3, description="Nombre maximum de résultats à afficher")
        llm_model: str = Field(default=default_model, description="Modèle LLM pour l'analyse des requêtes")
        enable_llm_response: bool = Field(default=True, description="Utiliser le LLM pour formatter les réponses")
        FOO: str = Field(default="Hello from FOO!", description="Example valve field")

    def __init__(self):
        self.valves = self.Valves()
        self.name = self.valves.name

    def classify_terminology_request(self, user_message: str, messages: List[dict]) -> bool:
        """Use LLM to determine if the user is asking for terminology definitions"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valves.openai_api_keys}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.valves.llm_model,
                "messages": [
                    {"role": "system", "content": CLASSIFY_REQUEST_PROMPT.format(messages=messages[-10:])},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.0,  # Make it more deterministic
                "max_tokens": 5,  # Reduced since we only need "OUI" or "NON"
                "stream": False,
            }

            response = requests.post(
                f"{self.valves.openai_api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            raw_response = result["choices"][0]["message"]["content"].strip()
            classification = raw_response.upper()

            log.info(f"LLM classification for '{user_message}': raw='{raw_response}' -> parsed='{classification}'")

            # Strict validation - only accept exact matches
            if classification == "OUI":
                return True
            elif classification == "NON":
                return False
            else:
                log.warning(f"Unexpected LLM classification response: '{classification}'. Defaulting to False.")
                return False

        except Exception as e:
            log.error(f"Error classifying request with LLM: {e}")
            # Return False to be conservative - better to not process than to process incorrectly
            return False

    def extract_search_terms_with_llm(self, user_message: str) -> List[str]:
        """Use LLM to extract search terms from user message"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valves.openai_api_keys}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.valves.llm_model,
                "messages": [
                    {"role": "system", "content": EXTRACT_TERMS_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.1,
                "max_tokens": 100,
                "stream": False,
            }

            response = requests.post(
                f"{self.valves.openai_api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            extracted_text = result["choices"][0]["message"]["content"].strip()
            log.info(f"LLM extracted terms: {extracted_text}")

            if extracted_text and extracted_text.lower() not in ["aucun", "none", ""]:
                terms = [term.strip() for term in extracted_text.split(",")]
                return [term for term in terms if term]

            return []

        except Exception as e:
            log.error(f"Error extracting terms with LLM: {e}")
            # Return empty list - let the pipeline handle no terms gracefully
            return []

    def search_terminology(self, query: str) -> Dict[str, Any]:
        """Search the French terminology database for the given query"""
        payload = {
            "offset": 0,
            "size": self.valves.search_size,
            "q": query,
            "lang": self.valves.language,
            "langs": self.valves.language,
            "langDisplay": self.valves.language,
            "mode": self.valves.search_mode,
            "facets": {
                "matchField.fr.facet": {"type": "terms"},
                "kb:type.fr.facet": {"type": "terms"},
                "t3:inGroup:hierarchy.value": {"type": "terms"},
            },
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OpenWebUI-French-Terminology-Pipeline/1.0",
        }

        try:
            response = requests.put(
                self.valves.terminology_api_endpoint,
                headers=headers,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error(f"Error searching terminology: {e}")
            return {"items": [], "error": str(e)}

    def format_raw_definitions(self, all_results: List[Dict[str, Any]]) -> str:
        """Format search results into raw definitions for LLM processing"""
        definitions = []

        for search_term, results in all_results:
            if "error" in results or not results.get("items"):
                continue

            for item in results["items"][: self.valves.max_results_display]:
                fields = item.get("fields", {})

                label = fields.get("rdfs:label", [""])[0] if fields.get("rdfs:label") else "N/A"
                definition = fields.get("skos:definition", [""])[0] if fields.get("skos:definition") else "Aucune définition disponible"
                alt_labels = fields.get("skos:altLabel", [])

                ancestors = fields.get("kb:ancestors", [])
                category = "Non classé"
                if ancestors and len(ancestors[0]) > 0:
                    category = " > ".join([ancestor["label"] for ancestor in ancestors[0][:3]])

                pub_date = fields.get("mef:dateParutionJO", [])

                definition_entry = f"""
Terme: {label}
{f'Aussi appelé: {", ".join(alt_labels)}' if alt_labels else ""}
Catégorie: {category}
Définition: {definition}
{f"Date de parution au JO: {pub_date[0]}" if pub_date else ""}
Source: Terminologie du Ministère des Finances français
---"""
                definitions.append(definition_entry)

        return "\n".join(definitions)

    def generate_llm_response(self, definitions: str, user_message: str) -> str:
        """Generate a natural language response using LLM"""
        try:
            headers = {
                "Authorization": f"Bearer {self.valves.openai_api_keys}",
                "Content-Type": "application/json",
            }

            system_prompt = RESPONSE_PROMPT.format(definitions=definitions)

            payload = {
                "model": self.valves.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.3,
                "max_tokens": 1500,
                "stream": False,
            }

            response = requests.post(
                f"{self.valves.openai_api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            log.error(f"Error generating LLM response: {e}")
            return f"Voici les définitions trouvées :\n\n{definitions}"



    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """
        Main pipeline function - processes requests as a complete model

        This method handles the entire conversation flow for terminology search
        """
        print(f"pipe: {__name__}")
        print(f"user_message: {user_message}")
        print(f"messages: {messages}")

        # Initial greeting if no meaningful message
        if not user_message or len(user_message.strip()) < 3:
            yield "Bonjour ! Je suis votre assistant pour la terminologie financière française. Posez-moi une question sur un terme financier, fiscal ou administratif !"
            return

        # Emit status: analyzing request
        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Analyse de votre demande...",
                    "done": False,
                },
            }
        }

        # Check if this is a terminology request
        is_terminology_request = self.classify_terminology_request(user_message, messages)

        if not is_terminology_request:
            yield """🔍 **Assistant Terminologie Financière Française**

Votre requête ne semble pas concerner la recherche de définitions officielles de la terminologie française du Ministère des Finances.

Pour toute autre question, veuillez sélectionner un autre assistant.
"""
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "Terminé !",
                        "done": True,
                    },
                }
            }
            return

        # Extract search terms
        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Extraction des termes de recherche...",
                    "done": False,
                },
            }
        }

        search_terms = self.extract_search_terms_with_llm(user_message)

        if not search_terms:
            yield "❌ Aucun terme de recherche identifié dans votre message. Veuillez préciser le terme dont vous souhaitez connaître la définition."
            return

        # Search for definitions
        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": f"Recherche de définitions pour: {', '.join(search_terms)}",
                    "done": False,
                },
            }
        }

        all_results = []
        found_any = False

        for term in search_terms:
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": f"Recherche en cours pour '{term}'...",
                        "done": False,
                    },
                }
            }

            results = self.search_terminology(term)
            all_results.append((term, results))

            if results.get("items"):
                found_any = True

            time.sleep(0.5)  # Small delay to show progress

        if not found_any:
            yield """💡 **Aucune définition trouvée**

**Suggestions :**
- Essayez avec des termes plus spécifiques ou utilisez des synonymes
- Cette base de données contient principalement des termes liés aux finances publiques, à la fiscalité et à l'administration française
- Vérifiez l'orthographe du terme recherché"""
            return

        # Format definitions and generate response
        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Formatage de la réponse...",
                    "done": False,
                },
            }
        }

        raw_definitions = self.format_raw_definitions(all_results)

        if self.valves.enable_llm_response and raw_definitions.strip():
            # Generate natural language response with LLM
            response = self.generate_llm_response(raw_definitions, user_message)
        else:
            # Return formatted definitions directly
            response = raw_definitions

        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Terminé !",
                    "done": True,
                },
            }
        }

        yield response

        # Yield citations for all found definitions
        for search_term, results in all_results:
            if "error" in results or not results.get("items"):
                continue

            for item in results["items"][: self.valves.max_results_display]:
                fields = item.get("fields", {})
                uri = item.get("uri", "")

                # Extract key information for citation
                label = fields.get("rdfs:label", [""])[0] if fields.get("rdfs:label") else "N/A"
                definition = fields.get("skos:definition", [""])[0] if fields.get("skos:definition") else "Aucune définition disponible"
                alt_labels = fields.get("skos:altLabel", [])

                # Create document content for citation
                document_content = f"Terme: {label}\n"
                if alt_labels:
                    document_content += f"Aussi appelé: {', '.join(alt_labels)}\n"
                document_content += f"Définition: {definition}"

                # Create source URL using the provided format
                source_url = f"https://terminologie.finances.gouv.fr/index#Concept:uri={uri}"

                # Yield citation event
                yield {
                    "event": {
                        "type": "source",
                        "data": {
                            "document": [document_content],
                            "metadata": [{"source": label}],
                            "source": {
                                "name": f"Terminologie française - {label}",
                                "url": source_url
                            },
                        },
                    }
                }
