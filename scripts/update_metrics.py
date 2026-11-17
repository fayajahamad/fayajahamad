#!/usr/bin/env python3
"""Refresh public GitHub profile metrics without nonstandard dependencies.

Uses the GitHub REST API and an optional GH_TOKEN environment variable.
All figures are based on public repository data. No inflated or fabricated counts.
"""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections import Counter
from html import escape

USER = os.getenv("PROFILE_USER", "fayajahamad")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
BASE = "https://api.github.com"
TOKEN = os.getenv("GH_TOKEN", "")


def get_json(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "fayajahamad-profile-metrics", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(BASE + path, headers=headers)
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GitHub API fetch failed for {path}: {exc}") from exc


def text(x, y, value, size, color="#EFF9FF", weight="600", anchor=None):
    attrs = f' x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}"'
    if anchor: attrs += f' text-anchor="{anchor}"'
    return '<text'+attrs+'>'+escape(str(value))+'</text>'


def shell(title, content):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="580" height="200" viewBox="0 0 580 200" role="img" aria-label="{escape(title)}"><rect width="580" height="200" rx="18" fill="#081524"/><rect width="548" height="1" x="16" y="67" fill="#234659"/><g font-family="Segoe UI,Arial,sans-serif">{text(26,44,title,18,'#4BD9F5','700')}{content}</g></svg>"""


def main():
    user = get_json('/users/'+USER)
    repos = []
    page = 1
    while True:
        batch = get_json(f'/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected GitHub API response for repositories")
        repos.extend(r for r in batch if not r.get('fork') and not r.get('private'))
        if len(batch) < 100: break
        page += 1
        if page > 100: raise RuntimeError('Unexpected pagination size')

    stars = sum(int(r.get('stargazers_count') or 0) for r in repos)
    public_count = int(user.get('public_repos',len(repos)))
    followers = int(user.get('followers',0))
    vals = [(26,public_count,'PUBLIC REPOS'),(211,stars,'RECEIVED STARS'),(396,followers,'FOLLOWERS')]
    content = ''
    for x,v,label in vals:
        content += text(x,124,v,42,'#EFF9FF','750')
        content += text(x,156,label,13,'#A9C5D5','650')
    (OUT/'github-metrics.svg').write_text(shell('PUBLIC GITHUB METRICS',content),encoding='utf-8')

    counts = Counter()
    for r in repos:
        languages = get_json('/repos/'+USER+'/'+r['name']+'/languages')
        if not isinstance(languages,dict): raise RuntimeError('Unexpected languages response')
        for key, value in languages.items(): counts[key]+=int(value)
    total = sum(counts.values())
    top = counts.most_common(4)
    # Aggregate smaller languages rather than leaving an unlabeled gap.
    if len(counts) > 4:
        top = counts.most_common(3)
        top.append(("Other", total - sum(count for _, count in top)))
    palette=['#4BD9F5','#7EE6BB','#FFC674','#A99AF8']
    content=''
    if not total:
        content+=text(26,119,'No language-byte data reported',21,'#EFF9FF')
    else:
        bar_start=26
        for (label,amt),color in zip(top,palette):
            width=528*amt/total
            content+=f'<rect x="{bar_start:.1f}" y="81" width="{width:.1f}" height="13" rx="2" fill="{color}" />'
            bar_start+=width
        for idx,(label,amt) in enumerate(top):
            x=26+(idx%2)*275; y=131+(idx//2)*34
            content+=f'<circle cx="{x+5}" cy="{y-5}" r="5" fill="{palette[idx]}"/>'
            content+=text(x+17,y,f'{label}  {amt/total*100:.1f}%',16,'#EFF9FF','500')
    (OUT/'languages.svg').write_text(shell('LANGUAGES BY CODE BYTES',content),encoding='utf-8')
    print('Updated metrics from',public_count,'public repos:',stars,'stars,',followers,'followers')

if __name__ == '__main__':
    main()
