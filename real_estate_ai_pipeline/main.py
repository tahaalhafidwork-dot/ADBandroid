"""Main entry point for the real estate AI pipeline.

Usage:
    python main.py --input apify_facebook_groups_results.json --provider local
    python main.py --input apify_facebook_groups_results.json --provider kilo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Add pipeline directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processing.classifier import PostClassifier  # noqa: E402
from processing.deduplicator import Deduplicator  # noqa: E402
from processing.extractor import ListingExtractor  # noqa: E402
from processing.normalizer import ListingNormalizer  # noqa: E402
from providers.kilo_provider import KiloProvider  # noqa: E402
from providers.local_provider import LocalProvider  # noqa: E402


def load_posts(input_path: str) -> List[Dict[str, Any]]:
    """Load posts from the Apify results JSON file."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("posts", [])


def get_provider(provider_name: str) -> Any:
    """Instantiate the requested model provider."""
    if provider_name == "kilo":
        provider = KiloProvider()
    elif provider_name == "local":
        provider = LocalProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

    if not provider.initialize():
        print(
            f"Warning: Provider '{provider_name}' initialized but reports unavailable.",
            file=sys.stderr,
        )
    return provider


def run_pipeline(
    posts: List[Dict[str, Any]], provider_name: str = "local"
) -> Dict[str, Any]:
    """Run the full pipeline on a list of posts.

    Returns a dict with structured_listings, rejected_posts, duplicates,
    and pipeline statistics.
    """
    provider = get_provider(provider_name)
    print(f"Using provider: {provider.provider_name}")
    print(f"Provider available: {provider.is_available()}")

    # Step 1: Classify all posts
    print("\n[1/5] Classifying posts...")
    classifier = PostClassifier(provider)
    classified = classifier.classify_posts(posts)

    # Count categories
    category_counts: Dict[str, int] = {}
    for post in classified:
        cat = post.get("_classification", {}).get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    print(f"  Classification results: {category_counts}")

    # Step 2: Extract fields from sale/rent posts
    print("\n[2/5] Extracting structured fields...")
    extractor = ListingExtractor(provider)
    extracted = extractor.extract_posts(classified)

    # Step 3: Normalize extracted fields
    print("\n[3/5] Normalizing fields...")
    normalizer = ListingNormalizer()

    structured_listings: List[Dict[str, Any]] = []
    rejected_posts: List[Dict[str, Any]] = []

    for post in extracted:
        cat = post.get("_classification", {}).get("category", "unclear")
        extraction = post.get("_extraction", {})

        if extraction.get("skipped"):
            # Not a sale/rent listing - add to rejected
            rejected_posts.append({
                "index": post.get("index"),
                "url": post.get("url"),
                "category": cat,
                "reason": extraction.get("reason", ""),
                "text": post.get("text", "")[:200],
            })
            continue

        # Build the final listing dict from extraction fields
        listing = {
            "source": extraction.get("source"),
            "source_url": extraction.get("source_url"),
            "listing_type": extraction.get("listing_type"),
            "property_type": extraction.get("property_type"),
            "title": extraction.get("title"),
            "description": extraction.get("description"),
            "city": extraction.get("city"),
            "district": extraction.get("district"),
            "complex_name": extraction.get("complex_name"),
            "area_sqm": extraction.get("area_sqm"),
            "bedrooms": extraction.get("bedrooms"),
            "bathrooms": extraction.get("bathrooms"),
            "floor": extraction.get("floor"),
            "furnished": extraction.get("furnished"),
            "price": extraction.get("price"),
            "currency": extraction.get("currency"),
            "contact_phones": extraction.get("contact_phones", []),
            "published_at": extraction.get("published_at"),
            "confidence": extraction.get("confidence"),
            "_provider": extraction.get("provider"),
            "_classification_confidence": post.get("_classification", {}).get("confidence"),
            "_classification_reasoning": post.get("_classification", {}).get("reasoning"),
        }
        structured_listings.append(listing)

    # Normalize all listings
    structured_listings = normalizer.normalize_all(structured_listings)

    # Step 4: Deduplication
    print("\n[4/5] Deduplicating...")
    dedup = Deduplicator(similarity_threshold=0.80)
    unique_listings, duplicate_listings = dedup.find_duplicates(structured_listings)
    print(f"  Unique: {len(unique_listings)}, Duplicates: {len(duplicate_listings)}")

    # Step 5: Build output
    print("\n[5/5] Building output...")

    # Compute field completion rates
    field_completion: Dict[str, int] = {}
    schema_fields = [
        "listing_type", "property_type", "title", "description",
        "city", "district", "complex_name", "area_sqm", "bedrooms",
        "bathrooms", "floor", "furnished", "price", "currency",
        "contact_phones", "published_at",
    ]
    total_listings = len(unique_listings)
    for field in schema_fields:
        count = sum(
            1 for l in unique_listings if l.get(field) is not None
        )
        field_completion[field] = count

    stats = {
        "total_posts": len(posts),
        "provider": provider.provider_name,
        "provider_available": provider.is_available(),
        "category_counts": category_counts,
        "sale_count": category_counts.get("for_sale", 0),
        "rent_count": category_counts.get("for_rent", 0),
        "service_count": category_counts.get("real_estate_service", 0),
        "not_real_estate_count": category_counts.get("not_real_estate", 0),
        "unclear_count": category_counts.get("unclear", 0),
        "buy_request_count": category_counts.get("buy_or_rent_request", 0),
        "rejected_count": len(rejected_posts),
        "structured_count": len(structured_listings),
        "unique_count": len(unique_listings),
        "duplicate_count": len(duplicate_listings),
        "field_completion": field_completion,
        "field_completion_rate": {
            field: round(count / total_listings, 2) if total_listings > 0 else 0.0
            for field, count in field_completion.items()
        },
    }

    return {
        "structured_listings": unique_listings,
        "rejected_posts": rejected_posts,
        "duplicates": duplicate_listings,
        "stats": stats,
    }


