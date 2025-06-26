# Albert API Stéphane Klein playground

Ce repository me sert de "[playground](https://notes.sklein.xyz/Playground/)" pour expériementer [en public](https://notes.sklein.xyz/Learn%20In%20Public/)
l'utilisation de [`albert-api`](https://github.com/etalab-ia/albert-api).

L'accès à l'instance <https://albert.api.etalab.gouv.fr> est limité.
Vous pouvez effectuer une demande d'accès à cette adresse : <https://alliance.numerique.gouv.fr/albert/contacter-albert-api/>.

## Conventions

La documentation (fichiers `*.md`) est rédigée en français, tandis que le code source des scripts (*bash* ou *python*), les commits messages et les noms de fichiers utilisent l'anglais.

## Configuration du workspace

Ce projet est compatible sour Linux et MacOS. Je ne l'ai personnellement testé uniquement sous Linux [Fedora](https://notes.sklein.xyz/Fedora/).

Prérequis:

- Installer Mise: https://mise.jdx.dev/installing-mise.html

```sh
$ mise install
$ pip install -r requirements.txt
```

Configuration des tokens d'accès à <https://albert.api.etalab.gouv.fr>

```
$ cp .secret.skel .secret
```

Éditer `.secret`.

```
$ source .envrc
```

Tester le bon fonctionnement de votre token :

```
$ ./scripts/check-openapi-api-connection.sh
[
  {
    "id": "albert-small",
    "created": 1749826951,
    "object": "model",
    "owned_by": "Albert API",
    "max_context_length": 64000,
    "type": "text-generation",
    "aliases": [
      "meta-llama/Llama-3.1-8B-Instruct"
    ],
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "embeddings-small",
    "created": 1749826951,
    "object": "model",
    "owned_by": "Albert API",
    "max_context_length": 8192,
    "type": "text-embeddings-inference",
    "aliases": [
      "BAAI/bge-m3"
    ],
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  }
]
```

## Exploration des collections

Utilisation du endpoint [`Get Collections`](https://albert.api.etalab.gouv.fr/documentation#tag/Collections/operation/get_collections_v1_collections_get).

```sh
$ ./scripts/get-collections.sh
{
  "object": "list",
  "data": [
    {
      "object": "collection",
      "id": 242,
      "name": "plus.transformation.gouv.fr", b
      "owner": "etalab@modernisation.gouv.fr",
      "description": null,
      "visibility": "private",
      "created_at": 1745498507,
      "updated_at": 1745498507,
      "documents": 80977
    },
    ...
```

Détail d'une collection par son `id`:

```sh
$ ./scripts/get-collection.sh 783
{
  "object": "collection",
  "id": 783,
  "name": "annuaire-administrations-etat",
  "owner": "faheem.beg@data.gouv.fr",
  "description": "Annuaire des administrations d'état",
  "visibility": "public",
  "created_at": 1748423004,
  "updated_at": 1748423004,
  "documents": 7864
}
```

## J'effectue des recherches dans la collection « Annuaire des administrations d'état »

Utilisation du endpoint [`/v1/search`](https://albert.api.etalab.gouv.fr/documentation#tag/Search)

```
$ ./scripts/search-annuaire.py "Qui est François Bayrou" | jq
{
  "object": "list",
  "data": [
    {
      "method": "semantic",
      "score": 0.56030065,
      "chunk": {
        "object": "chunk",
        "id": 1,
        "metadata": {
          "chunk_id": "a515667c-6dc0-4544-a1a8-2cf13d7da23b",
          "types": "Administration centrale (ou Ministère)",
          "name": "Premier ministre",
          "mission_description": "",
          "addresses": [
            {
              "pays": "France",
              "adresse": "Hôtel Matignon  57 rue de Varenne",
              "commune": "Paris",
              "latitude": "48.85428",
              "longitude": "2.320638",
              "code_postal": "75007"
            },
            {
              "pays": "France",
              "adresse": "57 rue de Varenne",
              "commune": "Paris SP 07",
              "latitude": "",
              "longitude": "",
              "code_postal": "75700"
            }
          ],
          "phone_numbers": [
            "01 42 75 80 00"
          ],
          "mails": [],
          "urls": [
            "https://www.info.gouv.fr"
          ],
          "social_medias": [],
          "mobile_applications": [],
          "opening_hours": "{}",
          "contact_forms": [
            "https://www.info.gouv.fr/contact/premier-ministre"
          ],
          "additional_information": "",
          "modification_date": "03/02/2025",
          "siret": "11000101300017",
          "siren": "110001013",
          "people_in_charge": [
            {
              "fonction": "Premier ministre",
              "personne": {
                "nom": "BAYROU",
                "grade": "",
                "prenom": "François",
                "civilite": "M.",
                "texte_reference": [
                  {
                    "valeur": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000050774288",
                    "libelle": "JORF n°0295 du 14 décembre 2024"
                  }
                ],
                "adresse_courriel": []
              },
              "telephone": ""
            }
          ],
...
```

## Utilisation d'un RAG pour une recherche dans « Annuaire des administrations d'état »

```sh
$ ./src/rag_annuaire.py "Qui est François Bayrou"
Je cherche...

Recherche en cours pour 'Comment est François Bayrou ?'

François Bayrou est un homme politique français qui occupe plusieurs postes importants. Voici les informations disponibles sur lui :

- Premier ministre : il est le Premier ministre de l'Administration centrale, également connu sous le nom de Ministère. Ses coordonnées sont :
  - Adresse : Hôtel Matignon, 57 rue de Varenne, 75007 Paris
  - Urls des sites Internet : https://www.info.gouv.fr

- Conseil stratégique de la recherche : il est le Président de ce conseil stratégique. Ses coordonnées sont :
  - Adresse : 1 rue Descartes, 75005 Paris
  - Urls des sites Internet : https://www.enseignementsup-recherche.gouv.fr

- Haut Conseil à la vie associative : il est également le Président de ce Haut Conseil. Ses coordonnées sont :
  - Adresse : 95 avenue de France, 75013 Paris
  - Urls des sites Internet : https://www.associations.gouv.fr/
  - Mail : hcva@jeunesse-sports.gouv.fr

Il est important de noter que les coordonnées du mail pour le poste de Premier ministre ne sont pas disponibles.
```

Exécution du test unitaire de cette commande :

```sh
$ ./src/test_rag_annuaire.py
.
------------------------------
Ran 1 test in 4.432s

OK
