"""Minimal localhost-only Control Room page."""
from __future__ import annotations
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from string import Template
from .observation import build_record
from .observer import ContainerObserver, ObservationError
from .receipt import generate_receipt
from .comparison import ComparisonReceipt, ComparisonResult, generate_comparison_receipt
from .retention import RetainedObservations
from .transition import TransitionEvidence, TransitionResult, receipt as transition_receipt

TEMPLATE = Template((Path(__file__).resolve().parents[2] / "web" / "index.html").read_text(encoding="utf-8"))
def _display(value: object) -> tuple[str, str]:
    if value is None or value == "": return "Unavailable", "unavailable"
    if isinstance(value, bool): return ("Running" if value else "Stopped"), "observed"
    return str(value), "observed"
def render_observation(observer: ContainerObserver, subject: str) -> str:
    try:
        raw = observer.inspect_one(subject)
        record = build_record(subject, raw, observer.source_interface, observer.source_command(subject))
        receipt = generate_receipt(record)
        fields = record.canonical_fields
        values = {"observer_status": ("Connected", "derived"), "container_name": _display(fields.container_name), "container_id": _display(fields.container_id), "configured_image": _display(fields.configured_image), "resolved_image": _display(fields.resolved_image), "state": _display(fields.state), "running": _display(fields.running), "created_at": _display(fields.created_at), "started_at": _display(fields.started_at), "observed_at": (record.observed_at, "retained"), "receipt_id": (receipt.receipt_id, "retained"), "source_interface": (record.source_interface, "observed"), "source_command": (record.source_command, "observed")}
        receipt_json = json.dumps(asdict(receipt), indent=2, sort_keys=True)
        cards = "".join(f'<article><span class="kind {escape(kind)}">{escape(kind)}</span><h3>{escape(label)}</h3><p>{escape(value)}</p></article>' for label, (value, kind) in ((key.replace("_", " ").title(), item) for key, item in values.items()))
        return TEMPLATE.safe_substitute(subject=escape(subject), cards=cards, receipt=escape(receipt_json), error="")
    except ObservationError as exc:
        error = f'<section class="error"><span class="kind derived">derived</span><h2>Observer unavailable</h2><p>{escape(str(exc))}</p></section>'
        return TEMPLATE.safe_substitute(subject=escape(subject), cards="", receipt="Unavailable — no observation receipt was created.", error=error)

def render_continuity(document: RetainedObservations, result: ComparisonResult, receipt: ComparisonReceipt | None = None) -> str:
    receipt = receipt or generate_comparison_receipt(document, result)
    cards = [
        ("Subject Selector", document.subject_selector, "operator-entered"),
        ("Retained Observation Count", str(len(result.ordered_observations)), "derived"),
        ("Identity Classification", result.classification, "classification"),
        ("Classification Reason", result.reason or "Unavailable", "unavailable" if result.reason is None else "classification"),
        ("Comparison Receipt ID", receipt.receipt_id, "retained"),
    ]
    for item in result.ordered_observations:
        cards.extend([(f"Observation {item.observation_index} Index", str(item.observation_index), "retained"), (f"Observation {item.observation_index} Container ID", item.container_id or "Unavailable", "unavailable" if item.container_id is None else "observed"), (f"Observation {item.observation_index} Receipt ID", item.observation_receipt_id, "retained"), (f"Observation {item.observation_index} Time", item.observed_at, "retained"), (f"Observation {item.observation_index} Source", item.source_interface, "observed")])
    rendered_cards = "".join(f'<article><span class="kind {escape(kind)}">{escape(kind)}</span><h3>{escape(label)}</h3><p>{escape(value)}</p></article>' for label, value, kind in cards)
    receipt_json = json.dumps(receipt.digest_input, indent=2, sort_keys=True)
    return TEMPLATE.safe_substitute(subject=escape(document.subject_selector), cards=rendered_cards, receipt=escape(receipt_json), error="")

