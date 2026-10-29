# INDOFLOODS acquisition and flood baseline

Run the repository's **Acquire INDOFLOODS and train flood research baseline** workflow from the GitHub Actions tab using `Run workflow`.

The workflow downloads four CSV tables directly from the official Zenodo record, verifies each file against the publisher-listed MD5 checksum, trains/evaluates the research baseline, and uploads the actual source tables, provenance manifest, model, and metrics as a downloadable GitHub Actions artifact. Raw datasets are not committed to Git history; they are recreated from the cited source on each run.

Source: Kuntla, S. K., & Saharia, M. (2025). *INDOFLOODS: A comprehensive database for flood events in India enhanced with catchment attributes*. Zenodo record 14584655; DOI 10.5281/zenodo.14584654. The publisher states that the dataset is openly accessible for academic and research purposes and requests citation of the dataset and associated BAMS article.

Important: the model estimates danger-level exceedance among **already recorded flood events**. The dataset does not contain matched non-flood periods, so this does not predict whether/when floods will occur. It is not validated for Kochi and must not be used for operational warnings.
