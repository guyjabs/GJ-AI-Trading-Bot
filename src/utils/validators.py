"""
Input validation schemas and utilities for API endpoints.
"""

from marshmallow import Schema, fields, validate, ValidationError
from typing import Dict, Any


class StartBotSchema(Schema):
    """Schema for start_bot WebSocket event"""
    mode = fields.Str(
        required=True,
        validate=validate.OneOf(['demo', 'manual', 'auto']),
        error_messages={'required': 'Mode is required'}
    )


class ForceResearchSchema(Schema):
    """Schema for force research API endpoint"""
    sources = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(['newsapi', 'alphavantage', 'finnhub'])),
        values=fields.Bool(),
        required=True
    )


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock/crypto symbol format.
    
    Args:
        symbol: Stock or crypto symbol
        
    Returns:
        True if valid
        
    Raises:
        ValidationError if invalid
    """
    if not symbol:
        raise ValidationError('Symbol cannot be empty')
    
    # Remove common suffixes for validation
    clean_symbol = symbol.replace('-USD', '').replace('/USD', '')
    
    # Check format: 1-5 uppercase letters
    if not clean_symbol.isalpha() or not clean_symbol.isupper():
        raise ValidationError(f'Invalid symbol format: {symbol}')
    
    if len(clean_symbol) < 1 or len(clean_symbol) > 5:
        raise ValidationError(f'Symbol length must be 1-5 characters: {symbol}')
    
    return True


def validate_quantity(quantity: float, min_qty: float = 0.0001) -> bool:
    """
    Validate trade quantity.
    
    Args:
        quantity: Number of shares/units
        min_qty: Minimum allowed quantity
        
    Returns:
        True if valid
        
    Raises:
        ValidationError if invalid
    """
    if quantity <= 0:
        raise ValidationError('Quantity must be positive')
    
    if quantity < min_qty:
        raise ValidationError(f'Quantity must be at least {min_qty}')
    
    return True


def sanitize_input(data: Dict[str, Any], schema: Schema) -> Dict[str, Any]:
    """
    Validate and sanitize input data using a marshmallow schema.
    
    Args:
        data: Input data dictionary
        schema: Marshmallow schema instance
        
    Returns:
        Validated and sanitized data
        
    Raises:
        ValidationError if validation fails
    """
    try:
        return schema.load(data)
    except ValidationError as e:
        raise ValidationError(f'Validation failed: {e.messages}')
