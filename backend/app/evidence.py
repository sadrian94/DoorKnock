from pathlib import Path
from .clock import utc_now
from typing import Dict, Any, Optional
import yaml
from .config import DOORKNOCK_MASTER_EVIDENCE_YAML_PATH

def load_master_evidence() -> Optional[Dict[str, Any]]:
    """Load structured candidate evidence bank from YAML."""
    if DOORKNOCK_MASTER_EVIDENCE_YAML_PATH.exists():
        try:
            data = yaml.safe_load(DOORKNOCK_MASTER_EVIDENCE_YAML_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None

def format_evidence_for_prompt(evidence: Dict[str, Any]) -> str:
    """Serialize the full structured evidence record without dropping YAML fields."""
    return yaml.safe_dump(evidence, allow_unicode=True, sort_keys=False).strip()

def get_candidate_master_context() -> str:
    """
    Retrieve candidate master context from the YAML evidence bank only.
    """
    evidence = load_master_evidence()
    if evidence:
        return format_evidence_for_prompt(evidence)
    return ""

def backup_master_evidence() -> Optional[Path]:
    """Create a timestamped backup of master_evidence.yaml before editing."""
    if not DOORKNOCK_MASTER_EVIDENCE_YAML_PATH.exists():
        return None
    timestamp = utc_now().strftime("%Y%m%d_%H%M%S_%fZ")
    backup_path = DOORKNOCK_MASTER_EVIDENCE_YAML_PATH.parent / f"master_evidence.{timestamp}.yaml.bak"
    backup_path.write_text(DOORKNOCK_MASTER_EVIDENCE_YAML_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path
