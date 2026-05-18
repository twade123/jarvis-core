---
name: draft-outreach
description: Research a prospect then draft personalized outreach. Uses web research by default, supercharged with enrichment and CRM. Trigger with "draft outreach to [person/company]", "write cold email to [prospect]", "reach out to [name]".
---

# Draft Outreach

Research first, then draft. This skill never sends generic outreach - it always researches the prospect first to personalize the message. Works standalone with web search, supercharged when you connect your tools.

## Connectors (Optional)

| Connector | What It Adds |
|-----------|--------------|
| **Enrichment** | Verified email, phone, background details |
| **CRM** | Prior relationship context, existing contacts |
| **Email** | Create draft directly in your inbox |

> **No connectors?** Web research works great. I'll output the email text for you to copy.

---

## How It Works

```
+------------------------------------------------------------------+
|                      DRAFT OUTREACH                               |
|                                                                   |
|  Step 1: RESEARCH (always happens first)                         |
|  - Web search (default)                                           |
|  - + Enrichment (if enrichment tools connected)                  |
|  - + CRM (if CRM connected)                                      |
|                                                                   |
|  Step 2: DRAFT (based on research)                               |
|  - Personalized opening (from research)                          |
|  - Relevant hook (their priorities)                              |
|  - Clear CTA                                                      |
|                                                                   |
|  Step 3: DELIVER (based on connectors)                           |
|  - Email draft (if email connected)                              |
|  - Copy for LinkedIn (always)                                    |
|  - Output to user (always)                                        |
+------------------------------------------------------------------+
```

---

## Output Format

```markdown
# Outreach Draft: [Person] @ [Company]
**Generated:** [Date] | **Research Sources:** [Web, Enrichment, CRM]

---

## Research Summary

**Target:** [Name], [Title] at [Company]
**Hook:** [Why reaching out now - the personalized angle]
**Goal:** [What you want from this outreach]

---

## Email Draft

**To:** [email if known, or "find email" note]
**Subject:** [Personalized subject line]

---

[Email body]

---

**Subject Line Alternatives:**
1. [Option 2]
2. [Option 3]

---

## LinkedIn Message (if no email)

**Connection Request (< 300 chars):**
[Short, no-pitch connection request]

**Follow-up Message (after connected):**
[Value-first message]

---

## Why This Approach

| Element | Based On |
|---------|----------|
| Opening | [Research finding that makes it personal] |
| Hook | [Their priority/pain point] |
| Proof | [Relevant customer story] |
| CTA | [Low-friction ask] |

---

## Email Draft Status

[Draft created - check ~~email]
[Email not connected - copy email above]
[No email found - use LinkedIn approach]

---

## Follow-up Sequence (Optional)

**Day 3 - Follow-up 1:**
[Short, new angle]

**Day 7 - Follow-up 2:**
[Different value prop]

**Day 14 - Break-up:**
[Final attempt]
```

---

## Execution Flow

### Step 1: Parse Request

```
Input patterns:
- "draft outreach to John Smith at Acme" → Person + company
- "write cold email to Acme's CTO" → Role + company
- "reach out to sarah@acme.com" → Email provided
- "LinkedIn message to [LinkedIn URL]" → Profile provided
```

### Step 2: Research First (Always)

**Use research-prospect skill internally:**
```
1. Web search for company + person
2. If Enrichment connected: Get verified contact info, background
3. If CRM connected: Check for prior relationship
```

**Must find before drafting:**
- Who they are (title, background)
- What the company does
- Recent news or trigger
- Personalization hook

### Step 3: Identify Hook

```
Priority order for hooks:
1. Trigger event (funding, hiring, news) → Most timely
2. Mutual connection → Social proof
3. Their content (post, article, talk) → Shows you did research
4. Company initiative → Relevant to their priorities
5. Role-based pain point → Least personal but still relevant
```

### Step 4: Draft Message

