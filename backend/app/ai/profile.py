def get_candidate_profile_context() -> str:
    """
    Load candidate profile strictly from local uncommitted workspace files to protect PII.
    Primary: DoorKnock/workspace/master_resume/master_evidence.yaml
    """
    from ..evidence import get_candidate_master_context
    ctx = get_candidate_master_context()
    if ctx and len(ctx.strip()) > 50:
        return ctx

    raise ValueError("Candidate master evidence is missing or invalid: workspace/master_resume/master_evidence.yaml")

