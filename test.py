from ai_engine.pipeline import NyaySaathiPipeline


def main() -> None:
    pipeline = NyaySaathiPipeline()
    test_inputs = [
        "My company has not paid my salary for 3 months",
        "padosi ne meri zameen par kabza kar liya",
        "UPI se paisa gaya par saamaan nahi mila",
    ]

    for idx, text in enumerate(test_inputs, start=1):
        result = pipeline.process(text)
        print(f"\nTest Case {idx}: {text}")
        print(f"category: {result.classification.category}")
        print(f"subcategory: {result.classification.subcategory}")
        print(f"confidence: {result.final_confidence:.3f}")
        print(f"intent_summary: {result.classification.intent_summary}")
        print(f"needs_clarification: {result.classification.needs_clarification}")


if __name__ == "__main__":
    main()