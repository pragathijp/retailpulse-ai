"""Grounding guarantees of the assistant. The LLM is always faked: no key, no network."""
import pytest

from ai_assistant import REFUSAL, ask, extract_numbers, unsupported_numbers

CTX = {'meta': {'reference_month': '2011-11'},
       'sections': {'monthly_totals': {'source_table': 'mart_monthly_sales', 'period': 'last 13 months', 'row_count': 2,
                                       'rows': [{'sales_month': '2011-11-01', 'net_revenue': 1161817.38},
                                                {'sales_month': '2011-10-01', 'net_revenue': 1020000.0}]}}}


def test_grounded_answer_is_verified():
    r = ask('Revenue in 2011-11?', context=CTX,
            complete=lambda s, u: 'Net revenue was 1,161,817.38 GBP in 2011-11.' + chr(10) + 'Sources: mart_monthly_sales, last 13 months')
    assert r['verified'] and r['unsupported_numbers'] == []


def test_difference_of_two_context_numbers_is_allowed():
    r = ask('Change?', context=CTX, complete=lambda s, u: 'Revenue rose by 141,817.38, from 1,020,000.00 to 1,161,817.38.')
    assert r['verified']


def test_percent_change_of_two_context_numbers_is_allowed():
    r = ask('Growth?', context=CTX, complete=lambda s, u: 'That is a 13.90 percent increase (1,161,817.38 vs 1,020,000.00).')
    assert r['verified']


def test_hallucinated_number_is_withheld():
    r = ask('Revenue?', context=CTX, complete=lambda s, u: 'Net revenue was 9,999,999.99 GBP.')
    assert not r['verified'] and r['answer'].startswith(REFUSAL) and '9999999.99' in r['unsupported_numbers']


def test_slightly_wrong_number_is_withheld():
    r = ask('Revenue?', context=CTX, complete=lambda s, u: 'Net revenue was 1,161,817.39 GBP.')
    assert not r['verified']


def test_retry_recovers_and_names_the_bad_figure():
    prompts, answers = [], iter(['Revenue 5,555.55.', 'Revenue 1,161,817.38.'])

    def fake(system, user):
        prompts.append(user)
        return next(answers)

    r = ask('Revenue?', context=CTX, complete=fake)
    assert r['verified'] and len(prompts) == 2 and '5555.55' in prompts[1]


def test_refusal_is_accepted_as_a_valid_answer():
    r = ask('Weather?', context=CTX, complete=lambda s, u: REFUSAL + ' The context has no weather data.')
    assert r['verified'] and r['answer'].startswith(REFUSAL)


def test_empty_answer_is_not_verified():
    assert not ask('Revenue?', context=CTX, complete=lambda s, u: '')['verified']


def test_dates_and_list_markers_are_not_treated_as_figures():
    assert extract_numbers('1. Revenue in 2011-11 was 1,161,817.38') == ['1161817.38']
    assert unsupported_numbers('2011-11-01 net revenue was 1,020,000.00', CTX) == []


def test_every_call_receives_the_system_prompt_and_context():
    seen = {}

    def fake(system, user):
        seen['system'], seen['user'] = system, user
        return REFUSAL

    ask('Revenue?', context=CTX, complete=fake)
    assert 'ONLY the figures' in seen['system'] and '1161817.38' in seen['user']


def test_gemini_wrapper_sends_system_prompt_model_and_context(monkeypatch):
    import ai_assistant

    calls = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            calls.update(model=model, contents=contents, system=config.system_instruction, temperature=config.temperature)
            return type('Resp', (), {'text': 'ok'})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(ai_assistant, 'gemini_client', lambda: FakeClient())
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    assert ai_assistant.gemini_complete('SYSTEM', 'USER') == 'ok'
    assert calls == {'model': 'test-model', 'contents': 'USER', 'system': 'SYSTEM', 'temperature': 0}


def test_missing_configuration_gives_a_clear_error(monkeypatch):
    import ai_assistant

    monkeypatch.setattr(ai_assistant, 'load_env', lambda: None)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)
    with pytest.raises(RuntimeError, match='GEMINI_MODEL'):
        ai_assistant.gemini_complete('s', 'u')
    monkeypatch.setenv('GEMINI_MODEL', 'm')
    with pytest.raises(RuntimeError, match='GEMINI_API_KEY'):
        ai_assistant.gemini_complete('s', 'u')
