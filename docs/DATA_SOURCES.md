# Feature data provenance

The 30 feature columns and all 11,055 feature rows in `prediction_artifacts/phisingtest.csv` exactly match `Training Dataset.arff` from UCI dataset 327 after excluding the `Result` column. This equality was verified on 24 September 2026. The original downloaded project did not include ground-truth labels in that CSV.

Dataset citation: Mohammad, R. & McCluskey, L. (2012). Phishing Websites [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C51W2X.

The UCI page lists the dataset license as CC BY 4.0. See https://archive.ics.uci.edu/dataset/327/phishing. Feature descriptions are paraphrased from the accompanying `Phishing Websites Features.docx`, by Rami M. Mohammad, Fadi Thabtah, and Lee McCluskey. Actual encoded domains were checked against the released ARFF and the project's CSV.

The workbook and `feature_dictionary.json` identify discrepancies between the document and released domains. They do not claim to reconstruct the original extractor. In particular, `Redirect` has released codes 0/1 despite a three-category narrative; `Request_URL` is binary despite a three-band documented rule; the `port` rule conflicts with its own preferred-state table.

The original application source and model were supplied in a downloaded folder without Git history or a license file. Existing author metadata is retained; the dataset license is not represented as a license for the inherited application code.
