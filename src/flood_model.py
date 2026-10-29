
    st.markdown("**Integrity and provenance**")
    integrity = readiness.get("integrity", {})

    if integrity.get("hash_verified"):
        st.success("Dataset SHA-256 matches its metadata.")
    elif integrity.get("raw_hash_matches") is False:
        st.error("Dataset SHA-256 does not match its metadata.")
    else:
        st.warning("Dataset SHA-256 has not been verified.")

    st.write(
        "Verified real observations are required before "
        "user-facing model evaluation is allowed."
    )

    st.markdown("**Feature coverage**")
    st.write(
        f"Usable required features: "
        f"{readiness['feature_count']} of "
        f"{len(FEATURE_COLUMNS)}."
    )

    st.write(
        f"Calendar dates covered: {readiness['distinct_dates']}"
    )

    st.write(
        f"Invalid timestamps: "
        f"{readiness['invalid_timestamps'] or 0}"
    )

    if readiness["missing_values"]:
        st.markdown("**Missing values by column**")
        st.json(readiness["missing_values"])

    st.markdown("**Integrity audit details**")
    st.json(readiness.get("metadata_status", {}))
