from app.llm import generate

def review_report(report, topic):
    prompt = f"""
    You are an expert editor reviewing a research report on the topic: "{topic}".
    
    Evaluate the report based on these quality criteria:
    1. Structure: Does it have an Introduction, Key Points, and Conclusion?
    2. Grounding: Is it clear and detailed enough?
    3. Citations: Does it contain inline citation numbers like [1] or [2] to cite sources? (This is CRITICAL. If there are no inline citations, it must be rejected).

    If the report is ready and high-quality, please rewrite it to polish the phrasing, formatting, and grammar, ensuring it looks like a professional whitepaper.
    Keep every inline citation number exactly as it appears, and do not add new facts.
    IMPORTANT: Start your response with "ACCEPT:" and then output the full polished report. Do not explain what you changed.

    If the report is poor, lacks inline citations, or is too superficial, write constructive feedback indicating what needs to be fixed.
    IMPORTANT: Start your response with "REJECT:" and then write your specific feedback for the writer. Do not write the report.

    Report to review:
    {report}
    """

    response = generate(prompt)
    return response