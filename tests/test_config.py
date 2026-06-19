import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULT_CONFIG, get_user_data_dir, get_resource_path


class TestConfig:
    def test_singleton(self):
        c1 = Config()
        c2 = Config()
        assert c1 is c2

    def test_default_config(self):
        config = Config()
        assert config.get('app.name') is not None
        assert config.get('database.filename') == 'ledger.db'
        assert config.get('budget.warning_threshold') == 0.8
        assert config.get('budget.danger_threshold') == 1.0

    def test_get_nested_key(self):
        config = Config()
        assert config.get('logging.level') is not None
        assert config.get('chart.default_figsize') is not None

    def test_get_default_value(self):
        config = Config()
        assert config.get('non.existent.key', 'default') == 'default'
        assert config.get('non.existent.key') is None

    def test_get_db_path(self):
        config = Config()
        db_path = config.get_db_path()
        assert db_path is not None
        assert str(db_path).endswith('ledger.db')

    def test_get_logs_dir(self):
        config = Config()
        logs_dir = config.get_logs_dir()
        assert logs_dir is not None
        assert 'logs' in str(logs_dir).lower() or 'StockPulse' in str(logs_dir)

    def test_bracket_access(self):
        config = Config()
        assert config['app.name'] == config.get('app.name')

    def test_contains(self):
        config = Config()
        assert 'app.name' in config
        assert 'non.existent' not in config

    def test_raw_config(self):
        config = Config()
        raw = config.raw
        assert isinstance(raw, dict)
        assert 'app' in raw
        assert 'database' in raw


class TestPathFunctions:
    def test_get_user_data_dir(self):
        data_dir = get_user_data_dir()
        assert data_dir is not None
        assert isinstance(data_dir, Path)
        assert 'StockPulse' in str(data_dir)

    def test_get_resource_path(self):
        resource_path = get_resource_path('config.yaml')
        assert resource_path is not None
        assert isinstance(resource_path, Path)
