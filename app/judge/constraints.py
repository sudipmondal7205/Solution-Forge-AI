"""Deterministic hard-constraint checks.

These checks run in Python rather than relying on the LLM.

They compare explicit user requirements against the outputs produced by
the Business Analyst, Solution Architect, Technology Advisor, and
Delivery Planner.

The Judge LLM performs qualitative evaluation separately. These checks
provide objective, reproducible evidence for explicit constraints.
"""

from __future__ import annotations

import re

from ..schemas.agents import DPOutput, SAOutput, TAOutput
from ..schemas.evaluation import HardConstraintCheck


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEEKS_PER_MONTH = 4.33

# Timeline tolerance:
# >15% over target -> FAIL / MAJOR
# >30% over target -> FAIL / CRITICAL
# <50% of target -> WARN / MINOR
TIMELINE_TOLERANCE = 0.15
TIMELINE_SEVERE = 0.30
TIMELINE_UNDERRUN = 0.50


CLOUD_ALIASES = {
    "AWS": [
        "aws",
        "amazon web services",
        "amazon",
    ],
    "Azure": [
        "azure",
        "microsoft azure",
    ],
    "GCP": [
        "gcp",
        "google cloud",
        "google cloud platform",
    ],
}


# Cloud/data-region hints.
# These are deliberately broad because the current TA/SA contracts
# do not require a dedicated "data_region" field.
COUNTRY_REGION_HINTS = {
    "India": [
        "ap-south",
        "mumbai",
        "hyderabad",
        "central india",
        "south india",
        "asia-south",
        "india",
    ],
    "United States": [
        "us-east",
        "us-west",
        "us-central",
        "useast",
        "uswest",
        "virginia",
        "oregon",
        "ohio",
        "iowa",
        "united states",
        "usa",
    ],
    "United Kingdom": [
        "eu-west-2",
        "uk south",
        "uk west",
        "london",
        "europe-west2",
        "united kingdom",
    ],
    "Germany": [
        "eu-central-1",
        "germany",
        "frankfurt",
        "europe-west3",
    ],
    "Ireland": [
        "eu-west-1",
        "ireland",
        "dublin",
        "north europe",
    ],
    "Singapore": [
        "ap-southeast-1",
        "singapore",
        "asia-southeast1",
    ],
    "Australia": [
        "ap-southeast-2",
        "australia",
        "sydney",
        "melbourne",
        "australia-southeast",
    ],
    "Japan": [
        "ap-northeast-1",
        "japan",
        "tokyo",
        "osaka",
        "asia-northeast1",
    ],
    "Canada": [
        "ca-central",
        "canada",
        "toronto",
        "montreal",
        "northamerica-northeast",
    ],
    "Brazil": [
        "sa-east-1",
        "brazil",
        "brazil south",
        "southamerica-east1",
    ],
    "France": [
        "eu-west-3",
        "france",
        "paris",
        "europe-west9",
    ],
    "South Korea": [
        "ap-northeast-2",
        "korea",
        "seoul",
        "asia-northeast3",
    ],
    "United Arab Emirates": [
        "me-central-1",
        "uae",
        "dubai",
        "me-central",
    ],
    "South Africa": [
        "af-south-1",
        "south africa",
        "johannesburg",
    ],
    "Netherlands": [
        "eu-west-4",
        "netherlands",
        "europe-west4",
        "amsterdam",
    ],
    "Switzerland": [
        "eu-central-2",
        "switzerland",
        "zurich",
        "europe-west6",
    ],
    "Indonesia": [
        "ap-southeast-3",
        "indonesia",
        "jakarta",
        "asia-southeast2",
    ],
    "Israel": [
        "il-central-1",
        "israel",
        "israel central",
        "me-west1",
    ],
    "Italy": [
        "italy north",
        "milan",
        "europe-west8",
        "eu-south-1",
    ],
    "Spain": [
        "eu-south-2",
        "spain",
        "spain central",
        "europe-southwest1",
    ],
    "Sweden": [
        "eu-north-1",
        "sweden",
        "stockholm",
        "europe-north1",
    ],
    "Poland": [
        "poland central",
        "warsaw",
        "europe-central2",
    ],
    "Mexico": [
        "mx-central-1",
        "mexico",
        "northamerica-south1",
    ],
    "Qatar": [
        "qatar",
        "qatar central",
        "me-central2",
    ],
    "Saudi Arabia": [
        "saudi",
        "me-south",
        "dammam",
    ],
    "New Zealand": [
        "new zealand",
        "australia-southeast2",
        "auckland",
    ],
    "Norway": [
        "norway east",
        "norway west",
        "europe-north2",
        "oslo",
    ],
    "Turkey": [
        "turkey",
        "istanbul",
    ],
    "Thailand": [
        "ap-southeast-7",
        "thailand",
        "bangkok",
        "asia-southeast3",
    ],
    "Malaysia": [
        "ap-southeast-5",
        "malaysia",
        "kuala lumpur",
    ],
    "Vietnam": [
        "vietnam",
        "hanoi",
        "ho chi minh",
    ],
    "Nigeria": [
        "nigeria",
        "lagos",
    ],
    "Kenya": [
        "kenya",
        "nairobi",
    ],
}


