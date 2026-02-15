# Smoke Checks

## Case 1: repository scan

Input `{"target_path":"."}` -> expect JSON with summary, risk_score, findings.

## Case 2: invalid path

Input `{"target_path":"./missing-path"}` -> expect validation error.

## Case 3: ASI mapping

Each finding should include an `asi` key such as `ASI01` or `ASI02`.

## Case 4: score bounds

`risk_score` must remain in range `0..100`.
