"""Correlation MCP tools."""

import os
from collections import defaultdict
from typing import Dict, List, Literal, Optional

from . import mcp
from ..client import brain_client
from ..client.correlation import CorrelationType


def _cluster_alphas(
    intra_df,
    id_to_sharpe: Dict[str, float],
    corr_threshold: float = 0.5,
) -> List[dict]:
    """Cluster alphas by intra-correlation and recommend best per cluster.

    Uses union-find to group alphas with pairwise |correlation| >= threshold.
    Returns list of dicts with cluster label, SUBMIT/SKIP recommendation,
    and correlated partners.
    """
    alpha_ids = [a for a in intra_df.columns if a in id_to_sharpe]

    # Find correlated pairs
    pairs: List[tuple] = []
    for i, a1 in enumerate(alpha_ids):
        for a2 in alpha_ids[i + 1:]:
            val = float(intra_df.loc[a1, a2]) if a1 in intra_df.index and a2 in intra_df.columns else 0.0
            if abs(val) >= corr_threshold:
                pairs.append((a1, a2, round(val, 2)))

    # Union-find
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: str, b: str):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a1, a2, _ in pairs:
        union(a1, a2)

    # Build clusters
    clusters: Dict[str, List[str]] = defaultdict(list)
    for aid in alpha_ids:
        clusters[find(aid)].append(aid)

    # Sort clusters by best Sharpe descending, assign labels
    results = []
    for ci, (_, members) in enumerate(
        sorted(clusters.items(), key=lambda kv: max(id_to_sharpe.get(a, 0) for a in kv[1]), reverse=True),
        start=1,
    ):
        members_sorted = sorted(members, key=lambda a: id_to_sharpe.get(a, 0), reverse=True)
        best = members_sorted[0]
        for aid in members_sorted:
            partner_notes = []
            for a1, a2, cv in pairs:
                if a1 == aid:
                    partner_notes.append(f"{a2}({cv})")
                elif a2 == aid:
                    partner_notes.append(f"{a1}({cv})")
            results.append({
                "alpha_id": aid,
                "sharpe": id_to_sharpe.get(aid, 0.0),
                "cluster": f"C{ci}",
                "recommend": "SUBMIT" if aid == best else "SKIP",
                "correlated_with": "; ".join(partner_notes) if partner_notes else "",
            })

    return results


@mcp.tool()
async def check_correlation(
    alpha_id: str,
    correlation_type: str = "both",
    threshold: float = 0.7,
    mode: Literal["remote", "local"] = "remote",
    years: int = 4,
    force_refresh: bool = False,
):
    """Check alpha correlation against production alphas, self alphas, or both.

    Args:
        alpha_id: The ID of the alpha to check.
        correlation_type: Which correlations to check. Valid values: "prod", "self", "power-pool", "both" (prod+self), "all" (prod+self+power-pool).
        threshold: Correlation threshold (default 0.7). Alpha passes if max correlation is below this.
        mode: "remote" (BRAIN API correlation endpoint) or "local" (PnL-based local computation).
        years: Trailing years of returns used only when mode="local".
        force_refresh: Re-download all OS alpha details and PnL data (mode="local" only).
    """
    if correlation_type == "both":
        check_types = [CorrelationType.PROD, CorrelationType.SELF]
    elif correlation_type == "all":
        check_types = [CorrelationType.PROD, CorrelationType.SELF, CorrelationType.POWER_POOL]
    else:
        check_types = [CorrelationType(correlation_type)]

    if mode == "local":
        result = await brain_client.check_local_correlation(
            alpha_id=alpha_id,
            check_types=check_types,
            threshold=threshold,
            years=years,
            force_refresh=force_refresh,
        )
    else:
        result = await brain_client.check_correlation(alpha_id, check_types, threshold)

    return str(result)


