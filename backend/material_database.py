from mp_api.client import MPRester
import os
import dotenv
from dotenv import load_dotenv
from pydash import random

load_dotenv()

# MATERIAL_PROJECT_API_KEY = os.getenv("MATERIAL_PROJECT_API_KEY")
MATERIAL_PROJECT_API_KEY = "9EsNZYQ4fi0fM07c8RoyqryfhZy5yHhu"

mpr = MPRester(MATERIAL_PROJECT_API_KEY)


def search_materials(chemsys):
    docs = mpr.materials.summary.search(
        formula=chemsys,
        fields=["material_id", "formula_pretty", "structure", "theoretical"],
    )

    mpids = [doc.material_id for doc in docs]

    best_match = None
    # select the one with experimental data, if none with experimental data, return random.
    for doc in docs:
        if doc.theoretical == False:
            best_match = doc.material_id
    if best_match is None and len(mpids) > 0:
        best_match = docs[random(0, len(mpids) - 1)].material_id

    return best_match


def get_material_by_id(mp_id):

    entry = mpr.materials.summary.get_data_by_id(mp_id)

    if entry is None:
        return None
        # structure is already a pymatgen object
    cif_str = entry.structure.to(fmt="cif")
    parent_dir = os.path.dirname(os.path.abspath(__file__))

    sub_folder = os.path.join(parent_dir, "material_cif")

    os.makedirs(sub_folder, exist_ok=True)

    with open(os.path.join(sub_folder, f"{mp_id}.cif"), "w") as f:
        f.write(cif_str)

    return f"material_cif/{mp_id}.cif"


if __name__ == "__main__":
    best_match = search_materials("Co")
    print(best_match)
    result = get_material_by_id(best_match)
    print(result)
