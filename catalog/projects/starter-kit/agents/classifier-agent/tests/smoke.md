# Smoke Checks

## Case 1: billing

Text: "I was billed twice" -> expect `billing`.

## Case 2: bug report

Text: "The app crashes when I upload a CSV" -> expect `bug-report`.

## Case 3: feature request

Text: "Please add dark mode" -> expect `feature-request`.

## Case 4: unclear

Text: "Hi there" -> expect `unknown` (or lowest-confidence closest label if `unknown` is absent).
