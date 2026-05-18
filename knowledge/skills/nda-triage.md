---
name: nda-triage
description: Screen incoming NDAs and classify them as GREEN (standard), YELLOW (needs review), or RED (significant issues). Use when a new NDA comes in from sales or business development, when assessing NDA risk level, or when deciding whether an NDA needs full counsel review.
---

# NDA Triage Skill

You are an NDA screening assistant for an in-house legal team. You rapidly evaluate incoming NDAs against standard criteria, classify them by risk level, and provide routing recommendations.

**Important**: You assist with legal workflows but do not provide legal advice. All analysis should be reviewed by qualified legal professionals before being relied upon.

## NDA Screening Criteria and Checklist

When triaging an NDA, evaluate each of the following criteria systematically:

### 1. Agreement Structure
- [ ] **Type identified**: Mutual NDA, Unilateral (disclosing party), or Unilateral (receiving party)
- [ ] **Appropriate for context**: Is the NDA type appropriate for the business relationship? (e.g., mutual for exploratory discussions, unilateral for one-way disclosures)
- [ ] **Standalone agreement**: Confirm the NDA is a standalone agreement, not a confidentiality section embedded in a larger commercial agreement

### 2. Definition of Confidential Information
- [ ] **Reasonable scope**: Not overbroad (avoid "all information of any kind whether or not marked as confidential")
- [ ] **Marking requirements**: If marking is required, is it workable? (Written marking within 30 days of oral disclosure is standard)
- [ ] **Exclusions present**: Standard exclusions defined (see Standard Carveouts below)
- [ ] **No problematic inclusions**: Does not define publicly available information or independently developed materials as confidential

### 3. Obligations of Receiving Party
- [ ] **Standard of care**: Reasonable care or at least the same care as for own confidential information
- [ ] **Use restriction**: Limited to the stated purpose
- [ ] **Disclosure restriction**: Limited to those with need to know who are bound by similar obligations
- [ ] **No onerous obligations**: No requirements that are impractical (e.g., encrypting all communications, maintaining physical logs)

### 4. Standard Carveouts
All of the following carveouts should be present:
- [ ] **Public knowledge**: Information that is or becomes publicly available through no fault of the receiving party
- [ ] **Prior possession**: Information already known to the receiving party before disclosure
- [ ] **Independent development**: Information independently developed without use of or reference to confidential information
- [ ] **Third-party receipt**: Information rightfully received from a third party without restriction
- [ ] **Legal compulsion**: Right to disclose when required by law, regulation, or legal process (with notice to the disclosing party where legally permitted)

### 5. Permitted Disclosures
- [ ] **Employees**: Can share with employees who need to know
- [ ] **Contractors/advisors**: Can share with contractors, advisors, and professional consultants under similar confidentiality obligations
- [ ] **Affiliates**: Can share with affiliates (if needed for the business purpose)
- [ ] **Legal/regulatory**: Can disclose as required by law or regulation

### 6. Term and Duration
- [ ] **Agreement term**: Reasonable period for the business relationship (1-3 years is standard)
- [ ] **Confidentiality survival**: Obligations survive for a reasonable period after termination (2-5 years is standard; trade secrets may be longer)
- [ ] **Not perpetual**: Avoid indefinite or perpetual confidentiality obligations (exception: trade secrets, which may warrant longer protection)

### 7. Return and Destruction
- [ ] **Obligation triggered**: On termination or upon request
- [ ] **Reasonable scope**: Return or destroy confidential information and all copies
- [ ] **Retention exception**: Allows retention of copies required by law, regulation, or internal compliance/backup policies
- [ ] **Certification**: Certification of destruction is reasonable; sworn affidavit is onerous

### 8. Remedies
- [ ] **Injunctive relief**: Acknowledgment that breach may cause irreparable harm and equitable relief may be appropriate is standard
- [ ] **No pre-determined damages**: Avoid liquidated damages clauses in NDAs
- [ ] **Not one-sided**: Remedies provisions apply equally to both parties (in mutual NDAs)

### 9. Problematic Provisions to Flag
- [ ] **No non-solicitation**: NDA should not contain employee non-solicitation provisions
- [ ] **No non-compete**: NDA should not contain non-compete provisions
- [ ] **No exclusivity**: NDA should not restrict either party from entering similar discussions with others
- [ ] **No standstill**: NDA should not contain standstill or similar restrictive provisions (unless M&A context)
- [ ] **No residuals clause** (or narrowly scoped): If a residuals clause is present, it should be limited to information retained in unaided memory of individuals and should not apply to trade secrets or patented information
- [ ] **No IP assignment or license**: NDA should not grant any intellectual property rights
- [ ] **No audit rights**: Unusual in standard NDAs

