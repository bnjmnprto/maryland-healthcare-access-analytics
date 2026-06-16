from src.ai_summary import summarize_all_counties
from src.data_pipeline import run_pipeline


UNSUPPORTED_CLINICAL_CLAIMS = [
    "diagnose",
    "diagnosis",
    "treatment plan",
    "clinical decision",
    "patient-specific",
    "guaranteed",
]


def test_ai_summaries_are_generated_for_all_counties():
    processed = run_pipeline()
    summaries = summarize_all_counties(processed)

    assert len(summaries) == 24
    assert summaries["plain_english_summary"].notna().all()


def test_ai_summaries_do_not_make_unsupported_clinical_claims():
    processed = run_pipeline()
    summaries = summarize_all_counties(processed)
    combined_text = " ".join(summaries["plain_english_summary"]).lower()

    for phrase in UNSUPPORTED_CLINICAL_CLAIMS:
        assert phrase not in combined_text
