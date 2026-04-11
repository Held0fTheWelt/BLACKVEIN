from pathlib import Path

root = Path("story_runtime_core")
src = root / "builtin_experience_templates.py"
lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
# lines 31-470 inclusive -> indices 30:470
chunk = lines[30:470]
header = '''"""God of Carnage solo builtin experience template (SSOT fragment).

Canonical dramatic YAML remains under content/modules/god_of_carnage/; this template
must stay title-aligned (VERTICAL_SLICE_CONTRACT_GOC).
"""

from __future__ import annotations

from .experience_template_models import (
    ActionTemplate,
    BeatTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    ExperienceKind,
    ExperienceTemplate,
    ExitTemplate,
    JoinPolicy,
    ParticipantMode,
    PropTemplate,
    RoleTemplate,
    RoomTemplate,
)


'''
Path("story_runtime_core/goc_solo_builtin_template.py").write_text(header + "".join(chunk), encoding="utf-8")
# Strip original: keep 1-30 and 471-end
new_src = "".join(lines[:30]) + "".join(lines[470:])
src.write_text(new_src, encoding="utf-8")
# Insert import after experience_template_models block in remaining file
text = src.read_text(encoding="utf-8")
needle = ")\n\n\ndef load_builtin_templates"
if needle not in text:
    needle = ")\n\ndef load_builtin_templates"
if needle not in text:
    raise SystemExit("needle not found")
insert = ")\n\nfrom .goc_solo_builtin_template import build_god_of_carnage_solo\n\n\ndef load_builtin_templates"
text = text.replace(needle, insert, 1)
src.write_text(text, encoding="utf-8")
print("ok")