def save_outputs(result: Dict[str, Any], output_dir: str) -> None:
    """Save pipeline outputs to JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "structured_listings.json"), "w", encoding="utf-8") as f:
        json.dump(result["structured_listings"], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "rejected_posts.json"), "w", encoding="utf-8") as f:
        json.dump(result["rejected_posts"], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "duplicates.json"), "w", encoding="utf-8") as f:
        json.dump(result["duplicates"], f, ensure_ascii=False, indent=2)

    print(f"\nOutputs saved to {output_dir}/")
    print(f"  - structured_listings.json ({len(result['structured_listings'])} listings)")
    print(f"  - rejected_posts.json ({len(result['rejected_posts'])} posts)")
    print(f"  - duplicates.json ({len(result['duplicates'])} duplicates)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Real Estate AI Pipeline - Process Facebook group posts"
    )
    parser.add_argument(
        "--input",
        default="apify_facebook_groups_results.json",
        help="Path to input JSON file with Facebook posts",
    )
    parser.add_argument(
        "--provider",
        choices=["local", "kilo"],
        default="local",
        help="Model provider to use (default: local)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)",
    )
    args = parser.parse_args()

    input_path = args.input
    if not os.path.isabs(input_path):
        input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", input_path)
        input_path = os.path.normpath(input_path)

    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading posts from: {input_path}")
    posts = load_posts(input_path)
    print(f"Loaded {len(posts)} posts")

    result = run_pipeline(posts, provider_name=args.provider)

    print("\n" + "=" * 60)
    print("PIPELINE STATISTICS")
    print("=" * 60)
    stats = result["stats"]
    for key, value in stats.items():
        if key != "field_completion_rate":
            print(f"  {key}: {value}")
    print("\n  Field completion rates:")
    for field, rate in stats.get("field_completion_rate", {}).items():
        print(f"    {field}: {rate}")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output_dir)
    save_outputs(result, output_dir)


if __name__ == "__main__":
    main()
