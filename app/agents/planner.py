from app.llm import generate

def create_plan(topic):
    prompt = f"""
    Break this topic into exactly 4 short research questions:

    Rules:
    - One line per question
    - No explanations
    - No headings
    - Only clean questions    

    Topic: {topic}
    """

    response = generate(prompt)

    questions = []
    for line in response.split("\n"):
        if line.strip():
            questions.append(line.split(". ",1)[-1])

    return questions