def render_human_continuity(document: RetainedObservations, result: ComparisonResult, receipt: ComparisonReceipt | None = None) -> str:
    receipt = receipt or generate_comparison_receipt(document, result)
    item = result.ordered_observations[-1] if result.ordered_observations else None
    same = result.classification == "SAME_SUBJECT"
    title = "Same container confirmed" if same else "Not enough evidence"
    summary = "Bolt-On looked at this real container twice. The full identity matched both times. Bolt-On only observed it and made no changes." if same else "Bolt-On could not safely confirm that the observations referred to the same container."
    facts = f'Container: {escape(document.subject_selector)}<br>Image: Not supplied by Docker<br>Latest state: Not supplied by Docker<br>Observations: {len(result.ordered_observations)}<br>Identity result: {"Same container confirmed" if same else "Not enough evidence"}<br>Observation method: Read-only Docker inspection<br>Changes made by Bolt-On: None'
    story = '<ol><li>Bolt-On looked at the container.</li><li>Bolt-On looked at it again.</li><li>The full identity matched.</li><li>Result: It was the same container.</li></ol>' if same else '<ol><li>Bolt-On looked at the container.</li><li>Bolt-On could not safely confirm the result.</li></ol>'
    main=f'<section class="receipt"><h1>{title}</h1><p>{summary}</p><h2>What Bolt-On saw</h2><p>{facts}</p><h2>What happened</h2>{story}<h2>What this proves</h2><p>Bolt-On can look at a real outside system, remember what it saw, and confirm whether a later observation refers to the same subject.</p><p>Bolt-On did not start, stop, restart, pause, remove, or modify the container.</p></section>'
    audit=f'<details><summary>View technical evidence</summary><p>Canonical classification: {escape(result.classification)}. Receipt ID: {escape(receipt.receipt_id)}. Receipt schema: {escape(receipt.schema)}.</p><pre>{escape(json.dumps(receipt.digest_input, indent=2, sort_keys=True))}</pre></details>'
    return TEMPLATE.safe_substitute(subject=escape(document.subject_selector),cards="",receipt="",error=main+audit)

def render_transition(evidence: TransitionEvidence, result: TransitionResult) -> str:
    transition = transition_receipt(evidence, result)
    cards = [("Subject Selector", evidence.subject_selector, "operator-entered"), ("Manual Stop Confirmed", str(evidence.operator_stop_confirmed), "operator-entered"), ("Subject Continuity", "Same full container ID" if result.classification == "SAME_SUBJECT_STOPPED" else "Unavailable", "derived"), ("State Classification", result.classification, "classification"), ("Classification Reason", result.reason or "Unavailable", "unavailable" if result.reason is None else "classification"), ("Transition Receipt ID", transition.receipt_id, "retained")]
    for label, item in (("Earlier", evidence.earlier), ("Later", evidence.later)):
        if item is None: cards.append((f"{label} Observation", "Unavailable", "unavailable")); continue
        fields, retained = item.canonical_fields, item.retained
        cards.extend([(f"{label} Container ID", str(fields.get("container_id") or "Unavailable"), "observed"), (f"{label} State", str(fields.get("state") or "Unavailable"), "observed"), (f"{label} Running", str(fields.get("running")), "observed"), (f"{label} Index", str(retained.observation_index), "retained"), (f"{label} Receipt ID", retained.observation_receipt_id, "retained"), (f"{label} Time", retained.observed_at, "retained")])
    rendered = "".join(f'<article><span class="kind {escape(kind)}">{escape(kind)}</span><h3>{escape(label)}</h3><p>{escape(value)}</p></article>' for label, value, kind in cards)
    return TEMPLATE.safe_substitute(subject=escape(evidence.subject_selector), cards=rendered, receipt=escape(json.dumps(transition.digest_input, indent=2, sort_keys=True)), error="")

