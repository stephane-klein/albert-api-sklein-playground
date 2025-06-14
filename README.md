# Albert API Stéphane Klein playground

Ce repository me sert de "[playground](https://notes.sklein.xyz/Playground/)" pour expériementer [en public](https://notes.sklein.xyz/Learn%20In%20Public/)
l'utilisation de [`albert-api`](https://github.com/etalab-ia/albert-api).

L'accès à l'instance <https://albert.api.etalab.gouv.fr> est limité.
Vous pouvez effectuer une demande d'accès à cette adresse : <https://alliance.numerique.gouv.fr/albert/contacter-albert-api/>.

## Conventions

La documentation (fichiers `*.md`) est rédigée en français, tandis que le code source, les scripts et les noms de fichiers utilisent l'anglais.

## Configuration du workspace

Ce projet est compatible sour Linux et MacOS. Je ne l'ai personnellement testé uniquement sous Linux [Fedora](https://notes.sklein.xyz/Fedora/).

Prérequis:

- Installer Mise: https://mise.jdx.dev/installing-mise.html

```sh
$ mise install
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
