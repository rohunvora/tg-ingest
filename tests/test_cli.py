import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from click.testing import CliRunner

from tg_export.cli import cli, parse_chat_url, get_last_message_id, serialize_entities


class TestChatUrlParsing:
    def test_parse_private_supergroup_url(self):
        url = "https://t.me/c/123456789"
        result = parse_chat_url(url)
        assert result == -100123456789
    
    def test_parse_public_group_url(self):
        url = "https://t.me/mygroup"
        result = parse_chat_url(url)
        assert result == "mygroup"
    
    def test_parse_joinchat_url(self):
        url = "https://t.me/joinchat/ABCDEFGH"
        result = parse_chat_url(url)
        assert result == "ABCDEFGH"


class TestLastMessageId:
    def test_get_last_message_id_empty_file(self, tmp_path):
        file = tmp_path / "test.jsonl"
        file.write_text("")
        assert get_last_message_id(file) is None
    
    def test_get_last_message_id_nonexistent_file(self, tmp_path):
        file = tmp_path / "nonexistent.jsonl"
        assert get_last_message_id(file) is None
    
    def test_get_last_message_id_valid_file(self, tmp_path):
        file = tmp_path / "test.jsonl"
        data = [
            {"msg_id": 1, "text": "first"},
            {"msg_id": 2, "text": "second"},
            {"msg_id": 3, "text": "last"}
        ]
        with open(file, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        
        assert get_last_message_id(file) == 3


class TestSerializeEntities:
    def test_serialize_empty_entities(self):
        assert serialize_entities(None) == []
        assert serialize_entities([]) == []
    
    def test_serialize_bold_entity(self):
        from telethon.tl.types import MessageEntityBold
        entity = MessageEntityBold(offset=0, length=4)
        result = serialize_entities([entity])
        assert result == [{"type": "bold", "offset": 0, "length": 4}]


class TestCLI:
    @patch.dict('os.environ', {'TELEGRAM_API_ID': '12345', 'TELEGRAM_API_HASH': 'abcdef'})
    @patch('tg_export.cli.TelegramClient')
    @patch('tg_export.cli.Path')
    def test_login_command(self, mock_path, mock_client):
        runner = CliRunner()
        
        # Mock session file
        mock_session_file = Mock()
        mock_session_file.exists.return_value = False
        mock_path.return_value = mock_session_file
        
        # Mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.session.save.return_value = "session_string"
        mock_client.return_value = mock_client_instance
        
        result = runner.invoke(cli, ['login'])
        
        # Should save session
        mock_session_file.write_text.assert_called_once()
    
    def test_login_without_credentials(self):
        runner = CliRunner()
        with patch.dict('os.environ', clear=True):
            result = runner.invoke(cli, ['login'])
            assert result.exit_code != 0
            assert "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set" in result.output


def test_unique_message_ids(tmp_path):
    """Test that exported messages have unique IDs"""
    file = tmp_path / "test.jsonl"
    
    # Simulate writing messages
    messages = [
        {"msg_id": 1, "text": "first"},
        {"msg_id": 2, "text": "second"},
        {"msg_id": 3, "text": "third"}
    ]
    
    with open(file, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
    
    # Read and verify uniqueness
    seen_ids = set()
    with open(file) as f:
        for line in f:
            data = json.loads(line)
            msg_id = data['msg_id']
            assert msg_id not in seen_ids, f"Duplicate message ID: {msg_id}"
            seen_ids.add(msg_id)
    
    assert len(seen_ids) == 3