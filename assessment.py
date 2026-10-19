"""Demonstration rules for the AI RESILIENCE assessment prototype."""


def assess_conditions(rainfall, river_level, ground):
    """Return a score from 0 to 3 using the app's existing rules."""
    score = 0

    if rainfall >= 100:
        score += 1
    if river_level >= 5:
        score += 1
    if ground in ["Waterlogged", "Unstable"]:
        score += 1

    return score