"""A small, deterministic framework for end-to-end capability runs."""

from .demos import build_demo_registry, demo_domains, demo_input
from .environment import read_env_file, resolve_settings
from .models import ForgeSettings, RunContext, Target
from .orchestrator import Orchestrator, RunOutcome
from .registry import Capability, CapabilityRegistry
from .validation import ValidationError, ValidationIssue, ValidationLayer
from .version import __version__

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "ForgeSettings",
    "Orchestrator",
    "RunContext",
    "RunOutcome",
    "Target",
    "ValidationError",
    "ValidationIssue",
    "ValidationLayer",
    "__version__",
    "build_demo_registry",
    "demo_domains",
    "demo_input",
    "read_env_file",
    "resolve_settings",
]