# ---------------------------------------------------------------------------
# Technology classification heuristics
# ---------------------------------------------------------------------------

PROPRIETARY_MARKERS = [
    "oracle database",
    "oracle db",
    "microsoft sql server",
    "mssql",
    "sql server",
    "ibm db2",
    "db2",
    "sap hana",
    "informix",
    "sybase",
    "teradata",
    "splunk",
    "datadog",
    "new relic",
    "dynatrace",
    "appdynamics",
    "mulesoft",
    "tibco",
    "informatica",
    "sas ",
    "matlab",
    "tableau",
    "power bi",
    "salesforce",
    "servicenow",
    "okta",
    "auth0",
    "vmware",
    "red hat openshift",
    "websphere",
    "weblogic",
    "coldfusion",
    ".net framework",
    "mongodb enterprise",
    "confluent platform",
    "elastic enterprise",
]


OPEN_SOURCE_MARKERS = [
    "postgresql",
    "postgres",
    "mysql",
    "mariadb",
    "redis",
    "valkey",
    "sqlite",
    "python",
    "fastapi",
    "django",
    "flask",
    "node.js",
    "nodejs",
    "express",
    "nestjs",
    "react",
    "vue",
    "svelte",
    "angular",
    "next.js",
    "nuxt",
    "docker",
    "kubernetes",
    "k8s",
    "nginx",
    "traefik",
    "rabbitmq",
    "kafka",
    "elasticsearch",
    "opensearch",
    "prometheus",
    "grafana",
    "loki",
    "jaeger",
    "terraform",
    "opentofu",
    "ansible",
    "keycloak",
    "minio",
    "celery",
    "go",
    "golang",
    "rust",
    "java",
    "spring boot",
    "quarkus",
    "laravel",
    "ruby on rails",
    "rails",
    "php",
    "typescript",
    "linux",
    "ubuntu",
    "clickhouse",
    "cassandra",
    "mongodb",
    "neo4j",
    "temporal",
    "nats",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text: str | None) -> str:
    """Normalize text for reliable case-insensitive matching."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _collect_text(*payloads: dict | None) -> str:
    """Flatten nested dictionaries/lists into a normalized text string."""
    parts: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            parts.append(node)
        elif node is not None:
            parts.append(str(node))

    for payload in payloads:
        walk(payload)

    return _norm(" ".join(parts))


# ---------------------------------------------------------------------------
# Cloud provider
# ---------------------------------------------------------------------------

def check_cloud_provider(
    user_input: dict,
    ta: TAOutput,
) -> HardConstraintCheck:

    requested = user_input["cloud_preference"]
    chosen_raw = ta.cloud.provider or ""
    chosen = _norm(chosen_raw)

    if requested == "No preference":
        if not chosen:
            return HardConstraintCheck(
                constraint="Cloud provider selection",
                status="WARN",
                severity="MINOR",
                evidence=(
                    "The user expressed no cloud preference and the "
                    "Technology Advisor named no provider."
                ),
                recommendation=(
                    "Select a specific cloud provider and justify the choice."
                ),
            )

        return HardConstraintCheck(
            constraint="Cloud provider selection",
            status="PASS",
            severity="INFO",
            evidence=(
                f"No preference was stated; the solution selects {chosen_raw}."
            ),
            recommendation="",
        )

    aliases = CLOUD_ALIASES.get(
        requested,
        [_norm(requested)],
    )

    if any(alias in chosen for alias in aliases):
        return HardConstraintCheck(
            constraint=f"Cloud provider must be {requested}",
            status="PASS",
            severity="INFO",
            evidence=f"The Technology Advisor selected {chosen_raw}.",
            recommendation="",
        )

    other = next(
        (
            name
            for name, alias_list in CLOUD_ALIASES.items()
            if name != requested
            and any(alias in chosen for alias in alias_list)
        ),
        None,
    )

    if other:
        return HardConstraintCheck(
            constraint=f"Cloud provider must be {requested}",
            status="FAIL",
            severity="CRITICAL",
            evidence=(
                f"The user required {requested} but the solution "
                f"selects {chosen_raw}."
            ),
            recommendation=f"Re-target the solution onto {requested}.",
        )

    return HardConstraintCheck(
        constraint=f"Cloud provider must be {requested}",
        status="FAIL",
        severity="MAJOR",
        evidence=(
            f"The user required {requested} but the cloud provider "
            f"field reads '{chosen_raw or 'empty'}'."
        ),
        recommendation=f"State {requested} explicitly as the cloud provider.",
    )


# ---------------------------------------------------------------------------
# Data residency
# ---------------------------------------------------------------------------

def check_data_residency(
    user_input: dict,
    ta: TAOutput,
    sa: SAOutput,
) -> HardConstraintCheck:

    country = user_input["country"]

    haystack = _collect_text(
        ta.model_dump(),
        sa.model_dump(),
    )

    hints = COUNTRY_REGION_HINTS.get(
        country,
        [_norm(country)],
    )

    # Explicit country/region evidence.
    if any(hint in haystack for hint in hints):
        return HardConstraintCheck(
            constraint=f"Data must be hosted in {country}",
            status="PASS",
            severity="INFO",
            evidence=(
                f"The solution references {country} or a "
                f"recognized region/residency location associated with it."
            ),
            recommendation="",
        )

    # Residency discussed, but exact placement isn't clear.
    residency_terms = [
        "data residency",
        "data sovereignty",
        "data localization",
        "data localisation",
        "hosted in",
        "stored in",
        "region",
    ]

    if any(term in haystack for term in residency_terms):
        return HardConstraintCheck(
            constraint=f"Data must be hosted in {country}",
            status="WARN",
            severity="MINOR",
            evidence=(
                "Data residency/location is discussed, but the solution "
                f"does not clearly identify {country}."
            ),
            recommendation=(
                f"Explicitly state the cloud region or hosting location "
                f"used for {country} data."
            ),
        )

    return HardConstraintCheck(
        constraint=f"Data must be hosted in {country}",
        status="FAIL",
        severity="MAJOR",
        evidence=(
            f"Neither the architecture nor technology output provides "
            f"evidence that data will be hosted in {country}."
        ),
        recommendation=(
            f"Specify the hosting region/location in {country} and "
            "explain how data residency is maintained."
        ),
    )


# ---------------------------------------------------------------------------
# Technology preference
# ---------------------------------------------------------------------------

def check_technology_preference(
    user_input: dict,
    ta: TAOutput,
) -> HardConstraintCheck:

    preference = user_input["technology_preference"]

    named = [
        _norm(t.technology)
        for t in ta.technologies
        if t.technology
    ]

    if not named:
        return HardConstraintCheck(
            constraint=f"Technology preference: {preference}",
            status="FAIL",
            severity="MAJOR",
            evidence="The Technology Advisor named no technologies.",
            recommendation="Produce a concrete technology stack.",
        )

    proprietary = [
        tech
        for tech in named
        if any(marker in tech for marker in PROPRIETARY_MARKERS)
    ]

    open_source = [
        tech
        for tech in named
        if any(marker in tech for marker in OPEN_SOURCE_MARKERS)
    ]

    if preference == "Open-source":

        if proprietary:
            severity = (
                "MAJOR"
                if len(proprietary) > 1
                else "MINOR"
            )

            return HardConstraintCheck(
                constraint="Technology preference: Open-source",
                status="FAIL",
                severity=severity,
                evidence=(
                    "Proprietary products appear in the open-source "
                    "stack according to the rule-based technology "
                    "classification: "
                    + ", ".join(sorted(set(proprietary))[:4])
                ),
                recommendation=(
                    "Replace proprietary components with open-source "
                    "alternatives or explicitly justify the exception."
                ),
            )

        if len(open_source) < max(1, len(named) // 3):
            return HardConstraintCheck(
                constraint="Technology preference: Open-source",
                status="WARN",
                severity="MINOR",
                evidence=(
                    "Few of the selected technologies are recognized "
                    "by the rule-based classifier as open-source."
                ),
                recommendation=(
                    "Confirm the licensing/support model of each "
                    "selected technology."
                ),
            )

        return HardConstraintCheck(
            constraint="Technology preference: Open-source",
            status="PASS",
            severity="INFO",
            evidence=(
                f"{len(open_source)} of {len(named)} selections are "
                "recognized by the heuristic as open-source."
            ),
            recommendation="",
        )

    if preference == "Enterprise":

        if not proprietary and len(open_source) == len(named):
            return HardConstraintCheck(
                constraint="Technology preference: Enterprise",
                status="WARN",
                severity="MINOR",
                evidence=(
                    "An enterprise preference was stated, but the "
                    "named stack contains no technologies recognized "
                    "by the heuristic as commercially supported."
                ),
                recommendation=(
                    "Consider vendor-supported offerings or explicitly "
                    "state how commercial support is obtained."
                ),
            )

        return HardConstraintCheck(
            constraint="Technology preference: Enterprise",
            status="PASS",
            severity="INFO",
            evidence=(
                "The stack includes technologies recognized as "
                "commercial/proprietary or vendor-backed."
            ),
            recommendation="",
        )

    # Hybrid / other supported preference.
    return HardConstraintCheck(
        constraint=f"Technology preference: {preference}",
        status="PASS",
        severity="INFO",
        evidence=(
            f"Technology preference '{preference}' is accepted; "
            f"{len(open_source)} open-source and "
            f"{len(proprietary)} proprietary selections were identified "
            "by the heuristic."
        ),
        recommendation="",
    )


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

def check_timeline(
    user_input: dict,
    dp: DPOutput,
) -> HardConstraintCheck:

    months = user_input["delivery_timeline_months"]
    target = months * WEEKS_PER_MONTH
    planned = dp.total_weeks

    constraint = (
        f"Delivery within {months} month(s) "
        f"(~{target:.0f} weeks)"
    )

    if planned <= 0:
        return HardConstraintCheck(
            constraint=constraint,
            status="FAIL",
            severity="MAJOR",
            evidence="The delivery plan contains no phase durations.",
            recommendation=(
                "Produce a phased timeline with week durations."
            ),
        )

    ratio = planned / target

    if ratio > 1 + TIMELINE_SEVERE:
        return HardConstraintCheck(
            constraint=constraint,
            status="FAIL",
            severity="CRITICAL",
            evidence=(
                f"The plan totals {planned} weeks against a "
                f"{target:.0f}-week target "
                f"({(ratio - 1) * 100:.0f}% over)."
            ),
            recommendation=(
                "Cut or defer MVP scope until the plan fits "
                "the stated timeline."
            ),
        )

    if ratio > 1 + TIMELINE_TOLERANCE:
        return HardConstraintCheck(
            constraint=constraint,
            status="FAIL",
            severity="MAJOR",
            evidence=(
                f"The plan totals {planned} weeks against a "
                f"{target:.0f}-week target."
            ),
            recommendation=(
                "Compress or defer scope to bring the plan "
                "within the timeline."
            ),
        )

    if ratio < TIMELINE_UNDERRUN:
        return HardConstraintCheck(
            constraint=constraint,
            status="WARN",
            severity="MINOR",
            evidence=(
                f"The plan totals only {planned} weeks against a "
                f"{target:.0f}-week target, which may understate "
                "the work."
            ),
            recommendation=(
                "Confirm that the plan covers the complete MVP scope."
            ),
        )

    return HardConstraintCheck(
        constraint=constraint,
        status="PASS",
        severity="INFO",
        evidence=(
            f"The plan totals {planned} weeks against a "
            f"{target:.0f}-week target."
        ),
        recommendation="",
    )


# ---------------------------------------------------------------------------
# Traffic propagation
# ---------------------------------------------------------------------------

def check_traffic_propagation(
    user_input: dict,
    sa: SAOutput,
    ta: TAOutput,
    ba: dict,
) -> HardConstraintCheck:

    traffic = user_input["expected_daily_traffic"]

    haystack = _collect_text(
        ba,
        sa.model_dump(),
        ta.model_dump(),
    )

    candidates = {
        str(traffic),
        f"{traffic:,}",
    }

    if traffic >= 1000 and traffic % 1000 == 0:
        candidates.add(f"{traffic // 1000}k")
        candidates.add(f"{traffic // 1000},000")

    if any(
        candidate.lower() in haystack
        for candidate in candidates
    ):
        return HardConstraintCheck(
            constraint=f"Traffic requirement of {traffic:,} is propagated",
            status="PASS",
            severity="INFO",
            evidence=(
                "The stated traffic figure is explicitly referenced "
                "in the generated solution."
            ),
            recommendation="",
        )

    scale_words = [
        "throughput",
        "concurrent",
        "requests per",
        "rps",
        "daily active",
        "load",
        "peak traffic",
        "scale to",
        "daily users",
        "scalability",
    ]

    if any(word in haystack for word in scale_words):
        return HardConstraintCheck(
            constraint=f"Traffic requirement of {traffic:,} is propagated",
            status="WARN",
            severity="MINOR",
            evidence=(
                "Scale is discussed, but the exact user-specified "
                "traffic figure is not explicitly referenced."
            ),
            recommendation=(
                "Tie the capacity/scaling discussion explicitly "
                "to the stated traffic requirement."
            ),
        )

    return HardConstraintCheck(
        constraint=f"Traffic requirement of {traffic:,} is propagated",
        status="FAIL",
        severity="MAJOR",
        evidence=(
            "The stated traffic requirement is not reflected "
            "in the generated BA, SA, or TA outputs."
        ),
        recommendation=(
            "Explicitly address the requested traffic scale "
            "in the architecture and technology recommendations."
        ),
    )


# ---------------------------------------------------------------------------
# MVP coverage
# ---------------------------------------------------------------------------

def check_mvp_coverage(
    ba: dict,
    dp: DPOutput,
) -> HardConstraintCheck:

    mvp_items = [
        str(item)
        for item in (ba.get("mvp_scope") or [])
        if item
    ]

    if not mvp_items:
        return HardConstraintCheck(
            constraint="MVP scope must be addressed by the delivery plan",
            status="FAIL",
            severity="MAJOR",
            evidence="The Business Analyst defined no MVP scope.",
            recommendation="Define an explicit MVP scope.",
        )

    plan_text = _collect_text(dp.model_dump())

    covered = 0

    for item in mvp_items:

        keywords = [
            word
            for word in re.findall(
                r"[a-z]{5,}",
                item.lower(),
            )
            if word not in {
                "should",
                "system",
                "allow",
                "users",
                "there",
                "which",
            }
        ]

        if not keywords:
            covered += 1
            continue

        hits = sum(
            1
            for word in keywords
            if word in plan_text
        )

        if hits >= max(1, len(keywords) // 3):
            covered += 1

    ratio = covered / len(mvp_items)

    if ratio >= 0.7:
        return HardConstraintCheck(
            constraint="MVP scope must be addressed by the delivery plan",
            status="PASS",
            severity="INFO",
            evidence=(
                f"{covered} of {len(mvp_items)} MVP scope items "
                "are traceable into the delivery plan."
            ),
            recommendation="",
        )

    if ratio >= 0.4:
        return HardConstraintCheck(
            constraint="MVP scope must be addressed by the delivery plan",
            status="WARN",
            severity="MINOR",
            evidence=(
                f"Only {covered} of {len(mvp_items)} MVP scope items "
                "are traceable into the delivery plan."
            ),
            recommendation=(
                "Add workstream tasks for uncovered MVP items."
            ),
        )

    return HardConstraintCheck(
        constraint="MVP scope must be addressed by the delivery plan",
        status="FAIL",
        severity="MAJOR",
        evidence=(
            f"Only {covered} of {len(mvp_items)} MVP scope items "
            "are traceable into the delivery plan."
        ),
        recommendation=(
            "Rework the delivery plan to cover the defined MVP scope."
        ),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_hard_constraint_checks(
    user_input: dict,
    ba: dict,
    sa: SAOutput,
    ta: TAOutput,
    dp: DPOutput,
) -> list[HardConstraintCheck]:

    return [
        check_cloud_provider(user_input, ta),
        check_data_residency(user_input, ta, sa),
        check_technology_preference(user_input, ta),
        check_timeline(user_input, dp),
        check_traffic_propagation(
            user_input,
            sa,
            ta,
            ba,
        ),
        check_mvp_coverage(
            ba,
            dp,
        ),
    ]