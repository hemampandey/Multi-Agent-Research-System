def extract_content_and_source(results):
    texts=[]
    sources=[]
    for r in results.get("results",[]):
        if "content" in r:
            texts.append(r["content"])
        elif "snippet" in r:
            sources.append(r["source"])

        if "url" in r:
            sources.append(r["url"])

    return "\n".join(texts), sources