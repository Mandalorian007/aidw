# Context

## Issue #{{ issue.number }}: {{ issue.title }}
{{ issue.body }}

## Issue Comments
{% for c in issue.comments %}
**@{{ c.author }}** ({{ c.date }}):
{{ c.body }}

{% endfor %}
{% if pr %}
## Pull Request #{{ pr.number }}: {{ pr.title }}
Branch: `{{ pr.branch }}`

{{ pr.body }}

### PR Comments
{% for c in pr.comments %}
**@{{ c.author }}** ({{ c.date }}):
{{ c.body }}

{% endfor %}
### Git State
```
{{ git_log }}
```

### Files Changed
{{ git_diff_stat }}
{% endif %}

## Trigger
**@{{ trigger.author }}**: {{ trigger.body }}