def render_stage_four(evidence: TransitionEvidence, result: TransitionResult) -> str:
    receipt = transition_receipt(evidence, result)
    latest = evidence.later or evidence.earlier; fields = latest.canonical_fields
    stopped = result.classification == "SAME_SUBJECT_STOPPED"
    title = "Same container seen after it stopped" if stopped else "Same container confirmed" if result.classification == "SAME_SUBJECT" else "Not enough evidence"
    summary = "Bolt-On first saw this container running. The operator stopped it outside Bolt-On. Bolt-On then saw the same container stopped. Bolt-On detected the change but did not cause it." if stopped else "Bolt-On looked at this real container twice. The full identity matched both times. Bolt-On only observed it and made no changes." if result.classification == "SAME_SUBJECT" else "Bolt-On could not safely confirm that the observations referred to the same container."
    state = "Stopped" if fields.get("running") is False else "Running" if fields.get("running") is True else "Not supplied by Docker"
    identity = "Same container confirmed" if result.classification in {"SAME_SUBJECT","SAME_SUBJECT_STOPPED"} else "Not enough evidence"
    story = "<ol><li>Bolt-On saw the container running.</li><li>The operator stopped it outside Bolt-On.</li><li>Bolt-On looked again.</li><li>The full identity still matched.</li><li>Result: The same container was now stopped.</li></ol>" if stopped else "<ol><li>Bolt-On looked at the container.</li><li>Bolt-On looked at it again.</li><li>The full identity matched.</li><li>Result: It was the same container.</li></ol>"
    main = f'<section class="receipt"><h1>{escape(title)}</h1><p>{escape(summary)}</p><h2>What Bolt-On saw</h2><p>Container: {escape(str(fields.get("container_name") or "Not supplied by Docker"))}<br>Image: {escape(str(fields.get("configured_image") or "Not supplied by Docker"))}<br>Latest state: {state}<br>Observations: 2<br>Identity result: {identity}<br>Observation method: Read-only Docker inspection<br>Changes made by Bolt-On: None</p><h2>What happened</h2>{story}<h2>What this proves</h2><p>Bolt-On can look at a real outside system, remember what it saw, and detect that the same subject later changed state.</p><p>Bolt-On did not start, stop, restart, pause, remove, or modify the container.</p></section>'
    technical = f'<details><summary>View technical evidence</summary><p>Observed: read directly from Docker. Retained: saved from an earlier observation. Derived: calculated from the evidence. Bolt-On classification: conclusion made by fixed rules. Operator-entered: action confirmed by the human operator. Unavailable: not supplied by the evidence source.</p><p>Canonical classification: {escape(result.classification)}. Receipt ID: {escape(receipt.receipt_id)}. Receipt schema: {escape(receipt.schema)}.</p><pre>{escape(json.dumps(receipt.digest_input, indent=2, sort_keys=True))}</pre></details>'
    return TEMPLATE.safe_substitute(subject=escape(evidence.subject_selector), cards="", receipt="", error=main + technical)
    def card(label, value, kind): return (label, "UNAVAILABLE" if value is None else str(value), kind if value is not None else "unavailable")
    earlier, later = evidence.earlier, evidence.later
    latest = later or earlier
    f = latest.canonical_fields
    cards=[card("Observer Connection Status","RETAINED EVIDENCE ONLY","derived"),card("Page Evidence Mode","RETAINED EVIDENCE","retained"),card("Container Name",f.get("container_name"),"observed"),card("Full Container ID",f.get("container_id"),"observed"),card("Image Identity",f.get("configured_image"),"observed"),card("Current Docker State",f.get("state"),"observed"),card("Running Boolean",f.get("running"),"observed"),card("Created At",f.get("created_at"),"observed"),card("Started At",f.get("started_at"),"observed"),card("Restart Count",None,"unavailable"),card("Latest Observation Time",latest.retained.observed_at,"retained"),card("Source Interface",latest.retained.source_interface,"observed"),card("Receipt Identifier",receipt.receipt_id,"retained"),card("Subject Continuity","SAME FULL CONTAINER ID" if result.classification=="SAME_SUBJECT_STOPPED" else None,"derived"),card("Classification",result.classification,"classification"),card("Operator Stop Confirmation",evidence.operator_stop_confirmed,"operator-entered")]
    timeline=[("Observed running",earlier), ("Retained same full ID",later), ("Operator-entered stop confirmation",evidence.operator_stop_confirmed), ("Observed exited / running=false",later), ("Bolt-On classification",result.classification)]
    cards += [(f"Timeline {i+1}: {label}", item.retained.observed_at if hasattr(item,"retained") else item, "retained" if hasattr(item,"retained") else "operator-entered" if isinstance(item,bool) else "classification") for i,(label,item) in enumerate(timeline)]
    rendered="".join(f'<article><span class="kind {escape(kind)}">{escape(kind.upper().replace("CLASSIFICATION","BOLT_ON_CLASSIFICATION").replace("OPERATOR-ENTERED","OPERATOR_ENTERED"))}</span><h3>{escape(label)}</h3><p>{escape(str(value))}</p></article>' for label,value,kind in cards)
    stopped=result.classification=="SAME_SUBJECT_STOPPED"; title="Same container observed after stopping" if stopped else "Same container confirmed"; summary="The operator stopped the container outside Bolt-On. Bolt-On later observed the same full container identity in the stopped state and did not cause the change." if stopped else "Bolt-On observed this real container twice through Docker’s read-only inspection interface. The full container identity matched in both observations. Bolt-On made no changes to the container."
    plain=f'<section class="receipt"><h2>{title}</h2><p>{summary}</p><h2>What Bolt-On saw</h2><p>{escape(str(f.get("container_name") or "Not provided by this observation source"))} using {escape(str(f.get("configured_image") or "Not provided by this observation source"))}; latest state {escape(str(f.get("state") or "Not provided by this observation source"))}; two retained observations from Docker CLI inspect. No action was performed.</p><h2>What this proves</h2><p>Bolt-On can observe a real outside system, retain what it saw, and produce evidence showing whether later observations refer to the same subject. It detected the observed state change.</p><p>Observed means read directly from Docker; retained means stored earlier; derived means calculated; classification is Bolt-On’s bounded conclusion; operator-entered is human confirmation.</p></section>'
    audit=f'<details><summary>View audit evidence</summary><p>Canonical classification: {escape(result.classification)}. Receipt schema: {escape(receipt.schema)}.</p><pre>{escape(json.dumps(receipt.digest_input,indent=2,sort_keys=True))}</pre></details>'
    return TEMPLATE.safe_substitute(subject=escape(evidence.subject_selector),cards=rendered,receipt=escape(receipt.receipt_id),error=plain+audit)
