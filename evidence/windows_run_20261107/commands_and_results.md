# 本機 Windows 實跑命令與結果

擷取時間（UTC）：2026-11-07T16:12:42.487252+00:00
OS：Windows-11-10.0.26200-SP0
Python：3.12.14

## first_steps

```
COMMAND: C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe scripts/first_steps.py
```

stdout:
```
SMILES: CCO
Formula: C2H6O; expected MW about 46.07 Da
Molecular weight: 46.069
HBD: 1
Open learning_output/ethanol.png and learning_output/ethanol.mol
```

stderr:
```
(empty)
```

EXIT_CODE: 0

## run_demo

```
COMMAND: C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe scripts/run_demo.py
```

stdout:
```
[
  {
    "input": "molecules.csv",
    "detected": "csv",
    "converted": 5,
    "failed": 0,
    "status": "complete"
  },
  {
    "input": "mixed_invalid.csv",
    "detected": "csv",
    "converted": 1,
    "failed": 2,
    "status": "partial"
  },
  {
    "input": "misnamed.csv",
    "detected": "mol",
    "converted": 1,
    "failed": 0,
    "status": "complete"
  }
]
Open this directory: C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\demo_20261108_001206_328058
```

stderr:
```
(empty)
```

EXIT_CODE: 0

## pytest

```
COMMAND: C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m pytest -q
```

stdout:
```
..............................................                           [100%]
46 passed in 32.49s
```

stderr:
```
(empty)
```

EXIT_CODE: 0
