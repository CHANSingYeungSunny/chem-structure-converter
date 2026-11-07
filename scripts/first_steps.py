"""Run from project root: python scripts/first_steps.py"""
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, Draw, Lipinski

mol = Chem.MolFromSmiles("CCO")  # Step 1: SMILES -> molecular graph
assert mol is not None          # Step 2: confirm parsing succeeded
print("SMILES:", Chem.MolToSmiles(mol))
print("Formula: C2H6O; expected MW about 46.07 Da")
print("Molecular weight:", Descriptors.MolWt(mol))  # Step 3: compute
print("HBD:", Lipinski.NumHDonors(mol))
target = Path("learning_output")
target.mkdir(exist_ok=True)
Draw.MolToImage(mol).save(target / "ethanol.png")  # Step 4: draw
Chem.MolToMolFile(mol, str(target / "ethanol.mol"))  # Step 5: export
print("Open learning_output/ethanol.png and learning_output/ethanol.mol")