**Email Structure (AIDA):**
```
SUBJECT: [Personalized, <50 chars, no spam words]

[Opening: Personal hook - shows you researched them]

[Interest: Their problem/opportunity in 1-2 sentences]

[Desire: Brief proof point - similar company result]

[Action: Clear, low-friction CTA]

[Signature]
```

**LinkedIn Connection Request (<300 chars):**
```
Hi [Name], [Mutual connection/shared interest/genuine compliment].
Would love to connect. [No pitch]
```

**LinkedIn Follow-up Message:**
```
Thanks for connecting! [Value-first: insight, article, observation]

[Soft transition to why you reached out]

[Question, not pitch]
```

### Step 5: Create Email Draft

```
If email connector available:
1. Create draft with to, subject, body
2. Return draft link
3. Note: "Draft created - review and send"

If not available:
1. Output email text
2. Note: "Copy to your email client"
```

---

## Capability by Connector

| Capability | Web Only | + Enrichment | + CRM | + Email |
|------------|----------|--------------|-------|---------|
| Personalized opening | Basic | Deep | With history | Same |
| Verified email | No | Yes | Yes | Yes |
| Background details | Public only | Full | Full | Full |
| Prior relationship | No | No | Yes | Yes |
| Auto-create draft | No | No | No | Yes |

---

## Message Templates by Scenario

### Cold Outreach (No Prior Relationship)

```
Subject: [Their initiative] + [your angle]

Hi [Name],

[Personal hook based on research - news, content, mutual connection].

[1 sentence on their likely challenge based on role/company].

[Brief proof: "We helped [Similar Company] achieve [Result]".]

Worth a 15-min call to see if relevant?

[Signature]
```

### Warm Outreach (Have Met / Mutual Connection)

```
Subject: Following up from [context]

Hi [Name],

[Reference to how you know them / who connected you].

[Why reaching out now - their trigger].

[Specific value you can offer].

[CTA]
```

### Re-Engagement (Went Dark)

```
Subject: [Short, curiosity-driven]

Hi [Name],

[Acknowledge time passed without being guilt-trippy].

[New reason to reconnect - their news or your news].

[Simple question to re-open dialogue].

[Signature]
```

### Post-Event Follow-up

```
Subject: Great meeting you at [Event]

Hi [Name],

[Specific memory from conversation].

[Value-add: article, intro, resource related to what you discussed].

[Soft CTA for next conversation].
```

---

## Email Style Guidelines

1. **Be concise but informative** — Get to the point quickly. Busy people skim.
2. **No markdown formatting** — Never use asterisks, bold (**text**), or other markdown. Write plain text that looks natural in any email client.
3. **Short paragraphs** — 2-3 sentences max per paragraph. White space is your friend.
4. **Simple lists** — If listing items, use plain dashes. No fancy formatting.

**Good:**
```
Here's what I can share:
- Case study from a similar company
- 15-min intro call this week
- Quick demo if helpful
```

**Bad:**
```
**What I Can Offer:**
- **Case study** from a similar company
- **Intro call** this week
```

---

## What NOT to Do

**Generic openers:**
- "I hope this email finds you well"
- "I'm reaching out because..."
- "I wanted to introduce myself"

**Feature dumps:**
- Long paragraphs about your product
- Multiple value props at once
- No clear CTA

**Fake personalization:**
- "I noticed you work at [Company]" (obviously)
- "Congrats on your role" (without context)

**Markdown in emails:**
- Using **bold** or *italic* asterisks
- Headers or formatted lists that won't render

**Instead:**
- Lead with something specific you learned
- One clear value prop
- One clear ask
- Plain text formatting only

---

## Channel Selection

```
IF verified email available:
  → Email preferred (higher response rate)
  → Also provide LinkedIn backup

IF no email:
  → LinkedIn connection request
  → Follow-up message template for after connection

IF warm intro possible:
  → Suggest mutual connection outreach first
```

---

## Company Configuration [CUSTOMIZE]

