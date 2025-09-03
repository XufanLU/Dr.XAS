from mp_api.client import MPRester
import os
import dotenv
from dotenv import load_dotenv
from pydash import random

load_dotenv()

MATERIAL_PROJECT_API_KEY = os.getenv("MATERIAL_PROJECT_API_KEY")
mpr = MPRester(MATERIAL_PROJECT_API_KEY)


def search_materials(chemsys):
        docs = mpr.materials.summary.search(
            chemsys=chemsys
        )
        mpids = [doc.material_id for doc in docs]

        best_match = None
        # select the one with experimental data, if none with experimental data, return random. 
        for doc in docs:
             if doc.theoretical == False:
                 best_match = doc.material_id
        if best_match is None and len(mpids) > 0:
            best_match = docs[random(0, len(mpids)-1)].material_id

        return best_match


if __name__ == "__main__":
    best_match= search_materials('Cu')
    print(best_match)
