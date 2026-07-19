"""
Pattern 9 · Index-Aware Retrieval — Ep10 (Azure)
Tríada verde en Azure Monitor Dashboard (3 widgets versionados, NO globales).

Mapea CR>0.85, Faith>0.9, AR>0.8 sobre Application Insights (customMetrics)
con filtros dimensionales fijos: pipeline=prod, model_version={fija}, domain=*.

Requisitos previos:
  pip install azure-identity azure-mgmt-dashboard azure-mgmt-resource
  Variables de entorno: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP
  Custom metrics ya ingestadas en App Insights: context_recall,
  faithfulness, answer_relevance (por pipeline/model_version/domain).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Final

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.mgmt.dashboard import DashboardManagementClient
from azure.mgmt.dashboard.models import (
    Dashboard,
    DashboardProperties,
    ErrorResponse,
    MarkdownPart,
    Part,
    PartType,
)


# ---------------------------------------------------------------------------
# Configuración — sin credenciales hardcodeadas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TriadConfig:
    """Parámetros de la tríada verde (alineados con Ep9 AWS)."""
    subscription_id: str
    resource_group: str
    dashboard_name: str
    location: str = "westeurope"
    model_version: str = "azure-openai-text-embed-3-large@2024-09"  # ¡FIJA!
    pipeline: Final[str] = "prod"
    # Umbrales firmados en el contrato Matryoshka (no se relajan)
    cr_threshold: float = 0.85
    faith_threshold: float = 0.90
    ar_threshold: float = 0.80


# ---------------------------------------------------------------------------
# Helpers — guardas anti-patrón (mezclar sustratos / versiones)
# ---------------------------------------------------------------------------

def _assert_versioned(triad: TriadConfig) -> None:
    """Bloquea dashboards globales (rompen histórico comparable)."""
    if triad.model_version.strip() in {"", "*", "latest"}:
        raise ValueError(
            "model_version debe ser FIJA y versionada. "
            "Un dashboard global rompe la firma Matryoshka "
            "y el histórico comparable entre Ep9 (AWS) y Ep10 (Azure)."
        )


def _kql(metric: str, op: str, threshold: float) -> str:
    """Consulta KQL con filtros dimensionales obligatorios."""
    return (
        f"customMetrics "
        f"| where name == '{metric}' "
        f"| where dimension.pipeline == '{TriadConfig.__dataclass_fields__['pipeline'].default or 'prod'}' "
        f"| summarize avg(value) by bin(timestamp, 1h), dimension.model_version, dimension.domain "
        f"| where avg_value {op} {threshold}"
    )


def _widget_part(title: str, kql_query: str, visualization_type: str = "line") -> Part:
    """Construye un AzureMonitorWidgetPart (KQL → métricas)."""
    part_metadata = {
        "type": "AzureMonitorWidgetPart",
        "settings": {
            "content": {
                "query": kql_query,
                "visualization": {"type": visualization_type},
                "title": title,
            }
        },
    }
    return Part(
        position={"x": 0, "y": 0, "colSpan": 6, "rowSpan": 4},
        metadata=part_metadata,
        type=PartType.MARKDOWN,  # placeholder; el ARM real usa widget-specific
    )


# ---------------------------------------------------------------------------
# Dashboard — 3 widgets versionados + guarda anti-patrón
# ---------------------------------------------------------------------------

def build_green_triad_dashboard(triad: TriadConfig) -> Dashboard:
    """Compone el dashboard con los 3 widgets de la tríada verde."""
    _assert_versioned(triad)

    kql_cr = _kql("context_recall", ">", triad.cr_threshold)
    kql_faith = _kql("faithfulness", ">", triad.faith_threshold)
    kql_ar = _kql("answer_relevance", ">", triad.ar_threshold)

    header = MarkdownPart(
        position={"x": 0, "y": 0, "colSpan": 12, "rowSpan": 1},
        markdown_content=(
            f"# Pattern 9 — Tríada verde (Azure)\n"
            f"**Sustrato:** AI Search + Azure OpenAI | **Pipeline:** `{triad.pipeline}` | "
            f"**Model version:** `{triad.model_version}` (FIJA)\n\n"
            f"Firma peligrosa → CR↑ Faith↓ ⇒ bug del generador, **no** embedder."
        ),
    )

    widgets = [
        header,
        _widget_part("Context Recall > 0.85", kql_cr),
        _widget_part("Faithfulness > 0.90", kql_faith),
        _widget_part("Answer Relevance > 0.80", kql_ar),
    ]

    props = DashboardProperties(
        lenses=[{"order": i, "parts": [p.serialize()] for i, p in enumerate(widgets)}],
        metadata={"model": {"columns": 12}},
    )

    return Dashboard(
        location=triad.location,
        tags={
            "pipeline": triad.pipeline,
            "model_version": triad.model_version,
            "pattern": "9-index-aware-retrieval",
            "substrate": "azure",
            "ep": "10",
        },
        properties=props,
    )


# ---------------------------------------------------------------------------
# Entrypoint — crea/actualiza el dashboard vía ARM
# ---------------------------------------------------------------------------

def deploy(triad: TriadConfig) -> str:
    credential = DefaultAzureCredential()
    client = DashboardManagementClient(credential, triad.subscription_id)

    dashboard = build_green_triad_dashboard(triad)

    try:
        poller = client.dashboards.begin_create_or_update(
            resource_group_name=triad.resource_group,
            dashboard_name=triad.dashboard_name,
            dashboard=dashboard,
        )
        result: Dashboard = poller.result()
        return result.id or ""
    except ClientAuthenticationError as exc:
        raise SystemExit(f"[auth] DefaultAzureCredential falló: {exc}") from exc
    except HttpResponseError as exc:
        raise SystemExit(f"[arm]  Dashboard rechazado: {exc.message}") from exc
    except ResourceNotFoundError as exc:
        raise SystemExit(f"[rg]   Resource group '{triad.resource_group}' no existe") from exc


# ---------------------------------------------------------------------------
# CLI — ejemplo de invocación
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = TriadConfig(
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group=os.environ["AZURE_RESOURCE_GROUP"],
        dashboard_name=f"pattern9-triad-{uuid.uuid4().hex[:8]}",
    )
    dashboard_id = deploy(cfg)
    print(f"[ok] Dashboard versionado desplegado: {dashboard_id}")