```markdown
## Outreach Settings

- My name: [Your Name]
- My title: [Your Title]
- My company: [Company Name]
- Value prop: [One sentence - what you help with]

## Signature
[Your preferred email signature]

## Proof Points
- [Customer 1]: [Result]
- [Customer 2]: [Result]
- [Customer 3]: [Result]

## CTA Options
- Default: "Worth a 15-min call?"
- Softer: "Open to learning more?"
- Specific: "Can I send over a quick demo?"

## Tone
- [Professional / Casual / Direct]
- Industry-specific language: [Yes/No]
```

---

## Example

**Input:** "draft outreach to the Head of Engineering at Notion"

**Research finds:**
- Name: David Tibbitts
- Recent news: Notion launched AI features
- Hiring: 5 ML engineer roles open
- Background: Ex-Facebook, Stanford CS

**Output:**

```markdown
# Outreach Draft: David Tibbitts @ Notion

## Research Summary
**Target:** David Tibbitts, Head of Engineering at Notion
**Hook:** They're scaling AI features and hiring ML talent
**Goal:** Intro call about AI infrastructure

---

## Email Draft

**To:** david@notion.so
**Subject:** Notion's AI scaling + a thought

---

Hi David,

Saw Notion's AI rollout is gaining serious traction - congrats.
With 5 ML roles open, seems like you're scaling fast.

Curious how you're thinking about inference infrastructure
as usage grows. We helped [Similar Company] cut their AI
serving costs 40% while improving latency.

Worth a 15-min call to see if relevant to your roadmap?

Best,
[Name]

---

**Subject Alternatives:**
1. Notion AI + scaling question
2. Quick thought on Notion's ML hiring

---

## Email Draft Status
Draft created - check ~~email
```

<!-- merged from skills/data-visualization.md -->
name: data-visualization
description: Create effective data visualizations with Python (matplotlib, seaborn, plotly). Use when building charts, choosing the right chart type for a dataset, creating publication-quality figures, or applying design principles like accessibility and color theory.
# Data Visualization Skill
Chart selection guidance, Python visualization code patterns, design principles, and accessibility considerations for creating effective data visualizations.
## Chart Selection Guide
### Choose by Data Relationship
| What You're Showing | Best Chart | Alternatives |
|---|---|---|
| **Trend over time** | Line chart | Area chart (if showing cumulative or composition) |
| **Comparison across categories** | Vertical bar chart | Horizontal bar (many categories), lollipop chart |
| **Ranking** | Horizontal bar chart | Dot plot, slope chart (comparing two periods) |
| **Part-to-whole composition** | Stacked bar chart | Treemap (hierarchical), waffle chart |
| **Composition over time** | Stacked area chart | 100% stacked bar (for proportion focus) |
| **Distribution** | Histogram | Box plot (comparing groups), violin plot, strip plot |
| **Correlation (2 variables)** | Scatter plot | Bubble chart (add 3rd variable as size) |
| **Correlation (many variables)** | Heatmap (correlation matrix) | Pair plot |
| **Geographic patterns** | Choropleth map | Bubble map, hex map |
| **Flow / process** | Sankey diagram | Funnel chart (sequential stages) |
| **Relationship network** | Network graph | Chord diagram |
| **Performance vs. target** | Bullet chart | Gauge (single KPI only) |
| **Multiple KPIs at once** | Small multiples | Dashboard with separate charts |
### When NOT to Use Certain Charts
- **Pie charts**: Avoid unless <6 categories and exact proportions matter less than rough comparison. Humans are bad at comparing angles. Use bar charts instead.
- **3D charts**: Never. They distort perception and add no information.
- **Dual-axis charts**: Use cautiously. They can mislead by implying correlation. Clearly label both axes if used.
- **Stacked bar (many categories)**: Hard to compare middle segments. Use small multiples or grouped bars instead.
- **Donut charts**: Slightly better than pie charts but same fundamental issues. Use for single KPI display at most.
## Python Visualization Code Patterns
### Setup and Style
```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np
# Professional style setup
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'figure.figsize': (10, 6),
    'figure.dpi': 150,
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
})
# Colorblind-friendly palettes
PALETTE_CATEGORICAL = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3', '#937860']
PALETTE_SEQUENTIAL = 'YlOrRd'
PALETTE_DIVERGING = 'RdBu_r'
### Line Chart (Time Series)
```python
fig, ax = plt.subplots(figsize=(10, 6))
for label, group in df.groupby('category'):
    ax.plot(group['date'], group['value'], label=label, linewidth=2)
