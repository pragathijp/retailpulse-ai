#!/usr/bin/env python3
"""Grounded business assistant: the LLM narrates supplied JSON only, and every number it writes is verified.

Flow: question -> context_builder (pre-aggregated marts) -> LLM -> number check -> answer, one retry, or refusal.
The LLM is Google Gemini through the google-genai SDK; any function complete(system, user) -> str can be injected
(the tests use a fake one, so they need no key and no network).

Usage:
    python src/ai_assistant.py "Which products declined most last month?"
    python src/ai_assistant.py --list-models
    python src/ai_assistant.py --golden          (writes docs/ai_golden_answers.md)
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DOCS, ROOT  # noqa: E402
from context_builder import build_context  # noqa: E402

NL = chr(10)
REFUSAL = 'I cannot answer this from the available data.'
DATE_RE = re.compile(r'[0-9]{4}-[0-9]{2}(?:-[0-9]{2})?')
NUM_RE = re.compile(r'[0-9][0-9,]*(?:[.][0-9]+)?')
LIST_MARKER_RE = re.compile(r'(?m)^[ ]*[0-9]+[.)][ ]')

SYSTEM_PROMPT = NL.join([
    'You are RetailPulse, a retail analytics assistant for business users.',
    'Rules:',
    '1. Use ONLY the figures in the JSON context. Never use outside knowledge, estimates or rounding.',
    '2. Quote every figure exactly as written in the context, in full, with thousands separators and no abbreviations such as K, M or B.',
    '3. You may state a difference or percent change between two context figures; show both figures you used.',
    '4. If the context cannot answer the question, reply exactly: ' + REFUSAL + ' Then say which data is missing.',
    '5. There is no product category field; treat product as stock code and say so when asked about categories.',
    '6. Currency is GBP. Last month means the most recent complete month in the context; mention that the final month of data is partial when relevant.',
    '7. Reply as a short, actionable business summary, then a final line starting with Sources: listing source_table and period.',
])

GOLDEN_QUESTIONS = [
    'What is the total net revenue and how many orders were there?',
    'Which products declined the most last month?',
    'Which country generates the most net revenue?',
    'How many customers are in the Champions RFM segment?',
    'Is there any unexplained revenue variance between store revenue and RFM revenue?',
]


# ---- LLM (Gemini) -------------------------------------------------------------------------------

def load_env():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def gemini_client():
    from google import genai
    load_env()
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not set. Put it in .env (see .env.example).')
    return genai.Client(api_key=key)


def gemini_complete(system, user):
    from google.genai import types
    load_env()
    model = os.getenv('GEMINI_MODEL')
    if not model:
        raise RuntimeError('GEMINI_MODEL is not set. Run: python src/ai_assistant.py --list-models, then put one name in .env')
    resp = gemini_client().models.generate_content(
        model=model, contents=user,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0, max_output_tokens=4096))
    return resp.text or ''


def list_models():
    for m in gemini_client().models.list():
        actions = getattr(m, 'supported_actions', None) or []
        if 'generateContent' in actions:
            print(m.name)


# ---- number verification ------------------------------------------------------------------------

def extract_numbers(text):
    text = LIST_MARKER_RE.sub('', DATE_RE.sub(' ', text))
    return [t for t in (tok.rstrip(',').replace(',', '') for tok in NUM_RE.findall(text)) if t]


def collect_context_numbers(node, nums):
    if isinstance(node, dict):
        for v in node.values():
            collect_context_numbers(v, nums)
    elif isinstance(node, list):
        for v in node:
            collect_context_numbers(v, nums)
    elif isinstance(node, bool) or node is None:
        return
    elif isinstance(node, (int, float)):
        nums.append(abs(float(node)))
    elif isinstance(node, str):
        for d in DATE_RE.findall(node):
            nums.extend(float(p) for p in d.split('-'))
        nums.extend(float(t) for t in extract_numbers(node))


def allowed_values(context):
    """Every context number, plus absolute differences and percent changes between any two of them."""
    nums = []
    collect_context_numbers(context, nums)
    base = np.unique(np.array(nums, dtype=float))
    delta = np.abs(base[:, None] - base[None, :])
    with np.errstate(divide='ignore', invalid='ignore'):
        pct = delta / np.where(base[None, :] == 0, np.nan, base[None, :]) * 100
    pct = pct[np.isfinite(pct)]
    return np.concatenate([base, delta.ravel(), pct.ravel()])


def unsupported_numbers(answer, context):
    allowed = allowed_values(context)
    bad = []
    for tok in extract_numbers(answer):
        decimals = len(tok.split('.')[1]) if '.' in tok else 0
        if not np.any(np.abs(np.round(allowed, decimals) - float(tok)) < 1e-6):
            bad.append(tok)
    return bad


# ---- main entry point ---------------------------------------------------------------------------

def ask(question, complete=None, context=None):
    complete = complete or gemini_complete
    context = context or build_context(question)
    user = f'Question: {question}' + NL + NL + 'Context JSON:' + NL + json.dumps(context, default=str)
    answer = (complete(SYSTEM_PROMPT, user) or '').strip()
    bad = unsupported_numbers(answer, context) if answer else ['<empty answer>']
    if bad:
        retry = user + NL + NL + f'Your previous answer contained figures that are not in the context: {bad}. ' \
                                 'Rewrite it using only figures from the context.'
        answer = (complete(SYSTEM_PROMPT, retry) or '').strip()
        bad = unsupported_numbers(answer, context) if answer else ['<empty answer>']
    if bad:
        return {'answer': REFUSAL + ' (answer withheld: it contained figures that could not be verified)',
                'verified': False, 'unsupported_numbers': bad, 'context': context}
    return {'answer': answer, 'verified': True, 'unsupported_numbers': [], 'context': context}


def run_golden():
    lines = ['# AI Assistant: Golden Answers', '',
             'Each answer below was generated live and passed the number-grounding check unless marked otherwise.', '']
    for q in GOLDEN_QUESTIONS:
        r = ask(q)
        lines += [f'## {q}', '', f'Verified: {"yes" if r["verified"] else "NO"}', '', r['answer'], '']
        print(('OK   ' if r['verified'] else 'FAIL ') + q)
    DOCS.mkdir(exist_ok=True)
    (DOCS / 'ai_golden_answers.md').write_text(NL.join(lines))
    print('Wrote docs/ai_golden_answers.md')


def main(argv):
    try:
        if argv[:1] == ['--list-models']:
            return list_models()
        if argv[:1] == ['--golden']:
            return run_golden()
    except RuntimeError as exc:
        sys.exit(f'Assistant not configured: {exc}')
    try:
        result = ask(' '.join(argv) or 'Which products declined the most last month?')
    except RuntimeError as exc:
        sys.exit(f'Assistant not configured: {exc}')
    print(result['answer'])
    print(NL + 'verified:', result['verified'], result['unsupported_numbers'] or '')


if __name__ == '__main__':
    main(sys.argv[1:])
