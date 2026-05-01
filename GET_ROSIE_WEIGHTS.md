# Obtaining ROSIE Model Weights

Node 2.1 of this pipeline (`nodes/node2_1_rosie.py`) can run in two modes:

| Mode | Description |
|---|---|
| **DEMO SURROGATE** | Color-feature proxy. Used automatically when no weights file is found. Pipeline testing only — no biological validity. |
| **REAL ROSIE** | Enable Medicine CNN. Predicts 50-channel protein expression from H&E patches. Required for publication-quality results. |

The manuscript results (10,446,317 cells) were produced with real ROSIE on the authors' proprietary KSC mouse H&E images.  
The included TCGA-PAAD sample runs the demo surrogate by default — sufficient to verify the pipeline architecture.

---

## How to Obtain ROSIE Weights

ROSIE is developed by [Enable Medicine](https://www.enablemedicine.com/).  
The model weights (~400 MB `.pth` file) are available on request:

**Step 1 — Register**

Create an account at the ROSIE GitLab repository:  
https://gitlab.com/enable-medicine-public/rosie

**Step 2 — Request access**

Contact Rick (Enable Medicine) to request approval to download the model checkpoint.  
Approval is typically granted for academic research use.

**Step 3 — Download**

Once approved, download the weights file (e.g. `rosie_weights.pth`) from the GitLab release assets or the link provided by Enable Medicine.

**Step 4 — Install the ROSIE package**

```bash
pip install rosie
# or, if installing from the GitLab clone:
pip install git+https://gitlab.com/enable-medicine-public/rosie.git
```

**Step 5 — Point the pipeline to your weights**

Option A — environment variable (recommended):
```bash
ROSIE_WEIGHTS=/path/to/rosie_weights.pth python app.py
```

Option B — place the file in the repo root:
```
LangGraphPrj_V5/
└── rosie_weights.pth   ← place here
```

The pipeline will automatically detect the file and switch to real ROSIE inference.

---

## Verifying the Mode

When the pipeline runs Node 2.1 you will see one of the following in the execution log:

**Real ROSIE (weights found):**
```
ROSIE mode   : REAL MODEL  (rosie_weights.pth)
Processing   : 300 tiles x 50 protein channels
```

**Demo surrogate (no weights):**
```
==============================================================
  ROSIE mode : DEMO SURROGATE (color-feature proxy)
  Results below are for pipeline testing ONLY.
  They are NOT biologically valid.
==============================================================
```

The `rosie_mode` field in the pipeline state also records which mode was used (`"real_rosie"` or `"surrogate_demo"`).

---

## Why are weights not included in this repository?

- The checkpoint file is ~400 MB — too large for GitHub.
- Distribution rights belong to Enable Medicine; redistribution requires their approval.
- The TCGA-PAAD test sample included here is sufficient to verify the full pipeline architecture without the weights.

For questions about weight access contact Enable Medicine directly via the GitLab repository linked above.
