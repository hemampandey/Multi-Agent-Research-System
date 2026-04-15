from app.llm import generate

def improve_report(report):
    prompt = f"""
    Rewrite this report to improve clarity and professionalism.

    IMPORTANT:
    - Do NOT explain what you changed
    - Do NOT add meta comments
    - Output ONLY the final improved report

    Report:
    {report}
    """

    response = generate(prompt)

    return response