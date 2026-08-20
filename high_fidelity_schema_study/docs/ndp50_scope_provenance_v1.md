# NDP-50 scope and request-provenance record v1

Date: 2026-07-27  
Status: pre-registration provenance boundary  
Scope: origin of the NDP study direction versus investigator-defined protocol
choices

## 1. Purpose

This record prevents an internal collaborator request from being overstated as
scientific evidence or as authorization for every later protocol choice. It
separates:

1. what the archived project correspondence directly establishes;
2. what the research team inferred as an operational task; and
3. what the investigators subsequently defined and must defend through the
   preregistered study design.

The underlying conversation is access-controlled project correspondence. This
public record contains a minimal audit summary, not a transcript, and does not
publish private message locators, email addresses, or verbatim private
conversation.

## 2. Correspondence audit

The complete accessible history of the relevant three-person Slack group
conversation was inspected on 2026-07-27. The account used by Swathi in that
conversation was distinguished from a second same-name workspace account by
channel membership. The audit found:

| Date | Directly supported fact | Evidentiary limit |
| --- | --- | --- |
| 2026-05-06 | Swathi supplied the National Data Platform registration/documentation link and identified it as NDP. | This establishes the target platform, not a sample size, split, estimand, or authorization to open test outcomes. |
| 2026-07-24 | William asked Swathi for the list of datasets to run. | The question is not a completed dataset list or approval. |
| 2026-07-24 to 2026-07-26 | Swathi referred back to the earlier data repository; William subsequently reported an NDP-oriented plan update. | These records support the NDP work direction but do not contain a direct written instruction from Swathi specifying exactly 50 datasets. |
| 2026-07-24 | Swathi supplied the Korini--Bizer CPA paper and described it and related work as relevant. | Relevance is not claim entailment, empirical validation, or approval of the resulting protocol. |
| 2026-07-26 | Swathi supplied `Feedback_Phase1.pptx` and invited changes judged appropriate. | The file is feedback input; incorporation and later collaborator sign-off remain separate events. |

No accessible message in the audited conversation contained an explicit
Swathi-authored statement equivalent to “run exactly 50 NDP datasets.” Absence
from this conversation does not prove that the number was never discussed in a
meeting or another medium. It means only that this repository must not cite the
audited Slack conversation as direct evidence for that exact number.

## 3. Provenance classification

The scope is therefore classified as follows:

| Element | Provenance class | Current authority |
| --- | --- | --- |
| Use NDP as the external dataset source | collaborator-originated project direction | archived internal correspondence plus the supplied public NDP locator |
| Evaluate the schema-extraction project on NDP data | operational research interpretation accepted by the study operator | current protocol and implementation artifacts |
| Select exactly 50 records | investigator-defined protocol choice | deterministic selection artifact and preregistration draft |
| Use a 15/10/25 development/validation/test split | investigator-defined design choice | deterministic selection artifact, protocol, and analysis plan |
| Use quota sampling, organization caps, paired dataset-level estimands, two co-primary contrasts, and Holm correction | investigator-defined methodological choices | machine-readable design, statistical analysis plan, and preregistration draft |
| Treat the current feedback as approved | unsupported until a valid collaborator sign-off replays | feedback sign-off schema v2 and publication gate |

The “50” label is a compact study name, not evidence that the collaborator
dictated the sample size and not evidence that 50 is statistically sufficient.
Sufficiency remains conditional on the registered opportunity counts,
calibration-derived planning inputs, power/assurance freeze, missingness, and
the underpowered stopping rule.

## 4. Permitted and prohibited wording

Permitted:

- “The NDP external-validation direction arose from collaborator discussion;
  the investigators operationalized it as the preregistered NDP-50 design.”
- “The selected study sample contains 50 records under the frozen deterministic
  selection policy.”
- “Swathi supplied NDP and literature inputs and is reviewing the resulting
  protocol as a project collaborator.”

Prohibited:

- “Swathi instructed us in Slack to run exactly 50 datasets.”
- “The collaborator selected or statistically justified the 15/10/25 split.”
- “The NDP-50 design is approved” before the exact v2 feedback sign-off and
  applicable governance artifacts replay.
- Any suggestion that private correspondence is independent scientific
  validation.

## 5. Change control

If a direct source for the exact sample-size request is later recovered, it
must be added through a dated new version or deviation record. The current
record must not be silently rewritten. A new source may clarify request
provenance, but it cannot retroactively establish preregistration, power,
independence, governance approval, or empirical validity.
