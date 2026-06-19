import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def get_user_data_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'StockPulse'


def get_user_config_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'StockPulse'


def get_user_logs_dir() -> Path:
    return get_user_data_dir() / 'logs'


def get_resource_path(relative_path: str) -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return base_path / relative_path


DEFAULT_CONFIG: Dict[str, Any] = {
    'app': {
        'name': 'StockPulse 记账',
        'version': '1.0.0',
        'theme': 'light',
        'color_theme': 'blue',
        'window_size': [1200, 800],
    },
    'database': {
        'path': None,
        'filename': 'ledger.db',
    },
    'logging': {
        'level': 'INFO',
        'directory': 'logs',
        'filename': 'app_{date}.log',
        'max_bytes': 10485760,
        'backup_count': 30,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    },
    'budget': {
        'default_cycle': 'monthly',
        'warning_threshold': 0.8,
        'danger_threshold': 1.0,
    },
    'ui': {
        'sidebar_width': 180,
        'font_family': 'Microsoft YaHei',
        'font_size': 14,
        'date_format': '%Y-%m-%d',
        'datetime_format': '%Y-%m-%d %H:%M:%S',
    },
    'chart': {
        'figure_dpi': 100,
        'default_figsize': [6, 4],
        'font_families': [
            'Microsoft YaHei',
            'SimHei',
            'Arial Unicode MS',
        ],
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml_config(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


class Config:
    _instance: Optional['Config'] = None
    _config: Dict[str, Any]

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        self._config = dict(DEFAULT_CONFIG)

        default_config_path = get_resource_path('config.yaml')
        default_cfg = _load_yaml_config(default_config_path)
        if default_cfg:
            self._config = _deep_merge(self._config, default_cfg)

        user_config_path = get_user_config_dir() / 'config.yaml'
        user_cfg = _load_yaml_config(user_config_path)
        if user_cfg:
            self._config = _deep_merge(self._config, user_cfg)

    def reload(self) -> None:
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_db_path(self) -> Path:
        db_path = self.get('database.path')
        if db_path:
            return Path(db_path)
        db_filename = self.get('database.filename', 'ledger.db')
        user_dir = get_user_data_dir()
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / db_filename

    def get_logs_dir(self) -> Path:
        log_dir = self.get('logging.directory', 'logs')
        if os.path.isabs(log_dir):
            return Path(log_dir)
        return get_user_logs_dir()

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    @property
    def raw(self) -> Dict[str, Any]:
        return dict(self._config)


config = Config()
