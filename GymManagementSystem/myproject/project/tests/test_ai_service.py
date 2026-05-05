"""Tests for AI service — uses the mock fallback path (no real API calls)."""
from unittest.mock import patch

import pytest

from project.ai_service import generate_fitness_plan, chat_reply, _mock_plan


@pytest.mark.django_db
class TestPlanGenerator:
    def test_mock_plan_has_seven_days(self, member):
        plan = _mock_plan(member)
        assert len(plan['workout']) == 7
        assert len(plan['diet']) == 7
        assert 'summary' in plan

    def test_no_api_key_falls_back_to_mock(self, member, settings):
        settings.GEMINI_API_KEY = ''
        parsed, raw = generate_fitness_plan(member)
        assert len(parsed['workout']) == 7
        assert 'Mock plan' in parsed['summary']

    def test_real_call_path_invokes_gemini(self, member, settings):
        settings.GEMINI_API_KEY = 'fake-key'

        # Patch the module attribute google.generativeai (imported lazily)
        with patch('google.generativeai.GenerativeModel') as MockModel, \
             patch('google.generativeai.configure'):
            MockModel.return_value.generate_content.return_value.text = (
                '{"summary":"ok","workout":[],"diet":[],"tips":[]}'
            )
            parsed, raw = generate_fitness_plan(member)
        assert parsed['summary'] == 'ok'


@pytest.mark.django_db
class TestChatReply:
    def test_no_api_key_returns_offline_stub(self, member, settings):
        settings.GEMINI_API_KEY = ''
        reply = chat_reply(member, 'hello', [])
        assert 'offline' in reply.lower()

    def test_real_path(self, member, settings):
        settings.GEMINI_API_KEY = 'fake-key'
        with patch('google.generativeai.GenerativeModel') as MockModel, \
             patch('google.generativeai.configure'):
            chat_obj = MockModel.return_value.start_chat.return_value
            chat_obj.send_message.return_value.text = 'Drink water!'
            reply = chat_reply(member, 'hi', [])
        assert reply == 'Drink water!'
