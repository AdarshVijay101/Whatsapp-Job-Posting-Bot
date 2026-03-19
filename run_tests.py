import pytest
import sys

if __name__ == '__main__':
    with open('pytest_output_clean.log', 'w', encoding='utf-8') as f:
        sys.stdout = f
        sys.stderr = f
        pytest.main(['-q', '--disable-warnings', '--tb=short', 'tests/'])
