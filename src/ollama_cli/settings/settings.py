import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provider:
    default: str = ""
    enabled: bool = False
    api_key: str | None = None
    base_url: str | None = None
    available_models: list[str] = field(default_factory=list)
    default_model: str = ""
    default_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    default: str | None = None
    git_enabled: bool = True
    agent_mod: bool = True
    providers: dict[str, Provider] = field(default_factory=dict)


def load_user_settings() -> Settings | None:
    cwd: str = os.getcwd()
    settings_path: str = os.path.join(cwd, ".ocli", "settings.json")

    if not os.path.exists(settings_path):
        return None

    try:
        with open(settings_path, encoding='utf-8') as f:
            settings_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Extract providers data
    providers = {}
    if "providers" in settings_data:
        for name, provider_data in settings_data["providers"].items():
            providers[name] = Provider(
                default=provider_data.get("default", ""),
                enabled=provider_data.get("enabled", False),
                api_key=provider_data.get("api_key"),
                base_url=provider_data.get("base_url"),
                available_models=provider_data.get("available_models", []),
                default_model=provider_data.get("default_model", ""),
                default_parameters=provider_data.get("default_parameters", {})
            )

    # Extract features data
    features = settings_data.get("features", {})

    # Create Settings instance
    settings = Settings(
        default=settings_data.get("default"),
        git_enabled=features.get("git_enabled", True),
        agent_mod=features.get("agent_mod", True),
        providers=providers
    )

    return settings
