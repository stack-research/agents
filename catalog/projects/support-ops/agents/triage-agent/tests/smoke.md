# Smoke Checks

## Case 1: outage

Text: "Production API is down" -> expect `priority=p1`, `category=bug` or `access` depending on context.

## Case 2: billing issue

Text: "I need a refund for duplicate charge" -> expect `category=billing`.

## Case 3: feature request

Text: "Please add SAML support" -> expect `category=feature`, `priority` no higher than `p3`.

## Case 4: how-to question

Text: "How do I configure webhooks?" -> expect `category=how-to`.
