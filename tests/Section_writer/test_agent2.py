import asyncio
import json

from app.agents.Section_writer.services.mongo_services.mongo_services import (
    ContextBuilder,
)

from app.agents.Section_writer.graph.node.section_writer import (
    section_writer,
)


async def main():

    builder = ContextBuilder()

    # Step 1 : Build Context
    context = builder.build_context(
        company_id="6b55059ff419103201431755",
        tender_id="6b5506d2f419103201431699",
    )

    builder.close()

    print("=" * 100)
    print("CONTEXT BUILT")
    print("=" * 100)

    print(f"Total Sections : {len(context['Sections'])}")
    print(f"Total Win Themes : {len(context['WinThemes'])}")

    if not context["Sections"]:
        print("No sections found.")
        return

    # Step 2 : First Section
    generation_context = {
        "Section": context["Sections"][0],
        "WinThemes": context["WinThemes"],
    }

    print("\n")
    print("=" * 100)
    print("SECTION SENT TO LLM")
    print("=" * 100)

    print(
        json.dumps(
            generation_context,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    # Step 3 : Call Section Writer
    result = await section_writer(
        generation_context=generation_context
    )

    print("\n")
    print("=" * 100)
    print("SECTION WRITER RESPONSE")
    print("=" * 100)

    print(
        json.dumps(
            result["response"],
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    print("\n")
    print("=" * 100)
    print("TOKEN USAGE")
    print("=" * 100)

    print(result["token_usage"])


if __name__ == "__main__":
    asyncio.run(main())