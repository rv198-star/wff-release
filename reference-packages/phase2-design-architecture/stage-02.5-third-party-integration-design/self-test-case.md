# Stage-02.5 Self-Test Case — external identity provider plus LLM provider

## 1. Test Goal
- verify that one case with two material external dependencies produces an explicit active Stage-02.5 package

## 2. Input Brief
> The system depends on WorkOS/Auth0 for workforce identity and an LLM API for recommendation generation. Internal services should not hardcode provider SDK semantics.

## 3. Expected Minimum Output Shape
- activation_decision = `active`
- dependency manifest with 2 rows
- 2 IDRs
- adapter specifications for both dependencies
- test strategy covering local/CI/staging/production
- non-empty risk register

