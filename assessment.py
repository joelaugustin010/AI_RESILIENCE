
"""Demonstration rules for the AI RESILIENCE assessment prototype."""

def assess_conditions(rainfall, river_level, ground):
    """Return a demonstration indicator score from 0 to 3."""
    score = 0

    if rainfall >= 100:
        score += 1

    if river_level >= 5:
        score += 1

    if ground in ["Waterlogged", "Unstable"]:
        score += 1

    return score


def explain_conditions(rainfall, river_level, ground):
    """Explain which demonstration indicators contributed to the score."""
    indicators = []

    if rainfall >= 100:
        indicators.append(
            "Rainfall is at or above the demonstration threshold of 100 mm."
        )

    if river_level >= 5:
        indicators.append(
            "River level is at or above the demonstration threshold of 5 m."
        )

    if ground == "Waterlogged":
        indicators.append("The reported ground condition is waterlogged.")
    elif ground == "Unstable":
        indicators.append("The reported ground condition is unstable.")

    if not indicators:
        indicators.append(
            "None of the configured demonstration indicators were triggered."
        )

    return indicators
