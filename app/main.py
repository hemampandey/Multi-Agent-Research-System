from app.graph import graph

def main():
    topic = input("Enter topic: ")

    result = graph.invoke({"topic":topic})

    print("\n📄 FINAL REPORT:\n")
    print(result["final_report"])

    print("\n🔗 SOURCES:\n")
    for i, url in enumerate(result["sources"], 1):
        print(f"{i}. {url}")

if __name__ == "__main__":
    main()
