# ============================================================
# GreenTender - AI BID EVALUATION ENGINE
# ------------------------------------------------------------
# Scores and ranks nursery quotations ("bids") submitted
# against a tender, using a transparent weighted-scoring model.
#
# No external AI API is called — this is a self-contained,
# deterministic "AI" scoring engine so it works fully offline,
# with no API keys and no extra cost. It's built so it can be
# swapped later for an LLM-based evaluator without changing
# any of the calling code (see evaluate_quotation()).
# ============================================================

from datetime import datetime, date


# ------------------------------------------------------------
# WEIGHTS
# ------------------------------------------------------------
# Together these must sum to 100. Tune here to change how the
# AI prioritises price vs speed vs quantity vs trust vs detail.
WEIGHTS = {
    "price": 40,          # Lower quoted price relative to other bids scores higher
    "delivery": 20,       # Fewer delivery days scores higher
    "quantity": 20,       # Meeting/exceeding the tender's required quantity scores higher
    "trust": 15,          # Verified nursery status
    "description": 5,     # Presence of a clear, sufficiently detailed quotation description
}


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _score_price(quoted_price, min_price, max_price, estimated_budget):
    """
    Lower price is better. Score is scaled relative to the
    cheapest and priciest bids on THIS tender, with a bonus
    penalty if a bid exceeds the tender's estimated budget.
    """
    quoted_price = _safe_float(quoted_price)

    if quoted_price <= 0:
        return 0.0

    if max_price == min_price:
        base = 100.0
    else:
        # Cheapest bid -> 100, priciest bid -> 40 (never zero out a
        # valid bid just for being the most expensive of the group)
        span = max_price - min_price
        base = 100.0 - ((quoted_price - min_price) / span) * 60.0

    budget = _safe_float(estimated_budget)
    if budget > 0 and quoted_price > budget:
        over_pct = (quoted_price - budget) / budget
        # Penalize going over budget, capped so it can't go negative
        base -= min(30.0, over_pct * 100.0)

    return max(0.0, min(100.0, base))


def _score_delivery(delivery_days, min_days, max_days):
    """Fewer delivery days is better, scaled relative to this tender's bids."""
    delivery_days = _safe_int(delivery_days)

    if delivery_days <= 0:
        return 50.0  # unknown/invalid -> neutral score

    if max_days == min_days:
        return 100.0

    span = max_days - min_days
    score = 100.0 - ((delivery_days - min_days) / span) * 100.0
    return max(0.0, min(100.0, score))


def _score_quantity(quantity_available, quantity_required):
    """Meeting or exceeding the required quantity scores highest."""
    available = _safe_int(quantity_available)
    required = _safe_int(quantity_required)

    if required <= 0:
        return 50.0

    ratio = available / required

    if ratio >= 1.0:
        return 100.0
    if ratio <= 0:
        return 0.0

    return round(ratio * 100.0, 2)


def _score_trust(verification_status):
    status = (verification_status or "").strip().lower()
    if status == "verified":
        return 100.0
    if status == "pending":
        return 50.0
    return 20.0  # rejected / unverified / unknown


def _score_description(description):
    text = (description or "").strip()
    length = len(text)

    if length == 0:
        return 0.0
    if length < 20:
        return 40.0
    if length < 80:
        return 75.0
    return 100.0


def _days_until_closing(closing_date):
    """Returns None if closing_date isn't a usable date."""
    if not closing_date:
        return None
    if isinstance(closing_date, datetime):
        closing_date = closing_date.date()
    if isinstance(closing_date, date):
        return (closing_date - date.today()).days
    return None


def _recommendation(score):
    if score >= 80:
        return "Highly Recommended"
    if score >= 60:
        return "Recommended"
    if score >= 40:
        return "Consider with Caution"
    return "Not Recommended"


def evaluate_quotation(quotation, tender, group_stats):
    """
    Scores a single quotation (dict-like, e.g. a DB row) against
    its tender (dict-like) and the group_stats computed across
    all quotations for that tender (see rank_quotations_for_tender).

    Returns a dict:
        {
            "quotation_id": ...,
            "ai_score": float 0-100,
            "recommendation": str,
            "breakdown": {
                "price": {...}, "delivery": {...},
                "quantity": {...}, "trust": {...}, "description": {...}
            }
        }
    """
    price_score = _score_price(
        quotation.get("quoted_price"),
        group_stats["min_price"],
        group_stats["max_price"],
        tender.get("estimated_budget"),
    )

    delivery_score = _score_delivery(
        quotation.get("delivery_days"),
        group_stats["min_days"],
        group_stats["max_days"],
    )

    quantity_score = _score_quantity(
        quotation.get("quantity_available"),
        tender.get("quantity_required"),
    )

    trust_score = _score_trust(quotation.get("verification_status"))

    description_score = _score_description(
        quotation.get("quotation_description")
    )

    weighted_total = (
        price_score * WEIGHTS["price"]
        + delivery_score * WEIGHTS["delivery"]
        + quantity_score * WEIGHTS["quantity"]
        + trust_score * WEIGHTS["trust"]
        + description_score * WEIGHTS["description"]
    ) / 100.0

    ai_score = round(weighted_total, 1)

    return {
        "quotation_id": quotation.get("quotation_id"),
        "nursery_id": quotation.get("nursery_id"),
        "ai_score": ai_score,
        "recommendation": _recommendation(ai_score),
        "breakdown": {
            "price": round(price_score, 1),
            "delivery": round(delivery_score, 1),
            "quantity": round(quantity_score, 1),
            "trust": round(trust_score, 1),
            "description": round(description_score, 1),
        },
    }


def rank_quotations_for_tender(tender, quotations):
    """
    tender: dict-like row from `tenders` (needs at least
        estimated_budget, quantity_required).
    quotations: list of dict-like rows, each needs at least
        quotation_id, nursery_id, quoted_price, delivery_days,
        quantity_available, quotation_description, and ideally
        verification_status (join with nursery_profiles).

    Returns a list of quotations (as plain dicts, original
    fields preserved) each augmented with:
        ai_score, ai_recommendation, ai_rank, ai_breakdown
    sorted by ai_score descending (best bid first).
    """
    if not quotations:
        return []

    prices = [_safe_float(q.get("quoted_price")) for q in quotations if _safe_float(q.get("quoted_price")) > 0]
    days = [_safe_int(q.get("delivery_days")) for q in quotations if _safe_int(q.get("delivery_days")) > 0]

    group_stats = {
        "min_price": min(prices) if prices else 0.0,
        "max_price": max(prices) if prices else 0.0,
        "min_days": min(days) if days else 0,
        "max_days": max(days) if days else 0,
    }

    results = []
    for q in quotations:
        evaluation = evaluate_quotation(q, tender, group_stats)
        merged = dict(q)
        merged["ai_score"] = evaluation["ai_score"]
        merged["ai_recommendation"] = evaluation["recommendation"]
        merged["ai_breakdown"] = evaluation["breakdown"]
        results.append(merged)

    results.sort(key=lambda r: r["ai_score"], reverse=True)

    for idx, r in enumerate(results, start=1):
        r["ai_rank"] = idx

    return results


def best_bid_summary(ranked_quotations):
    """Short human-readable summary of the top bid, for flashes/notifications."""
    if not ranked_quotations:
        return "No quotations available for AI evaluation yet."

    top = ranked_quotations[0]
    return (
        f"AI recommends Quotation #QT-{top['quotation_id']} "
        f"(score {top['ai_score']}/100 — {top['ai_recommendation']})."
    )
