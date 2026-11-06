"""Evidence-aware preventive action recommendations for disaster scenarios.

Recommendations are preparedness options, not forecasts or official instructions.
The engine never estimates risk reduction, ranks actions, or overrides authorities.
"""
from __future__ import annotations

from typing import Any
import hashlib
import re

from src.hazard_registry import WORKFLOW_HAZARDS, components_for


# Each action is deliberately operationally safe and authority-aware. Triggers
# describe when an option is relevant; they are not numerical warning thresholds.
_ACTIONS: dict[str, list[dict[str, str]]] = {
    "Flood": [
        {"phase": "Before the event", "action": "Have authorised teams inspect and maintain drains, culverts and outfalls before the rainy period.", "trigger": "Routine seasonal preparedness; intensify only when local forecasts or inspections indicate concern.", "benefit": "Reduces avoidable blockage-related drainage problems; does not guarantee flood prevention.", "owner": "Local body / drainage operator", "evidence": "Asset register, inspection logs, work orders and disposal records.", "caution": "Do not enter drains, canals or floodwater. Work must be done by authorised crews under safe conditions."},
        {"phase": "Before the event", "action": "Verify official flood-prone-area maps, shelter locations and accessible evacuation routes.", "trigger": "Preparedness planning, especially where people or critical services may be exposed.", "benefit": "Improves readiness to act on an official evacuation instruction.", "owner": "Local disaster-management authority", "evidence": "Current official hazard maps, shelter capacity, route accessibility and community plans.", "caution": "This application does not verify routes or designate shelters."},
        {"phase": "Before the event", "action": "Organise trained community messengers to relay official flood warnings through locally accessible channels, keeping the warning content and geographic scope unchanged.", "trigger": "Verified gaps exist in warning reach or timely receipt among exposed communities.", "benefit": "Can improve warning reach and lead time so households have more opportunity to take locally appropriate protective action; effectiveness depends on context.", "owner": "Local disaster-management authority / trained community organisations", "evidence": "Official warning records, messenger training and delivery logs, household receipt/timing surveys, and post-flood outcome evaluation.", "caution": "Messengers must relay authorised warnings rather than create or modify forecasts; this intervention has evidence from a Bihar trial but its effects must not be assumed to transfer unchanged to Kochi."},
        {"phase": "Before the event", "action": "Prepare household and facility continuity kits; protect essential documents, medicines and critical records from water.", "trigger": "General flood preparedness.", "benefit": "Can reduce avoidable disruption to households and essential services.", "owner": "Households / facility managers", "evidence": "Facility continuity plan and locally recommended emergency-supply checklist.", "caution": "Follow local public-health and disaster-management guidance."},
        {"phase": "When an official warning is issued", "action": "Move people and essential movable equipment away from areas identified by authorities as exposed; evacuate when instructed.", "trigger": "Official warning or evacuation direction for the specific locality.", "benefit": "Reduces exposure when evacuation or relocation is advised.", "owner": "Residents / facility managers / local authorities", "evidence": "Official warning, local evacuation plan and verified exposure information.", "caution": "Never walk, swim or drive through floodwater; do not delay an official evacuation order."},
        {"phase": "During the event", "action": "Keep away from floodwater, fast-flowing channels, submerged roads and fallen electrical lines; use official updates.", "trigger": "Flooding or inundation is occurring or reported nearby.", "benefit": "Reduces risks from currents, hidden hazards, contamination and electricity.", "owner": "Everyone; emergency services for response", "evidence": "Official public-safety instructions and verified local alerts.", "caution": "Do not attempt rescues in moving water; contact emergency services."},
        {"phase": "After the event", "action": "Return only after the relevant authority confirms it is safe; have damaged buildings and electrical systems checked by qualified personnel.", "trigger": "Floodwater has receded but the area has not yet been officially cleared.", "benefit": "Reduces exposure to structural, electrical and contamination hazards.", "owner": "Residents / building owners / utility operators", "evidence": "Official all-clear, structural inspection and utility safety clearance.", "caution": "Avoid contact with contaminated water and do not energise wet electrical equipment."},
    ],
    "Cyclone": [
        {"phase": "Before the event", "action": "Secure or store loose outdoor objects and arrange qualified inspection of roofs, shutters, signage and other vulnerable structures.", "trigger": "Seasonal preparedness; complete outdoor work before hazardous winds begin.", "benefit": "Can reduce wind-borne debris and avoidable structural damage.", "owner": "Property owners / facility managers / qualified contractors", "evidence": "Building inspection, asset register and maintenance records.", "caution": "Do not climb roofs or work at height during strong winds or unsafe weather."},
        {"phase": "Before the event", "action": "Confirm official shelter information, evacuation arrangements, backup communications and contact lists.", "trigger": "Preparedness planning and before any forecast impact period.", "benefit": "Improves coordination and readiness if normal services are disrupted.", "owner": "Local authorities / facility managers", "evidence": "Current official shelter list, tested contact tree and continuity plan.", "caution": "Use only shelters and routes identified by the competent authority."},
        {"phase": "When an official warning is issued", "action": "Follow the official warning level and local evacuation instructions; complete relocation before conditions deteriorate.", "trigger": "IMD / disaster-management authority warning applicable to the area.", "benefit": "Reduces exposure to dangerous wind, coastal and rainfall conditions.", "owner": "Residents / local authorities / facility managers", "evidence": "Official bulletin with issue time, valid period and geographic area.", "caution": "Do not infer safety from a model output in this application."},
        {"phase": "During the event", "action": "Remain in a sturdy sheltered location away from windows; avoid unnecessary travel and outdoor work.", "trigger": "Hazardous winds or official shelter-in-place advice.", "benefit": "Reduces exposure to debris and dangerous outdoor conditions.", "owner": "Residents / facility managers", "evidence": "Official local safety instructions.", "caution": "Follow evacuation instructions if authorities direct evacuation; do not go outside during a lull unless officially cleared."},
        {"phase": "After the event", "action": "Wait for the official all-clear; avoid fallen wires and damaged structures and report hazards to the responsible services.", "trigger": "Winds have eased but damage and utility hazards may remain.", "benefit": "Reduces secondary injuries and speeds safe reporting of hazards.", "owner": "Residents / utility operators / local authorities", "evidence": "Official all-clear and utility/building inspections.", "caution": "Never touch downed power lines."},
    ],
    "Heavy rainfall": [
        {"phase": "Before the event", "action": "Check official rainfall bulletins, station identity, accumulation period and issue/valid times; compare like-for-like observations.", "trigger": "A rainfall observation or forecast is entered or a heavy-rain bulletin is issued.", "benefit": "Prevents decisions based on mismatched units, periods or stale information.", "owner": "Analyst / local disaster-management authority", "evidence": "Official IMD bulletin or quality-controlled gauge record.", "caution": "A rainfall estimate alone is not a flood forecast."},
        {"phase": "Before the event", "action": "Ask authorised teams to inspect known drainage bottlenecks and maintain safe access to critical facilities.", "trigger": "Seasonal maintenance or official heavy-rain outlook.", "benefit": "Can reduce avoidable local drainage and access disruption.", "owner": "Local body / road and drainage operators", "evidence": "Verified bottleneck inventory and maintenance logs.", "caution": "Do not conduct drain or road work during unsafe weather."},
        {"phase": "During the event", "action": "Avoid low-lying crossings and waterlogged roads; follow local closures and official alerts.", "trigger": "Heavy rainfall, waterlogging or road-closure notice.", "benefit": "Reduces exposure to rapidly changing road and drainage conditions.", "owner": "Road users / traffic and local authorities", "evidence": "Official closure and warning information.", "caution": "Never cross moving or standing floodwater."},
    ],
    "Drainage failure": [
        {"phase": "Before the event", "action": "Inspect reported drainage failures through authorised crews and record the exact asset, condition and repair status.", "trigger": "A blockage, partial impairment or failure is reported.", "benefit": "Turns an unverified report into a traceable maintenance task.", "owner": "Drainage operator / local body", "evidence": "Asset ID, geotagged inspection, work order and completion record.", "caution": "No entry into confined spaces or drains without authorised specialist procedures."},
        {"phase": "Before the event", "action": "Review catchment flow paths and drainage capacity with a qualified engineer before proposing upgrades.", "trigger": "Repeated flooding or a documented capacity concern.", "benefit": "Supports properly designed long-term improvements.", "owner": "Local body / qualified drainage engineer", "evidence": "Survey, hydraulic analysis, design review and maintenance plan.", "caution": "Do not infer capacity or design dimensions from this scenario tool."},
    ],
    "Earthquake": [
        {"phase": "Before the event", "action": "Arrange qualified structural screening of critical buildings and prioritise professionally designed retrofits where required.", "trigger": "Routine resilience planning, especially for critical facilities and older structures.", "benefit": "Identifies structural vulnerabilities for engineering action.", "owner": "Building owner / qualified structural engineer / authority", "evidence": "Building inventory, structural drawings and signed engineering assessment.", "caution": "This app cannot certify a building as safe or prescribe structural modifications."},
        {"phase": "Before the event", "action": "Secure heavy furniture and equipment and practise the locally recommended drop, cover and hold-on procedure.", "trigger": "General earthquake preparedness.", "benefit": "Can reduce injuries from falling objects and improve response readiness.", "owner": "Households / schools / facility managers", "evidence": "Facility safety checklist and documented drills.", "caution": "Follow recognised local emergency guidance."},
        {"phase": "During the event", "action": "During shaking, follow recognised public-safety guidance such as drop, cover and hold on; protect yourself from falling objects and do not rush onto stairs or outside.", "trigger": "Ground shaking is occurring.", "benefit": "Reduces exposure to falling objects and unsafe movement during shaking.", "owner": "People in buildings / facility safety teams", "evidence": "Recognised national or local earthquake-safety guidance and facility drills.", "caution": "Follow instructions from emergency authorities; this app does not provide building-specific shelter advice."},
        {"phase": "After shaking", "action": "Move away from visibly damaged structures and report suspected gas, electrical or structural hazards to emergency services or operators.", "trigger": "An earthquake has been felt or damage is reported.", "benefit": "Reduces exposure to after-event hazards.", "owner": "Residents / emergency services / utility operators", "evidence": "Official incident information and qualified inspection.", "caution": "Do not re-enter damaged buildings until cleared by competent authorities."}
    ],
    "Landslide": [
        {"phase": "Before the event", "action": "Have a qualified geotechnical team inspect known unstable slopes, retaining structures and drainage concerns.", "trigger": "Official landslide advisory, documented slope concern or routine risk-reduction planning.", "benefit": "Supports early identification and professional management of slope hazards.", "owner": "Landowner / local authority / geotechnical engineer", "evidence": "Official hazard mapping, field inspection and geotechnical report.", "caution": "Do not approach an actively moving slope or attempt informal slope repairs."},
        {"phase": "When an official warning is issued", "action": "Follow local evacuation instructions and keep people away from slopes, runout areas and closed roads.", "trigger": "Official landslide warning or evacuation direction.", "benefit": "Reduces exposure to slope failure and debris movement.", "owner": "Residents / local authorities", "evidence": "Official warning, mapped exclusion area and evacuation plan.", "caution": "Do not return until authorities declare the area safe."},
        {"phase": "During the event", "action": "If slope movement is observed or an official warning is issued, move away from the slope and mapped runout area and follow the local authority's evacuation direction.", "trigger": "Observed movement, a landslide event or an applicable official warning.", "benefit": "Reduces exposure to moving ground and debris.", "owner": "Residents / local authorities / emergency services", "evidence": "Official warning, field observations and locally approved evacuation plan.", "caution": "Do not approach, cross or investigate a moving slope or debris path."},
        {"phase": "After the event", "action": "Keep access restricted until the slope and nearby structures are assessed by qualified personnel.", "trigger": "A landslide has occurred or new cracks/movement are reported.", "benefit": "Reduces exposure to secondary movement and unstable ground.", "owner": "Local authority / geotechnical team", "evidence": "Site inspection and official clearance.", "caution": "Do not enter the runout area to retrieve belongings."}
    ],
    "Heatwave": [
        {"phase": "Before the event", "action": "Prepare a heat-health plan with drinking-water access, shaded or cooled spaces, outreach and continuity for health services.", "trigger": "Seasonal preparedness or official heat outlook.", "benefit": "Improves readiness to protect people at higher exposure and maintain essential care.", "owner": "Health department / local authority / facility managers", "evidence": "Official heat-health plan, service capacity and outreach records.", "caution": "Use official health advice; this app does not assess individual medical risk."},
        {"phase": "When an official warning is issued", "action": "Share official heat guidance and adjust outdoor work or school activities according to local authority instructions.", "trigger": "Official heat alert applicable to the area.", "benefit": "Can reduce avoidable heat exposure.", "owner": "Employers / schools / local authorities", "evidence": "Official alert and occupational/education safety policy.", "caution": "Do not use this app's temperature estimate as an official heat warning."},
        {"phase": "During the event", "action": "Ensure access to drinking water and cooler spaces and check on people who may need assistance.", "trigger": "Hot conditions or official heat advisory.", "benefit": "Supports basic heat-risk reduction and continuity of care.", "owner": "Households / community organisations / health services", "evidence": "Local health guidance and facility readiness checks.", "caution": "Seek medical help for suspected heat illness."},
        {"phase": "After the event", "action": "Continue health-service follow-up for people affected by heat and review cooling, water and power service interruptions before closing the response.", "trigger": "The official heat alert has ended or conditions have eased.", "benefit": "Supports continuity of care and documents service gaps for the next hot period.", "owner": "Health services / local authorities / facility managers", "evidence": "Health-service records, official alert timeline and utility continuity logs.", "caution": "An ended alert does not mean every person or facility has recovered; follow public-health advice."}
    ],
    "Drought": [
        {"phase": "Before the event", "action": "Track official reservoir, groundwater and water-supply information and agree staged demand-management actions with the responsible utility.", "trigger": "Seasonal water planning or official drought/water-shortage advisory.", "benefit": "Supports earlier, coordinated water planning.", "owner": "Water utility / local authority", "evidence": "Verified storage, inflow, demand and supply records.", "caution": "Rainfall deficit alone does not establish local water shortage."},
        {"phase": "Before the event", "action": "Prepare continuity plans for drinking water, hospitals, schools and other essential services.", "trigger": "Water-supply vulnerability identified by the responsible utility.", "benefit": "Helps maintain essential services during supply constraints.", "owner": "Utilities / facility managers", "evidence": "Verified demand, storage, replenishment and backup arrangements.", "caution": "Any water restrictions must come from the competent authority."},
        {"phase": "During the event", "action": "Follow official water-supply advisories and restrictions, use approved distribution points where provided, and report service interruptions to the responsible utility.", "trigger": "A verified water-shortage or drought advisory applies to the area.", "benefit": "Supports coordinated demand management and access to essential water services.", "owner": "Residents / water utility / local authority", "evidence": "Official supply schedule, quality advisories, storage and distribution records.", "caution": "Do not assume untreated or alternate-source water is safe; follow public-health and utility guidance."},
        {"phase": "After the event", "action": "Confirm restoration and water quality through the responsible utility and review source, storage and demand records before ending contingency measures.", "trigger": "Supply conditions improve or an official shortage advisory is withdrawn.", "benefit": "Supports safe service restoration and improves future water-continuity planning.", "owner": "Water utility / public-health authority / facility managers", "evidence": "Official restoration notice, water-quality results and service logs.", "caution": "Do not independently declare water safe or end official restrictions."}
    ],
    "Industrial incident": [
        {"phase": "Before the event", "action": "Maintain facility-specific prevention, monitoring, notification and emergency-response plans with trained responsible personnel.", "trigger": "Routine industrial safety management and regulatory review.", "benefit": "Improves readiness to detect, report and coordinate an incident.", "owner": "Facility operator / regulator / emergency services", "evidence": "Approved safety case, inspection records, monitoring logs and drill reports.", "caution": "Do not infer a release or identify a polluting source from AQI alone."},
        {"phase": "When an official alert is issued", "action": "Follow facility and public-authority instructions for sheltering, evacuation or access restrictions.", "trigger": "Verified incident notification or official protective-action instruction.", "benefit": "Reduces exposure by aligning actions with pollutant- and site-specific advice.", "owner": "Facility operator / public-health and emergency authorities", "evidence": "Verified incident details and official protective-action notice.", "caution": "Do not approach a suspected release or attempt unauthorised containment."},
        {"phase": "During the event", "action": "Move away from the reported incident area and follow the competent authority's sheltering, evacuation and access-control instructions; report observations through official channels.", "trigger": "A verified industrial incident or official protective-action instruction is in effect.", "benefit": "Reduces exposure while keeping response decisions with trained incident commanders and public authorities.", "owner": "Public / facility operator / emergency services", "evidence": "Official incident notice, monitoring updates and emergency-service instructions.", "caution": "Do not approach, sample, handle or attempt to contain an unknown substance; do not infer a safe distance from this app."},
        {"phase": "After the event", "action": "Return to affected facilities or neighbourhoods only after official clearance and follow published environmental and public-health monitoring advice.", "trigger": "The incident is reported as controlled but access or contamination status has not been cleared.", "benefit": "Reduces exposure to residual hazards and supports documented recovery.", "owner": "Public authorities / facility operator / public-health teams", "evidence": "Official all-clear, monitoring results and site inspection records.", "caution": "Do not treat absence of visible signs or odour as proof that an area is safe."}
    ],
    "Infrastructure failure": [
        {"phase": "Before the event", "action": "Maintain an asset-condition register and inspect critical bridges, power, water and communication dependencies through qualified operators.", "trigger": "Routine maintenance or a documented condition concern.", "benefit": "Helps identify maintenance and continuity gaps before service failure.", "owner": "Asset owner / utility operator", "evidence": "Asset IDs, inspection records, condition ratings and maintenance history.", "caution": "This app does not certify structural or electrical safety."},
        {"phase": "Before the event", "action": "Test backup power, communications, water and service-continuity arrangements for critical facilities.", "trigger": "Routine continuity testing or an approaching hazard that may disrupt utilities.", "benefit": "Can reduce service interruption when primary systems fail.", "owner": "Facility managers / utility operators", "evidence": "Test logs, backup duration and maintenance records.", "caution": "Testing and switching must be performed by authorised personnel."},
        {"phase": "During the event", "action": "Use operator-approved continuity procedures and official service updates; keep people away from damaged assets and report outages through the responsible operator.", "trigger": "A critical asset failure or service outage is confirmed or officially reported.", "benefit": "Supports safer continuity and coordinated restoration without unsafe contact with damaged infrastructure.", "owner": "Utility / asset operator / facility manager", "evidence": "Incident ticket, outage footprint, operator instructions and backup-service logs.", "caution": "Do not inspect, operate, isolate or repair electrical, structural or utility equipment unless authorised and qualified."},
        {"phase": "After the event", "action": "Restore service only after the responsible operator completes inspection and authorises return to service; record outage duration and affected dependencies.", "trigger": "The immediate failure is contained and restoration is being considered.", "benefit": "Supports safe restoration and creates evidence for future reliability improvements.", "owner": "Asset owner / utility operator / facility manager", "evidence": "Inspection clearance, repair record, restoration timestamp and service-quality checks.", "caution": "Do not independently energise or reopen damaged infrastructure."}
    ],
}