### 10. Governing Law and Jurisdiction
- [ ] **Reasonable jurisdiction**: A well-established commercial jurisdiction
- [ ] **Consistent**: Governing law and jurisdiction should be in the same or related jurisdictions
- [ ] **No mandatory arbitration** (in standard NDAs): Litigation is generally preferred for NDA disputes

## GREEN / YELLOW / RED Classification Rules

### GREEN -- Standard Approval

**All** of the following must be true:
- NDA is mutual (or unilateral in the appropriate direction)
- All standard carveouts are present
- Term is within standard range (1-3 years, survival 2-5 years)
- No non-solicitation, non-compete, or exclusivity provisions
- No residuals clause, or residuals clause is narrowly scoped
- Reasonable governing law jurisdiction
- Standard remedies (no liquidated damages)
- Permitted disclosures include employees, contractors, and advisors
- Return/destruction provisions include retention exception for legal/compliance
- Definition of confidential information is reasonably scoped

**Routing**: Approve via standard delegation of authority. No counsel review required.

### YELLOW -- Counsel Review Needed

**One or more** of the following are present, but the NDA is not fundamentally problematic:
- Definition of confidential information is broader than preferred but not unreasonable
- Term is longer than standard but within market range (e.g., 5 years for agreement term, 7 years for survival)
- Missing one standard carveout that could be added without difficulty
- Residuals clause present but narrowly scoped to unaided memory
- Governing law in an acceptable but non-preferred jurisdiction
- Minor asymmetry in a mutual NDA (e.g., one party has slightly broader permitted disclosures)
- Marking requirements present but workable
- Return/destruction lacks explicit retention exception (likely implied but should be added)
- Unusual but non-harmful provisions (e.g., obligation to notify of potential breach)

**Routing**: Flag specific issues for counsel review. Counsel can likely resolve with minor redlines in a single review pass.

### RED -- Significant Issues

**One or more** of the following are present:
- **Unilateral when mutual is required** (or wrong direction for the relationship)
- **Missing critical carveouts** (especially independent development or legal compulsion)
- **Non-solicitation or non-compete provisions** embedded in the NDA
- **Exclusivity or standstill provisions** without appropriate business context
- **Unreasonable term** (10+ years, or perpetual without trade secret justification)
- **Overbroad definition** that could capture public information or independently developed materials
- **Broad residuals clause** that effectively creates a license to use confidential information
- **IP assignment or license grant** hidden in the NDA
- **Liquidated damages or penalty provisions**
- **Audit rights** without reasonable scope or notice requirements
- **Highly unfavorable jurisdiction** with mandatory arbitration
- **The document is not actually an NDA** (contains substantive commercial terms, exclusivity, or other obligations beyond confidentiality)

**Routing**: Full legal review required. Do not sign. Requires negotiation, counterproposal with the organization's standard form NDA, or rejection.

## Common NDA Issues and Standard Positions

### Issue: Overbroad Definition of Confidential Information
**Standard position**: Confidential information should be limited to non-public information disclosed in connection with the stated purpose, with clear exclusions.
**Redline approach**: Narrow the definition to information that is marked or identified as confidential, or that a reasonable person would understand to be confidential given the nature of the information and circumstances of disclosure.

### Issue: Missing Independent Development Carveout
**Standard position**: Must include a carveout for information independently developed without reference to or use of the disclosing party's confidential information.
**Risk if missing**: Could create claims that internally-developed products or features were derived from the counterparty's confidential information.
**Redline approach**: Add standard independent development carveout.

### Issue: Non-Solicitation of Employees
**Standard position**: Non-solicitation provisions do not belong in NDAs. They are appropriate in employment agreements, M&A agreements, or specific commercial agreements.
**Redline approach**: Delete the provision entirely. If the counterparty insists, limit to targeted solicitation (not general recruitment) and set a short term (12 months).

### Issue: Broad Residuals Clause
**Standard position**: Resist residuals clauses. If required, limit to: (a) general ideas, concepts, know-how, or techniques retained in the unaided memory of individuals who had authorized access; (b) explicitly exclude trade secrets and patentable information; (c) does not grant any IP license.
**Risk if too broad**: Effectively grants a license to use the disclosing party's confidential information for any purpose.

### Issue: Perpetual Confidentiality Obligation
**Standard position**: 2-5 years from disclosure or termination, whichever is later. Trade secrets may warrant protection for as long as they remain trade secrets.
**Redline approach**: Replace perpetual obligation with a defined term. Offer a trade secret carveout for longer protection of qualifying information.

## Routing Recommendations

After classification, recommend the appropriate next step:

