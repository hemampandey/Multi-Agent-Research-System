from app.llm import generate


def generate_report(topic,data):
    prompt = f"""
    Write a professional research report.

    IMPORTANT:
    - Use ONLY the provided data
    - Add citation numbers like [1], [2] in the text
    - Each citation should correspond to a source
    - Be clear and structured

    Data:
    {data}

    Topic: {topic}

    Format:
    -Introduction
    -Key Points
    -Conclusion
    """

    response = generate(prompt)

    return response