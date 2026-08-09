"""
PIA pilot contracts and guarded execution surface.

The PIA pilot is deliberately narrow: it proves authenticated formation,
condition-blind state access, Host A -> Host B continuity import, typed route
distributions, and guarded receipt validation for a bounded pilot assay.  It
does not claim production-grade model portability or durable identity.
"""

from .pilot import (
    DEFAULT_ROUTE_VOCABULARY,
    BlindedFixture,
    ConditionBlindStateAccessController,
    ContinuityBundle,
    ContradictionObservation,
    DeterministicPilotHost,
    FormationAuthority,
    FormationService,
    GrokCliModelHost,
    HostStateStore,
    PIAValidationError,
    PIAGuardedExecutor,
    PIARunReceipt,
    RouteSupport,
    TypedRouteDistribution,
    commit_blinded_fixture,
    verify_fixture_steward_record,
    validate_formed_history,
    validate_host_import_receipt,
    validate_pia_run_receipt,
    validate_typed_route_distribution,
)

__all__ = [
    "DEFAULT_ROUTE_VOCABULARY",
    "BlindedFixture",
    "ConditionBlindStateAccessController",
    "ContinuityBundle",
    "ContradictionObservation",
    "DeterministicPilotHost",
    "FormationAuthority",
    "FormationService",
    "GrokCliModelHost",
    "HostStateStore",
    "PIAValidationError",
    "PIAGuardedExecutor",
    "PIARunReceipt",
    "RouteSupport",
    "TypedRouteDistribution",
    "commit_blinded_fixture",
    "verify_fixture_steward_record",
    "validate_formed_history",
    "validate_host_import_receipt",
    "validate_pia_run_receipt",
    "validate_typed_route_distribution",
]