_COMPOUND_ACTIONS: dict[str, list[dict[str, str]]] = {
    "Compound: cyclone + flood": [
        {"phase": "Before the event", "action": "Coordinate cyclone, rainfall, river and coastal-water monitoring in one incident timeline, preserving each source's issue time, valid time and location.", "trigger": "Cyclone and flood are selected together or an official cyclone bulletin overlaps a local flood concern.", "benefit": "Helps responders see timing and dependencies without treating separate indicators as a validated joint probability.", "owner": "District emergency operations / relevant data providers", "evidence": "Time-aligned official IMD bulletins, CWC or gauge records, coastal observations and source metadata.", "caution": "Concurrent signals do not establish a compound forecast; no synthetic combined threshold is used."},
        {"phase": "Before the event", "action": "Review continuity arrangements for hospitals, power, drinking water, communications and access routes against both wind and flood disruption pathways.", "trigger": "Critical services are nominated or the official forecast indicates possible multi-hazard disruption.", "benefit": "Identifies single points of failure and backup needs across connected services.", "owner": "District authority / facility and utility operators", "evidence": "Verified asset locations, dependency map, backup duration, facility plans and official hazard footprint.", "caution": "This workspace does not verify which facilities are inside a hazard footprint."},
        {"phase": "When an official warning is issued", "action": "Use the district's official evacuation and shelter plan; check that the designated route is not closed or affected by flooding before movement.", "trigger": "An official evacuation instruction applies to the locality.", "benefit": "Reduces the chance of moving people onto a route affected by another hazard component.", "owner": "Local authorities / residents following official directions", "evidence": "Official evacuation instruction, live route closures and verified shelter status.", "caution": "Never enter floodwater or use a closed route; follow emergency services if routes change."},
    ],
    "Compound: heavy rainfall + drainage failure": [
        {"phase": "Before the event", "action": "Have the drainage operator verify the reported asset failure, inspect upstream/downstream connections and record whether a safe repair or temporary service measure is feasible before rainfall.", "trigger": "A drainage failure is reported alongside a heavy-rainfall scenario.", "benefit": "Connects the rainfall forcing concern to a specific, verifiable maintenance response.", "owner": "Drainage operator / local body", "evidence": "Asset ID, field inspection, catchment context, work order and qualified engineering review.", "caution": "Do not infer local flood depth or capacity from rainfall alone; no one should enter drains or floodwater."},
        {"phase": "Before the event", "action": "Identify critical facilities that depend on the affected drainage catchment and confirm their continuity and access plans.", "trigger": "A drainage asset is reported failed or partially impaired.", "benefit": "Helps identify services that may need contingency arrangements if local waterlogging occurs.", "owner": "Local body / facility managers", "evidence": "Verified drainage network, facility locations, access routes and dependency records.", "caution": "A network connection or facility exposure must be verified; it is not inferred by this tool."},
        {"phase": "During the event", "action": "Follow official road-closure and emergency instructions, keep away from floodwater and failed drainage assets, and report observed waterlogging to the responsible authority.", "trigger": "Heavy rainfall coincides with reported drainage impairment or local waterlogging.", "benefit": "Supports safer movement and timely operator awareness of local disruption.", "owner": "Residents / traffic authority / drainage operator", "evidence": "Official advisories, verified asset location and time-stamped field reports.", "caution": "Never enter drains, culverts or floodwater; do not attempt an unauthorised repair."},
        {"phase": "After the event", "action": "Have the drainage operator document the failure, inspect the affected network and record repair, clearance and maintenance follow-up.", "trigger": "Rainfall or waterlogging has eased and the affected drainage asset requires post-event review.", "benefit": "Creates a traceable recovery and maintenance record for future risk reduction.", "owner": "Drainage operator / local body", "evidence": "Asset inspection, work order, completion record and post-event performance observations.", "caution": "Only authorised crews should inspect or repair drainage infrastructure."}
    ],
}

