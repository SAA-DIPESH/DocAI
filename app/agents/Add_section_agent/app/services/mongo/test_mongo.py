import os
from pprint import pprint
# Ensure your import path points to the correct location
from mongo_services import MongoService 


def test_find_best_matching_section():
    # 1. Input payload
    tender_id = "6a2ffcf49b077f038d5cce85"
    company_id = "6a202607915f3a8b0831fec6"
    section_name = "Company Details"
    section_purpose = "Demonstrate company capability and relevant experience."

    print("🚀 Running test for find_best_matching_section...")

    # 2. Call the function
    result = MongoService.find_best_matching_section(
        tender_id=tender_id,
        company_id=company_id,
        section_name=section_name,
        section_purpose=section_purpose
    )

    # 3. Print the actual results to your console (Updated Keys)
    print("\n--- TEST RESULTS ---")
    print(f"Matched ID:   {result.get('SectionId')}")
    print(f"Matched Name: {result.get('SectionName')}")
    print(f"Score:        {result.get('SimilarityScore')}")
    print("--------------------\n")

    # 4. Corrected Assertions
    assert "SectionId" in result, "Error: Missing SectionId in response"
    assert result["SectionName"] is not None, "Error: SectionName is empty"
    assert result["SimilarityScore"] > 0, "Error: Similarity score should be greater than 0"

    print("✅ Test passed successfully!")


if __name__ == "__main__":
    test_find_best_matching_section()