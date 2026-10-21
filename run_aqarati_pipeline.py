import json
from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, 'real_estate_ai_pipeline')

# Load filtered posts
with open('apify_all_filtered.json', encoding='utf-8') as f:
    posts = json.load(f)

print(f"Posts with images and valid date: {len(posts)}")

# Show sample (write to file to avoid encoding issues)
with open('C:/Users/lenovo/AppData/Local/Temp/kilo/sample_posts.txt', 'w', encoding='utf-8') as out:
    for i, p in enumerate(posts[:5]):
        out.write("--- Post %d ---\n" % i)
        out.write("  URL: %s\n" % p.get('url'))
        out.write("  Time: %s\n" % p.get('time'))
        out.write("  Images: %d\n" % len(p.get('_extracted_images', [])))
        out.write("  Text: %s\n" % (p.get('text') or '')[:150])
        out.write("\n")
print("Sample written to temp file")

# Now run pipeline with kilo-auto/free method B
from real_estate_ai_pipeline.main import run_pipeline

# The pipeline expects posts with 'text', 'url', 'time' fields
# Our posts have these fields plus _extracted_images
result = run_pipeline(posts, provider_name='kilo', method='B')

print("\n=== RESULTS ===")
print("Categories: %s" % result['stats']['category_counts'])
print("Unique: %d, Duplicates: %d" % (result['stats']['unique_count'], result['stats']['duplicate_count']))
print("Cost: %s" % result['stats']['cost_summary'])
print("Parse errors: %d" % len(result['stats']['parse_errors']))
print("Truncated: %d" % len(result['stats']['truncated_responses']))

# Save results
with open('real_estate_ai_pipeline/output/aqarati_50_results.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print("\nSaved results to aqarati_50_results.json")

# Show structured listings count
print("\nStructured listings: %d" % len(result['structured_listings']))
for i, l in enumerate(result['structured_listings'][:10]):
    print("  %d: %s, %s, %s, %s, %s, %s" % (
        i, l.get('listing_type'), l.get('property_type'), l.get('city'),
        l.get('complex_name'), l.get('area_sqm'), l.get('bedrooms')))