_COMMON: list[dict[str, str]] = [
    {"phase": "Before the event", "action": "Keep an updated contact tree, accessible emergency information and a facility/community continuity plan.", "trigger": "General preparedness for every hazard.", "benefit": "Improves coordination when normal communications or services are disrupted.", "owner": "Households / institutions / local authorities", "evidence": "Named responsible persons, tested contacts and current plans.", "caution": "Use current official emergency contacts and instructions."},
]


def generate_prevention_actions(
    hazards: list[str] | tuple[str, ...] | str,
    inputs: dict[str, Any] | None = None,
    *,
    custom_disaster: str = "",
) -> list[dict[str, str]]:
    """Return hazard-specific, non-ranked actions with explicit triggers and caveats."""
    if isinstance(hazards, str):
        selected = [hazards]
    else:
        selected = list(hazards or [])
    context = inputs or {}
    valid = [hazard for hazard in selected if hazard in WORKFLOW_HAZARDS]
    components: list[str] = []
    for hazard in valid:
        for component in components_for(hazard):
            if component not in components:
                components.append(component)

    actions: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in _COMMON:
        actions.append({**item, "hazard": "All selected hazards", "activation_basis": "General preparedness"})
    for component in components:
        for item in _ACTIONS.get(component, []):
            key = (item["phase"], item["action"])
            if key in seen:
                continue
            seen.add(key)
            actions.append({**item, "hazard": component, "activation_basis": item["trigger"]})

    for hazard in valid:
        for item in _COMPOUND_ACTIONS.get(hazard, []):
            key = (item["phase"], item["action"])
            if key in seen:
                continue
            seen.add(key)
            actions.append({**item, "hazard": hazard, "activation_basis": item["trigger"]})

    # Context only narrows relevance; user-entered measurements are never treated
    # as authenticated observations or converted into warning thresholds.
    classification = str(context.get("input_classification") or context.get("evidence_type") or "Unknown / unverified")
    if context.get("rainfall_mm") not in (None, ""):
        actions.append({
            "hazard": "Heavy rainfall / flood evidence", "phase": "Verify evidence",
            "action": "Verify the rainfall source, station, units, accumulation period, issue time and valid time before using it in a decision.",
            "trigger": "A rainfall value was entered into this scenario.",
            "benefit": "Reduces decisions based on stale, mismatched or unverified rainfall information.",
            "owner": "Analyst / responsible data provider",
            "evidence": "Original official bulletin or quality-controlled gauge record with metadata.",
            "caution": f"Input classification: {classification}. Entry in this app does not authenticate the value.",
            "activation_basis": "User-entered rainfall value; verification required",
        })
    if context.get("river_level_m") not in (None, ""):
        actions.append({
            "hazard": "Flood evidence", "phase": "Verify evidence",
            "action": "Confirm the river gauge identity, timestamp, units and datum; compare only with an official threshold for that same gauge and reference.",
            "trigger": "A river-level value was entered.",
            "benefit": "Prevents invalid comparisons between different gauges or vertical references.",
            "owner": "Hydrology analyst / gauge operator",
            "evidence": "Gauge metadata, official station record and documented threshold.",
            "caution": "No river-level threshold is inferred by this application.",
            "activation_basis": "User-entered river level; metadata verification required",
        })
    drainage = str(context.get("drainage_status", "")).casefold()
    if any(word in drainage for word in ("impaired", "failed", "partial")):
        actions.append({
            "hazard": "Drainage failure", "phase": "Before the event",
            "action": "Refer the reported drainage impairment to the responsible operator for inspection, safe maintenance and a recorded repair decision.",
            "trigger": f"User-described drainage status: {context.get('drainage_status')}.",
            "benefit": "Creates a traceable response to a reported vulnerability without assuming its extent.",
            "owner": "Drainage operator / local body",
            "evidence": "Verified asset location, inspection record and work-order status.",
            "caution": "The reported status is not independently verified; no one should enter drains or floodwater.",
            "activation_basis": "User-reported drainage concern; verify locally",
        })
    for service in context.get("services", context.get("assets", [])) or []:
        service = str(service)
        if service not in {"Hospitals", "Electricity", "Drinking water", "Communications", "Roads and bridges", "Shelters", "Schools", "Drainage", "Industrial facilities"}:
            continue
        actions.append({
            "hazard": "Critical-service continuity", "phase": "Before the event",
            "action": f"Review the continuity plan and backup arrangements for {service.lower()} with its responsible operator.",
            "trigger": f"{service} was nominated for review; actual exposure and service condition are not verified.",
            "benefit": "Identifies dependencies and preparedness gaps that could prolong service disruption.",
            "owner": "Responsible {service} operator / facility manager".format(service=service.lower()),
            "evidence": "Verified asset location, dependency map, backup duration, maintenance and exercise records.",
            "caution": "Nomination does not establish that this service is exposed or likely to fail.",
            "activation_basis": "User-nominated critical service; exposure verification required",
        })

    if custom_disaster.strip() or not valid:
        actions.append({
            "hazard": "Unregistered / custom scenario", "phase": "Before the event",
            "action": "Obtain a hazard-specific assessment from the competent authority or qualified specialist before selecting technical precautions.",
            "trigger": "The scenario includes an unregistered or unsupported hazard.",
            "benefit": "Avoids applying an unrelated hazard checklist to a different threat.",
            "owner": "Competent disaster-management authority / domain specialist",
            "evidence": "Hazard definition, official guidance, location-specific exposure and approved response plan.",
            "caution": "No hazard-specific model or tailored precaution is inferred for an unregistered scenario.",
            "activation_basis": "Custom scenario; specialist review required",
        })
    # Stable action identifiers link the catalogue to intervention outcome records.
    # The readable action text remains the display label; IDs change only if the
    # hazard or intervention definition itself changes.
    for item in actions:
        hazard_key = re.sub(r"[^a-z0-9]+", "-", item["hazard"].casefold()).strip("-")
        action_key = hashlib.sha1(item["action"].encode("utf-8")).hexdigest()[:10]
        item["action_id"] = f"{hazard_key}:{action_key}"
    return actions


__all__ = ["generate_prevention_actions"]