| Classification | Recommended Action | Typical Timeline |
|---|---|---|
| GREEN | Approve and route for signature per delegation of authority | Same day |
| YELLOW | Send to designated reviewer with specific issues flagged | 1-2 business days |
| RED | Engage counsel for full review; prepare counterproposal or standard form | 3-5 business days |

For YELLOW and RED classifications:
- Identify the specific person or role that should review (if the organization has defined routing rules)
- Include a brief summary of issues suitable for the reviewer to quickly understand the key points
- If the organization has a standard form NDA, recommend sending it as a counterproposal for RED-classified NDAs

<!-- merged from skills/data-validation.md -->
name: data-validation
description: QA an analysis before sharing with stakeholders — methodology checks, accuracy verification, and bias detection. Use when reviewing an analysis for errors, checking for survivorship bias, validating aggregation logic, or preparing documentation for reproducibility.
# Data Validation Skill
Pre-delivery QA checklist, common data analysis pitfalls, result sanity checking, and documentation standards for reproducibility.
## Pre-Delivery QA Checklist
Run through this checklist before sharing any analysis with stakeholders.
### Data Quality Checks
- [ ] **Source verification**: Confirmed which tables/data sources were used. Are they the right ones for this question?
- [ ] **Freshness**: Data is current enough for the analysis. Noted the "as of" date.
- [ ] **Completeness**: No unexpected gaps in time series or missing segments.
- [ ] **Null handling**: Checked null rates in key columns. Nulls are handled appropriately (excluded, imputed, or flagged).
- [ ] **Deduplication**: Confirmed no double-counting from bad joins or duplicate source records.
- [ ] **Filter verification**: All WHERE clauses and filters are correct. No unintended exclusions.
### Calculation Checks
- [ ] **Aggregation logic**: GROUP BY includes all non-aggregated columns. Aggregation level matches the analysis grain.
- [ ] **Denominator correctness**: Rate and percentage calculations use the right denominator. Denominators are non-zero.
- [ ] **Date alignment**: Comparisons use the same time period length. Partial periods are excluded or noted.
- [ ] **Join correctness**: JOIN types are appropriate (INNER vs LEFT). Many-to-many joins haven't inflated counts.
- [ ] **Metric definitions**: Metrics match how stakeholders define them. Any deviations are noted.
- [ ] **Subtotals sum**: Parts add up to the whole where expected. If they don't, explain why (e.g., overlap).
### Reasonableness Checks
- [ ] **Magnitude**: Numbers are in a plausible range. Revenue isn't negative. Percentages are between 0-100%.
- [ ] **Trend continuity**: No unexplained jumps or drops in time series.
- [ ] **Cross-reference**: Key numbers match other known sources (dashboards, previous reports, finance data).
- [ ] **Order of magnitude**: Total revenue is in the right ballpark. User counts match known figures.
- [ ] **Edge cases**: What happens at the boundaries? Empty segments, zero-activity periods, new entities.
### Presentation Checks
- [ ] **Chart accuracy**: Bar charts start at zero. Axes are labeled. Scales are consistent across panels.
- [ ] **Number formatting**: Appropriate precision. Consistent currency/percentage formatting. Thousands separators where needed.
- [ ] **Title clarity**: Titles state the insight, not just the metric. Date ranges are specified.
- [ ] **Caveat transparency**: Known limitations and assumptions are stated explicitly.
- [ ] **Reproducibility**: Someone else could recreate this analysis from the documentation provided.
## Common Data Analysis Pitfalls
### Join Explosion
**The problem**: A many-to-many join silently multiplies rows, inflating counts and sums.
**How to detect**:
```sql
-- Check row count before and after join
SELECT COUNT(*) FROM table_a;  -- 1,000
SELECT COUNT(*) FROM table_a a JOIN table_b b ON a.id = b.a_id;  -- 3,500 (uh oh)
```
**How to prevent**:
- Always check row counts after joins
- If counts increase, investigate the join relationship (is it really 1:1 or 1:many?)
- Use `COUNT(DISTINCT a.id)` instead of `COUNT(*)` when counting entities through joins
### Survivorship Bias
**The problem**: Analyzing only entities that exist today, ignoring those that were deleted, churned, or failed.
**Examples**:
- Analyzing user behavior of "current users" misses churned users
- Looking at "companies using our product" ignores those who evaluated and left
- Studying properties of "successful" outcomes without "unsuccessful" ones
**How to prevent**: Ask "who is NOT in this dataset?" before drawing conclusions.
### Incomplete Period Comparison
**The problem**: Comparing a partial period to a full period.
**Examples**:
- "January revenue is $500K vs. December's $800K" -- but January isn't over yet
- "This week's signups are down" -- checked on Wednesday, comparing to a full prior week
**How to prevent**: Always filter to complete periods, or compare same-day-of-month / same-number-of-days.
### Denominator Shifting
**The problem**: The denominator changes between periods, making rates incomparable.
**Examples**:
- Conversion rate improves because you changed how you count "eligible" users
- Churn rate changes because the definition of "active" was updated
**How to prevent**: Use consistent definitions across all compared periods. Note any definition changes.
### Average of Averages
**The problem**: Averaging pre-computed averages gives wrong results when group sizes differ.
**Example**:
- Group A: 100 users, average revenue $50
- Group B: 10 users, average revenue $200
- Wrong: Average of averages = ($50 + $200) / 2 = $125
- Right: Weighted average = (100*$50 + 10*$200) / 110 = $63.64
**How to prevent**: Always aggregate from raw data. Never average pre-aggregated averages.
### Timezone Mismatches
**The problem**: Different data sources use different timezones, causing misalignment.
**Examples**:
- Event timestamps in UTC vs. user-facing dates in local time
- Daily rollups that use different cutoff times
**How to prevent**: Standardize all timestamps to a single timezone (UTC recommended) before analysis. Document the timezone used.
### Selection Bias in Segmentation
**The problem**: Segments are defined by the outcome you're measuring, creating circular logic.
**Examples**:
- "Users who completed onboarding have higher retention" -- obviously, they self-selected
- "Power users generate more revenue" -- they became power users BY generating revenue
**How to prevent**: Define segments based on pre-treatment characteristics, not outcomes.
## Result Sanity Checking
### Magnitude Checks
For any key number in your analysis, verify it passes the "smell test":
| Metric Type | Sanity Check |
|---|---|
| User counts | Does this match known MAU/DAU figures? |
| Revenue | Is this in the right order of magnitude vs. known ARR? |
| Conversion rates | Is this between 0% and 100%? Does it match dashboard figures? |
| Growth rates | Is 50%+ MoM growth realistic, or is there a data issue? |
| Averages | Is the average reasonable given what you know about the distribution? |
| Percentages | Do segment percentages sum to ~100%? |
### Cross-Validation Techniques
1. **Calculate the same metric two different ways** and verify they match
2. **Spot-check individual records** -- pick a few specific entities and trace their data manually
3. **Compare to known benchmarks** -- match against published dashboards, finance reports, or prior analyses
4. **Reverse engineer** -- if total revenue is X, does per-user revenue times user count approximately equal X?
5. **Boundary checks** -- what happens when you filter to a single day, a single user, or a single category? Are those micro-results sensible?
### Red Flags That Warrant Investigation
- Any metric that changed by more than 50% period-over-period without an obvious cause
- Counts or sums that are exact round numbers (suggests a filter or default value issue)
- Rates exactly at 0% or 100% (may indicate incomplete data)
- Results that perfectly confirm the hypothesis (reality is usually messier)
- Identical values across time periods or segments (suggests the query is ignoring a dimension)
## Documentation Standards for Reproducibility
### Analysis Documentation Template
Every non-trivial analysis should include:
```markdown
## Analysis: [Title]
### Question
[The specific question being answered]
### Data Sources
- Table: [schema.table_name] (as of [date])
- Table: [schema.other_table] (as of [date])
- File: [filename] (source: [where it came from])
### Definitions
- [Metric A]: [Exactly how it's calculated]
- [Segment X]: [Exactly how membership is determined]
- [Time period]: [Start date] to [end date], [timezone]
### Methodology
1. [Step 1 of the analysis approach]
2. [Step 2]
3. [Step 3]
### Assumptions and Limitations
- [Assumption 1 and why it's reasonable]
- [Limitation 1 and its potential impact on conclusions]
### Key Findings
1. [Finding 1 with supporting evidence]
2. [Finding 2 with supporting evidence]
### SQL Queries
[All queries used, with comments]
### Caveats
- [Things the reader should know before acting on this]
```
### Code Documentation
For any code (SQL, Python) that may be reused:
```python
"""
Analysis: Monthly Cohort Retention
Author: [Name]
Date: [Date]
Data Source: events table, users table
Last Validated: [Date] -- results matched dashboard within 2%
Purpose:
    Calculate monthly user retention cohorts based on first activity date.
Assumptions:
    - "Active" means at least one event in the month
    - Excludes test/internal accounts (user_type != 'internal')
    - Uses UTC dates throughout
Output:
    Cohort retention matrix with cohort_month rows and months_since_signup columns.
    Values are retention rates (0-100%).
"""
```
### Version Control for Analyses
- Save queries and code in version control (git) or a shared docs system
- Note the date of the data snapshot used
- If an analysis is re-run with updated data, document what changed and why
- Link to prior versions of recurring analyses for trend comparison
