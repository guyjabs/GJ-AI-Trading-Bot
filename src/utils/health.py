"""
Health check utilities for production monitoring.
"""

from typing import Dict, Any
from datetime import datetime
import time


class HealthCheck:
    """Health check manager for monitoring system status"""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.checks[name] = check_func
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return status"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': int(time.time() - self.start_time),
            'checks': {}
        }
        
        for name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = {
                    'status': 'pass' if check_result else 'fail',
                    'details': check_result if isinstance(check_result, dict) else {}
                }
                
                if not check_result:
                    results['status'] = 'degraded'
            except Exception as e:
                results['checks'][name] = {
                    'status': 'fail',
                    'error': str(e)
                }
                results['status'] = 'unhealthy'
        
        return results


# Global health check instance
health_check = HealthCheck()


def check_database() -> bool:
    """Check database connectivity"""
    # TODO: Implement actual DB check when PostgreSQL is integrated
    return True


def check_alpaca_api() -> bool:
    """Check Alpaca API connectivity"""
    try:
        from src.api.alpaca import get_alpaca_client
        from config import ALPACA_CONFIG
        
        client = get_alpaca_client(
            api_key=ALPACA_CONFIG.get('api_key'),
            secret_key=ALPACA_CONFIG.get('secret_key'),
            paper=ALPACA_CONFIG.get('paper', True)
        )
        
        # Try to get account info
        account = client.get_account_info()
        return account.get('buying_power', 0) >= 0
    except Exception:
        return False


def check_redis() -> bool:
    """Check Redis connectivity"""
    # TODO: Implement when Redis is integrated
    return True


# Register default checks
health_check.register_check('database', check_database)
health_check.register_check('alpaca_api', check_alpaca_api)
health_check.register_check('redis', check_redis)
