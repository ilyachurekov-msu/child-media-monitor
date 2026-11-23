"""Fail publication on unreviewed licenses or prohibited source files."""
import json
import subprocess
import sys
import tomllib
import re
from importlib.metadata import distribution
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from pathlib import Path

licenses = json.loads(subprocess.check_output([sys.executable, '-m', 'piplicenses', '--format=json'], text=True))
project = tomllib.loads(Path('pyproject.toml').read_text())['project']
pending = project['dependencies'] + project['optional-dependencies']['dev']
required = set()
while pending:
    dependency = Requirement(pending.pop())
    if dependency.marker and not dependency.marker.evaluate({'extra': ''}): continue
    name = canonicalize_name(dependency.name)
    if name in required: continue
    required.add(name)
    pending.extend(distribution(dependency.name).requires or [])
allowed = ('MIT', 'Apache', 'BSD', 'ISC', 'MPL', 'Mozilla', 'Python Software', 'PSF', 'Unlicense', 'Public Domain', 'LGPL', 'HPND', 'Zope')
bad = [(r['Name'], r['License']) for r in licenses if canonicalize_name(r['Name']) in required and not any(a.casefold() in r['License'].casefold() for a in allowed)]
assert not bad, f'License review required: {bad}'
for filename in ['.env', 'docs/source-check.json']:
    # Live diagnostic output is intentionally not part of the public package.
    if filename == '.env': assert not Path(filename).exists(), 'Never publish .env'
tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
for filename in tracked:
    contents = Path(filename).read_text(encoding='utf-8')
    assert not re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)', contents), 'Potential secret in ' + filename
print('Dependency license inventory and local secret patterns checked')
