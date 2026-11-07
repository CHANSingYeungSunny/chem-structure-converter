# 本機 Windows 實跑命令與結果

擷取時間（UTC）：2026-11-07T15:59:56.255152+00:00
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
Open this directory: C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\demo_20261107_235914_724708
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
.F.....................................                                  [100%]
================================== FAILURES ===================================
______________________ test_ui_initial_and_result_views _______________________

    @pytest.mark.skipif(importlib.util.find_spec("streamlit") is None, reason="Optional UI dependency not installed")
    def test_ui_initial_and_result_views():
        from streamlit.testing.v1 import AppTest
    
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        assert not app.exception
        assert app.title[0].value == "ChemBridge 分子格式轉換"
        manifest = {"detection": {"format": "smiles", "reason": "test fixture", "warnings": []},
                    "converted_records": 1, "failed_records": 0}
        data = {"molecules": [{"name": "ethanol", "smiles": "CCO", "properties": {"hbd": 1}}]}
        app.session_state["result"] = (manifest, data, [], [], b"test zip fixture")
>       app.run()

tests\test_optional_ui.py:18: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv\Lib\site-packages\streamlit\testing\v1\app_test.py:396: in run
    return self._tree.run(timeout=timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\streamlit\testing\v1\element_tree.py:1924: in run
    return self._runner._run(widget_states, timeout=timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\streamlit\testing\v1\app_test.py:359: in _run
    self._tree = script_runner.run(
.venv\Lib\site-packages\streamlit\testing\v1\local_script_runner.py:128: in run
    require_widgets_deltas(self, timeout)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

runner = LocalScriptRunner(forward_msg_queue=<streamlit.runtime.forward_msg_queue.ForwardMsgQueue object at 0x000001D942FC7BF0>...mezone: "(\'中國標準時間\', \'中國日光節約時間\')"
}
}, {}, {'client_state': page_script_hash: "41d3a69772854a9de3a1f027c6db8450"
}])
timeout = 3

    def require_widgets_deltas(runner: LocalScriptRunner, timeout: float = 3) -> None:
        """Wait for the given ScriptRunner to emit a completion event. If the timeout
        is reached, the runner will be shutdown and an error will be thrown.
        """
    
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.001)
            if runner.script_stopped():
                return
    
        # If we get here, the runner hasn't yet completed before our
        # timeout. Create an error string for debugging.
        err_string = f"AppTest script run timed out after {timeout}(s)"
    
        # Shutdown the runner before throwing an error, so that the script
        # doesn't hang forever.
        runner.request_stop()
        runner.join()
    
>       raise RuntimeError(err_string)
E       RuntimeError: AppTest script run timed out after 3(s)

.venv\Lib\site-packages\streamlit\testing\v1\local_script_runner.py:176: RuntimeError
---------------------------- Captured stderr call -----------------------------
2026-11-07 23:59:36.129 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-11-07 23:59:37.221 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
=========================== short test summary info ===========================
FAILED tests/test_optional_ui.py::test_ui_initial_and_result_views - RuntimeE...
1 failed, 38 passed in 32.94s
```

stderr:
```
(empty)
```

EXIT_CODE: 1
