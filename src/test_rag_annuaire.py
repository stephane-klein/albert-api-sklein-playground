#!/usr/bin/env python3
import unittest
from inspect import cleandoc

from rag_annuaire import Pipeline

class TestRagAnnuaire(unittest.TestCase):
    def test_search_annuaire_rag(self):
        pipeline = Pipeline()
        chunk = list(
            pipeline.pipe(
                user_message="Qui est François Bayrou",
                model_id=None,
                messages=None,
                body=None
            )
        )
        self.assertEqual(
            chunk[0]["event"]["data"]["description"],
            "Je cherche..."
        )
        self.assertEqual(
            chunk[1]["event"]["data"]["description"],
            "Recherche en cours pour 'Comment est François Bayrou ?'"
        )
        self.assertEqual(
            chunk[2].strip(),
            cleandoc("""
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
            """)
        )

if __name__ == '__main__':
    unittest.main()
