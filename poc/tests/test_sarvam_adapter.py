import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the poc directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sarvam_adapter import SarvamClient

class TestSarvamAdapter(unittest.TestCase):

    @patch("sarvam_adapter.SarvamAI")
    @patch.dict(os.environ, {"SARVAM_API_KEY": "fake_key"})
    def setUp(self, mock_sarvam_class):
        self.mock_client = MagicMock()
        mock_sarvam_class.return_value = self.mock_client
        self.adapter = SarvamClient()

    def test_chat_completion_success(self):
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a response"
        mock_response.choices = [mock_choice]
        mock_response.usage.completion_tokens = 10
        
        # In the new SDK, chat.completions is a direct method call
        self.mock_client.chat.completions.return_value = mock_response
        
        # Execute
        answer = self.adapter.chat_completion("sys prompt", "user prompt")
        
        # Assert
        self.assertEqual(answer, "This is a response")
        self.mock_client.chat.completions.assert_called_once()
        args, kwargs = self.mock_client.chat.completions.call_args
        self.assertEqual(kwargs["messages"][0]["content"], "sys prompt")
        self.assertEqual(kwargs["messages"][1]["content"], "user prompt")

    def test_transcribe_success(self):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.transcript = "Mock transcript"
        mock_response.language_code = "en-IN"
        self.mock_client.speech_to_text.transcribe.return_value = mock_response
        
        # Execute
        transcript, det_lang = self.adapter.transcribe(b"fake_audio_bytes")
        
        # Assert
        self.assertEqual(transcript, "Mock transcript")
        self.assertEqual(det_lang, "en-IN")
        self.mock_client.speech_to_text.transcribe.assert_called_once()

    def test_text_to_speech_success(self):
        # Setup mock response
        mock_response = MagicMock()
        import base64
        mock_response.audios = [base64.b64encode(b"audio_bytes").decode("utf-8")]
        self.mock_client.text_to_speech.convert.return_value = mock_response
        
        # Execute
        audio = self.adapter.text_to_speech("some text")
        
        # Assert
        self.assertEqual(audio, b"audio_bytes")
        self.mock_client.text_to_speech.convert.assert_called_once()

    def test_translate_success(self):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.translated_text = "வணக்கம்"
        self.mock_client.text.translate.return_value = mock_response
        
        # Execute
        result = self.adapter.translate("hello", "en-IN", "ta-IN")
        
        # Assert
        self.assertEqual(result, "வணக்கம்")
        self.mock_client.text.translate.assert_called_once()
        args, kwargs = self.mock_client.text.translate.call_args
        self.assertEqual(kwargs["input"], "hello")
        self.assertEqual(kwargs["source_language_code"], "en-IN")
        self.assertEqual(kwargs["target_language_code"], "ta-IN")

if __name__ == "__main__":
    unittest.main()
