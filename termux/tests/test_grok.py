import io
import json
import os
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grok import Grok


class GrokAdapter(unittest.TestCase):
    def test_unconfigured_does_not_make_network_request(self):
        with patch.dict(os.environ, {'XAI_API_KEY': '', 'LEO_GROK_MODEL': ''}), \
             patch('urllib.request.urlopen') as request:
            with self.assertRaises(ValueError):
                Grok().reply('hello')
            request.assert_not_called()

    def test_mock_tool_response_is_a_proposal_only(self):
        response = {'choices': [{'message': {'content': 'Please review.', 'tool_calls': [
            {'function': {'name': 'propose_command', 'arguments': json.dumps({'cmd': 'pwd', 'reason': 'test'})}}
        ]}}]}
        # Dummy placeholders are not credentials; no live request or shell execution.
        with patch.dict(os.environ, {'XAI_API_KEY': 'fixture-not-a-real-key', 'LEO_GROK_MODEL': 'fixture-model'}), \
             patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as request:
            content, proposal = Grok().reply('where are we?')
            self.assertEqual(content, 'Please review.')
            self.assertEqual(proposal['cmd'], 'pwd')
            req = request.call_args.args[0]
            body = json.loads(req.data)
            self.assertEqual(req.full_url, 'https://api.x.ai/v1/chat/completions')
            self.assertEqual(body['tools'][0]['function']['name'], 'propose_command')
            self.assertFalse(body['parallel_tool_calls'])
