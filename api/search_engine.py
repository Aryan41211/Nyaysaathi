from .data_loader import CASES


def simple_search(query):
    query = query.lower()

    results = []

    for case in CASES:

        score = 0

        descriptions = case.get("descriptions", [])

        for desc in descriptions:
            desc = desc.lower()

            if query in desc:
                score += 5

            for word in query.split():
                if word in desc:
                    score += 2

        problem = case.get("problem_description", "").lower()

        for word in query.split():
            if word in problem:
                score += 1

        if score > 0:
            results.append({
                "case": case,
                "score": score
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return [r["case"] for r in results[:5]]