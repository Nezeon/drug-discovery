# /chem-pipeline — Chemistry Pipeline Skill

> Auto-invoked when working with RDKit, DeepChem, SMILES strings,
> molecular generation, scaffolds, or ADMET prediction.

---

## The Most Important Rule in This File

**Gemini does NOT generate molecules. RDKit and DeepChem do.**

Gemini is used for language tasks: extracting protein names from text, writing narratives, interpreting results.
RDKit is used for chemistry: SMILES manipulation, scaffold extraction, filtering, visualisation.
DeepChem is used for ML chemistry: ADMET prediction, generative models.

Never ask Gemini to produce a SMILES string. It will confidently produce an invalid molecule.

---

## RDKit Patterns

### SMILES Validation (always do this first)
```python
from rdkit import Chem

def validate_smiles(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None

# In agent code — filter invalid before processing
valid_compounds = [c for c in compounds if validate_smiles(c["smiles"])]
```

### Lipinski's Rule of Five
```python
from rdkit.Chem import Descriptors

def passes_lipinski(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
```

### Murcko Scaffold Extraction
```python
from rdkit.Chem.Scaffolds import MurckoScaffold

def get_scaffold(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    return Chem.MolToSmiles(scaffold)
```

### Tanimoto Novelty Check
```python
from rdkit.Chem import AllChem
from rdkit import DataStructs

def compute_max_tanimoto(query_smiles: str, reference_smiles_list: list[str]) -> float:
    """Returns highest Tanimoto similarity between query and any reference compound."""
    query_mol = Chem.MolFromSmiles(query_smiles)
    if query_mol is None:
        return 1.0  # invalid = treat as non-novel
    query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, radius=2, nBits=2048)
    max_sim = 0.0
    for ref_smiles in reference_smiles_list:
        ref_mol = Chem.MolFromSmiles(ref_smiles)
        if ref_mol is None:
            continue
        ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, radius=2, nBits=2048)
        sim = DataStructs.TanimotoSimilarity(query_fp, ref_fp)
        max_sim = max(max_sim, sim)
    return max_sim

# Novelty threshold from config
NOVELTY_THRESHOLD = 0.85
is_novel = compute_max_tanimoto(new_smiles, known_smiles_list) < NOVELTY_THRESHOLD
```

### Synthetic Accessibility Score
```python
# SA Score is in rdkit.Contrib — not the main library
from rdkit.Contrib.SA_Score import sascorer

def get_sa_score(smiles: str) -> float | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return sascorer.calculateScore(mol)

# SA Score scale: 1 (easy to synthesise) → 10 (very hard)
# Threshold: drop if SA > 6.0, warn if 4.0–6.0
```

### SMILES → SVG for Frontend
```python
from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D
import base64

def smiles_to_svg(smiles: str, width: int = 300, height: int = 200) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()
```

### Butina Clustering (scaffold diversity)
```python
from rdkit.ML.Cluster import Butina
from rdkit.Chem import AllChem

def cluster_scaffolds(smiles_list: list[str], cutoff: float = 0.4) -> list[list[int]]:
    mols = [Chem.MolFromSmiles(s) for s in smiles_list]
    fps = [AllChem.GetMorganFingerprintAsBitVect(m, 2) for m in mols if m]
    dists = []
    nfps = len(fps)
    for i in range(1, nfps):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend([1 - x for x in sims])
    clusters = Butina.ClusterData(dists, nfps, cutoff, isDistData=True)
    return clusters
```

---

## DeepChem Patterns

### Loading TDC ADMET Models
```python
import deepchem as dc
from tdc.single_pred import ADMET

# Always use pretrained models — do not train from scratch in hackathon
# Models are downloaded on first run — run preload_models.py first

def load_admet_model(task: str):
    """
    Available TDC tasks for ADMET:
    - 'Caco2_Wang' — intestinal absorption
    - 'AMES' — mutagenicity
    - 'hERG' — cardiotoxicity
    - 'BBB_Martini' — blood-brain barrier
    - 'HIA_Hou' — human intestinal absorption
    - 'Pgp_Broccatelli' — P-glycoprotein inhibition
    - 'Bioavailability_Ma' — oral bioavailability
    - 'Lipophilicity_AstraZeneca' — logD
    - 'CYP2D6_Veith' — CYP inhibition
    - 'CYP3A4_Veith' — CYP inhibition
    - 'DILI' — drug-induced liver injury (hepatotoxicity)
    """
    data = ADMET(name=task)
    return data

# Prediction pattern
def predict_admet(smiles: str, task: str) -> float:
    # DeepChem TDC inference — returns float 0-1 for classification tasks
    # Always call .item() on numpy scalar before JSON serialisation
    pass
```

### BRICS Fragmentation
```python
from rdkit.Chem import BRICS

def brics_fragments(smiles: str) -> list[str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    frags = BRICS.BRICSDecompose(mol)
    # Clean fragment SMILES — remove attachment markers
    clean = []
    for frag in frags:
        frag = frag.replace('[*]', '').replace('(*)', '')
        mol_frag = Chem.MolFromSmiles(frag)
        if mol_frag:
            clean.append(Chem.MolToSmiles(mol_frag))
    return clean
```

---

## Critical Chemistry Facts for This Project

- **Never trust Gemini with SMILES** — always generate via RDKit/DeepChem, validate before use
- **SA Score > 8 = unsynthesisable** — drop immediately. SA > 6 = warn.
- **hERG prediction** — if predicted IC50 < 1µM, it's a hard FAIL. Do not pass to scorer.
- **Ames positive** — mutagenic. Hard FAIL. Do not pass to scorer.
- **TPSA > 140** — poor oral bioavailability. Flag WARN on absorption.
- **Rotatable bonds > 10** — poor oral bioavailability. Flag WARN.
- **LogP > 5** — membrane permeability issues. Flag WARN.
- **MW > 500** — poor oral absorption (Lipinski violation). Flag WARN.
- **AlphaFold pLDDT < 70** — binding site may be disordered. Note in output, don't discard.