@mcp.tool()
async def batch_check_correlation(
    alpha_ids: List[str],
    correlation_type: str = "self",
    threshold: float = 0.7,
    years: int = 4,
    output_path: Optional[str] = None,
):
    """Check local correlation for a batch of alpha IDs at once.

    Computes both pairwise (intra) correlation between the candidates and
    each candidate vs baseline (inter) correlation. Saves the intra-correlation
    matrix as CSV.

    Also clusters alphas by intra-correlation (using the same threshold)
    and recommends the highest-Sharpe alpha per cluster for submission.

    Args:
        alpha_ids: List of alpha IDs to check (minimum 2).
        correlation_type: Which baseline correlations to check. Valid values: "self", "power-pool", "both" (self+power-pool). "prod" is not supported in local mode.
        threshold: Correlation threshold (default 0.7). Alpha passes if max correlation is below this.
        years: Trailing years of returns used for local computation.
        output_path: Optional path to save intra-correlation matrix CSV. Defaults to assets/correlation/batch_intra.csv.
    """
    # Parse correlation_type into check_types (same pattern, but exclude prod)
    if correlation_type == "both":
        check_types = [CorrelationType.SELF, CorrelationType.POWER_POOL]
    else:
        check_types = [CorrelationType(correlation_type)]

    result = await brain_client.batch_check_local_correlation(
        alpha_ids=alpha_ids,
        check_types=check_types,
        threshold=threshold,
        years=years,
    )

    intra_df = result["intra_correlation"]
    inter = result["inter_correlation"]

    # Save intra-correlation matrix CSV
    csv_path = output_path or "assets/correlation/batch_intra.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    intra_df.to_csv(csv_path)

    # Build markdown summary
    lines: List[str] = []
    lines.append("## Batch Correlation Results\n")

    # Inter-correlation: each candidate vs baseline
    lines.append("### Inter-Correlation (vs baseline)\n")
    lines.append("| Alpha ID | Passed | Check Type | Max Corr | Top Correlated |")
    lines.append("|----------|--------|------------|----------|----------------|")
    for aid, resp in inter.items():
        for ct, check_result in resp.checks.items():
            if check_result.top_correlations:
                top = check_result.top_correlations[0].id
            else:
                top = "—"
            max_corr = f"{check_result.max_correlation:.2f}" if check_result.max_correlation is not None else "—"
            passed = "✅" if check_result.passes_check else "❌"
            lines.append(f"| {aid} | {passed} | {ct.value} | {max_corr} | {top} |")
    lines.append("")

    # Intra-correlation: cluster and recommend
    # Fetch Sharpe for each alpha
    id_to_sharpe: Dict[str, float] = {}
    for aid in alpha_ids:
        try:
            details = await brain_client.get_alpha_details(aid)
            id_to_sharpe[aid] = float(details.is_.sharpe)
        except Exception:
            id_to_sharpe[aid] = 0.0

    clusters = _cluster_alphas(intra_df, id_to_sharpe, corr_threshold=threshold)
    if clusters:
        lines.append(f"### Intra-Correlation Cluster Analysis (threshold={threshold})\n")
        lines.append("| Cluster | Alpha ID | Sharpe | Recommend | Correlated With |")
        lines.append("|---------|----------|--------|-----------|-----------------|")
        for c in clusters:
            rec = f"✅ {c['recommend']}" if c["recommend"] == "SUBMIT" else f"⏭️ {c['recommend']}"
            lines.append(f"| {c['cluster']} | {c['alpha_id']} | {c['sharpe']:.2f} | {rec} | {c['correlated_with']} |")
        lines.append("")

        submit_count = sum(1 for c in clusters if c["recommend"] == "SUBMIT")
        total_clusters = len(set(c["cluster"] for c in clusters))
        lines.append(f"*{total_clusters} clusters found. {submit_count} alphas recommended for sequential submission.*")
        lines.append("")

    lines.append(f"📄 Intra-correlation matrix saved to: `{csv_path}`")

    return "\n".join(lines)


# Deprecated: replaced by check_alpha in alpha_tools.py
# @mcp.tool()
async def get_submission_check(alpha_id: str, is_power_pool: bool = False):
    """Comprehensive pre-submission check.

    Args:
        alpha_id: The ID of the alpha to check.
        is_power_pool: If True, applies Power Pool correlation rules (threshold=0.5, 10% Sharpe rule).
    """
    return str(await brain_client.get_submission_check(alpha_id, is_power_pool=is_power_pool))
