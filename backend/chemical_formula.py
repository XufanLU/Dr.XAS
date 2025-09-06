import json
from dotenv import load_dotenv

from openai import OpenAI
load_dotenv()
client = OpenAI()

def get_chemical_formula(compound_name):
    formula= ""
    response = client.responses.create(
        model="gpt-4o",
        input=f'''What is the chemical formula of {compound_name}? just give me the formula name, no explanation.
        e.g. H2O, CO2, C6H12O6'''
    )
    formula = response.output_text

    print(formula)

    if len(formula) > 20:
        return ""
    return formula


if __name__ == "__main__":  
    print(get_chemical_formula("Nickel molybdate"))