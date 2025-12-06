"""
Unit tests for OpenAI API Client.
"""

import pytest
from unittest.mock import Mock, patch
import json
from src.api.openai import make_ai_request, parse_ai_response


class TestOpenAIClient:
    """Test suite for OpenAI API integration"""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        with patch('src.api.openai.client') as mock:
            yield mock
    
    def test_make_ai_request_success(self, mock_openai_client):
        """Test successful AI request"""
        # Mock response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "decision": "buy",
            "symbol": "AAPL",
            "quantity": 10
        })
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = make_ai_request("Test prompt")
        
        assert result is not None
        assert result.choices[0].message.content is not None
    
    def test_parse_ai_response_valid_json(self):
        """Test parsing valid JSON response"""
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "decision": "sell",
            "symbol": "TSLA",
            "quantity": 5
        })
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        result = parse_ai_response(mock_response)
        
        assert result['decision'] == 'sell'
        assert result['symbol'] == 'TSLA'
        assert result['quantity'] == 5
    
    def test_parse_ai_response_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = '''```json
{
    "decision": "buy",
    "symbol": "NVDA",
    "quantity": 15
}
```'''
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        result = parse_ai_response(mock_response)
        
        assert result['decision'] == 'buy'
        assert result['symbol'] == 'NVDA'
        assert result['quantity'] == 15
    
    def test_parse_ai_response_strips_markdown(self):
        """Test that markdown code blocks are properly stripped"""
        mock_response = Mock()
        mock_message = Mock()
        # The parser uses regex to strip ```json and ``` markers
        mock_message.content = '```json\n{"decision": "hold"}\n```'
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        result = parse_ai_response(mock_response)
        
        assert result['decision'] == 'hold'
    
    def test_parse_ai_response_invalid_json(self):
        """Test handling of invalid JSON"""
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "This is not valid JSON"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with pytest.raises(Exception) as exc_info:
            parse_ai_response(mock_response)
        
        assert "Invalid JSON response" in str(exc_info.value)
    
    def test_make_ai_request_api_error(self, mock_openai_client):
        """Test handling of API errors"""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            make_ai_request("Test prompt")
    
    def test_integration_request_and_parse(self, mock_openai_client):
        """Test full flow of request and parse"""
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = '{"decision": "buy", "symbol": "MSFT", "quantity": 8}'
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        ai_response = make_ai_request("Should I buy MSFT?")
        parsed = parse_ai_response(ai_response)
        
        assert parsed['decision'] == 'buy'
        assert parsed['symbol'] == 'MSFT'
        assert parsed['quantity'] == 8