ax.set_title('Metric Trend by Category', fontweight='bold')
ax.set_xlabel('Date')
ax.set_ylabel('Value')
ax.legend(loc='upper left', frameon=True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
# Format dates on x-axis
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig('trend_chart.png', dpi=150, bbox_inches='tight')
### Bar Chart (Comparison)
```python
fig, ax = plt.subplots(figsize=(10, 6))
# Sort by value for easy reading
df_sorted = df.sort_values('metric', ascending=True)
bars = ax.barh(df_sorted['category'], df_sorted['metric'], color=PALETTE_CATEGORICAL[0])
# Add value labels
for bar in bars:
    width = bar.get_width()
    ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
            f'{width:,.0f}', ha='left', va='center', fontsize=10)
ax.set_title('Metric by Category (Ranked)', fontweight='bold')
ax.set_xlabel('Metric Value')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('bar_chart.png', dpi=150, bbox_inches='tight')
### Histogram (Distribution)
```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df['value'], bins=30, color=PALETTE_CATEGORICAL[0], edgecolor='white', alpha=0.8)
# Add mean and median lines
mean_val = df['value'].mean()
median_val = df['value'].median()
ax.axvline(mean_val, color='red', linestyle='--', linewidth=1.5, label=f'Mean: {mean_val:,.1f}')
ax.axvline(median_val, color='green', linestyle='--', linewidth=1.5, label=f'Median: {median_val:,.1f}')
ax.set_title('Distribution of Values', fontweight='bold')
ax.set_xlabel('Value')
ax.set_ylabel('Frequency')
ax.legend()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('histogram.png', dpi=150, bbox_inches='tight')
### Heatmap
```python
fig, ax = plt.subplots(figsize=(10, 8))
# Pivot data for heatmap format
pivot = df.pivot_table(index='row_dim', columns='col_dim', values='metric', aggfunc='sum')
sns.heatmap(pivot, annot=True, fmt=',.0f', cmap='YlOrRd',
            linewidths=0.5, ax=ax, cbar_kws={'label': 'Metric Value'})
ax.set_title('Metric by Row Dimension and Column Dimension', fontweight='bold')
ax.set_xlabel('Column Dimension')
ax.set_ylabel('Row Dimension')
plt.tight_layout()
plt.savefig('heatmap.png', dpi=150, bbox_inches='tight')
### Small Multiples
```python
categories = df['category'].unique()
n_cats = len(categories)
n_cols = min(3, n_cats)
n_rows = (n_cats + n_cols - 1) // n_cols
fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows), sharex=True, sharey=True)
axes = axes.flatten() if n_cats > 1 else [axes]
for i, cat in enumerate(categories):
    ax = axes[i]
    subset = df[df['category'] == cat]
    ax.plot(subset['date'], subset['value'], color=PALETTE_CATEGORICAL[i % len(PALETTE_CATEGORICAL)])
    ax.set_title(cat, fontsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
# Hide empty subplots
for j in range(i+1, len(axes)):
    axes[j].set_visible(False)
fig.suptitle('Trends by Category', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('small_multiples.png', dpi=150, bbox_inches='tight')
### Number Formatting Helpers
```python
def format_number(val, format_type='number'):
    """Format numbers for chart labels."""
    if format_type == 'currency':
        if abs(val) >= 1e9:
            return f'${val/1e9:.1f}B'
        elif abs(val) >= 1e6:
            return f'${val/1e6:.1f}M'
        elif abs(val) >= 1e3:
            return f'${val/1e3:.1f}K'
        else:
            return f'${val:,.0f}'
    elif format_type == 'percent':
        return f'{val:.1f}%'
    elif format_type == 'number':
        if abs(val) >= 1e9:
            return f'{val/1e9:.1f}B'
        elif abs(val) >= 1e6:
            return f'{val/1e6:.1f}M'
        elif abs(val) >= 1e3:
            return f'{val/1e3:.1f}K'
        else:
            return f'{val:,.0f}'
    return str(val)
# Usage with axis formatter
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format_number(x, 'currency')))
### Interactive Charts with Plotly
```python
import plotly.express as px
import plotly.graph_objects as go
# Simple interactive line chart
fig = px.line(df, x='date', y='value', color='category',
              title='Interactive Metric Trend',
              labels={'value': 'Metric Value', 'date': 'Date'})
fig.update_layout(hovermode='x unified')
fig.write_html('interactive_chart.html')
fig.show()
# Interactive scatter with hover data
fig = px.scatter(df, x='metric_a', y='metric_b', color='category',
                 size='size_metric', hover_data=['name', 'detail_field'],
                 title='Correlation Analysis')
fig.show()
## Design Principles
### Color
- **Use color purposefully**: Color should encode data, not decorate
- **Highlight the story**: Use a bright accent color for the key insight; grey everything else
- **Sequential data**: Use a single-hue gradient (light to dark) for ordered values
- **Diverging data**: Use a two-hue gradient with neutral midpoint for data with a meaningful center
- **Categorical data**: Use distinct hues, maximum 6-8 before it gets confusing
- **Avoid red/green only**: 8% of men are red-green colorblind. Use blue/orange as primary pair
### Typography
- **Title states the insight**: "Revenue grew 23% YoY" beats "Revenue by Month"
- **Subtitle adds context**: Date range, filters applied, data source
- **Axis labels are readable**: Never rotated 90 degrees if avoidable. Shorten or wrap instead
- **Data labels add precision**: Use on key points, not every single bar
- **Annotation highlights**: Call out specific points with text annotations
### Layout
- **Reduce chart junk**: Remove gridlines, borders, backgrounds that don't carry information
- **Sort meaningfully**: Categories sorted by value (not alphabetically) unless there's a natural order (months, stages)
- **Appropriate aspect ratio**: Time series wider than tall (3:1 to 2:1); comparisons can be squarer
- **White space is good**: Don't cram charts together. Give each visualization room to breathe
### Accuracy
- **Bar charts start at zero**: Always. A bar from 95 to 100 exaggerates a 5% difference
- **Line charts can have non-zero baselines**: When the range of variation is meaningful
- **Consistent scales across panels**: When comparing multiple charts, use the same axis range
- **Show uncertainty**: Error bars, confidence intervals, or ranges when data is uncertain
- **Label your axes**: Never make the reader guess what the numbers mean
## Accessibility Considerations
### Color Blindness
- Never rely on color alone to distinguish data series
- Add pattern fills, different line styles (solid, dashed, dotted), or direct labels
- Test with a colorblind simulator (e.g., Coblis, Sim Daltonism)
- Use the colorblind-friendly palette: `sns.color_palette("colorblind")`
### Screen Readers
- Include alt text describing the chart's key finding
- Provide a data table alternative alongside the visualization
- Use semantic titles and labels
### General Accessibility
- Sufficient contrast between data elements and background
- Text size minimum 10pt for labels, 12pt for titles
- Avoid conveying information only through spatial position (add labels)
- Consider printing: does the chart work in black and white?
### Accessibility Checklist
Before sharing a visualization:
- [ ] Chart works without color (patterns, labels, or line styles differentiate series)
- [ ] Text is readable at standard zoom level
- [ ] Title describes the insight, not just the data
- [ ] Axes are labeled with units
- [ ] Legend is clear and positioned without obscuring data
- [ ] Data source and date range are noted
