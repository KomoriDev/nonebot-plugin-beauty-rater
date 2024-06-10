from pathlib import Path

from pydantic import BaseModel
from nonebot import get_plugin_config

font_path: Path = Path(__file__).parent / "resources" / "fonts" / "simyou.ttf"


class ScopedConfig(BaseModel):

    # 基础配置
    api_key: str = ""
    secret_key: str = ""
    timeout: int = 30


class Config(BaseModel):
    rate: ScopedConfig = ScopedConfig()
    """Beauty Rater Config"""


config = get_plugin_config(Config).rate
