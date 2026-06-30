from __future__ import annotations

from sirna_offtarget.application.workflow import WorkflowState, execute_workflow
from sirna_offtarget.config import HarnessConfig


def run_analysis(config: HarnessConfig) -> WorkflowState:
    return execute_workflow(config)
