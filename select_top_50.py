import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Load original filtered posts (with images)
with open('apify_all_filtered.json', encoding='utf-8') as f:
    original_posts = json.load(f)

# Build URL -> images map
url_to_images = {}
for p in original_posts:
    url = p.get('url') or p.get('facebookUrl') or ''
    images = p.get('_extracted_images', [])
    if images:
        url_to_images[url] = images

print("URLs with images in original: %d" % len(url_to_images))

# Load sale/rent results
with open('real_estate_ai_pipeline/output/aqarati_50_sale_rent.json', encoding='utf-8') as f:
    listings = json.load(f)

# Add image info to each listing
for l in listings:
    url = l.get('source_url', '')
    images = url_to_images.get(url, [])
    l['images'] = images
    l['image_count'] = len(images)

# Count listings with images
with_images = [l for l in listings if l.get('image_count', 0) > 0]
without_images = [l for l in listings if l.get('image_count', 0) == 0]
print("Listings with images: %d" % len(with_images))
print("Listings without images: %d" % len(without_images))

# Save ALL qualified listings (sale/rent, valid date, at least one image) to separate file
# Filter: only those with at least one image
qualified = [l for l in listings if l.get('image_count', 0) > 0]
print("Qualified (with images): %d" % len(qualified))

with open('real_estate_ai_pipeline/output/aqarati_50_all_qualified.json', 'w', encoding='utf-8') as f:
    json.dump(qualified, f, ensure_ascii=False, indent=2)

print("Saved all qualified listings to aqarati_50_all_qualified.json")

# Select top 50 (prioritize those with more complete fields)
def completeness_score(l):
    score = 0
    for field in ['title', 'city', 'district', 'complex_name', 'area_sqm', 'bedrooms', 'price', 'currency']:
        if l.get(field) is not None:
            score += 1
    if l.get('image_count', 0) > 0:
        score += 1
    return score

qualified.sort(key=completeness_score, reverse=True)
top_50 = qualified[:50]

print("\nTop 50 selected:")
for_sale_50 = [l for l in top_50 if l.get('listing_type') == 'for_sale']
for_rent_50 = [l for l in top_50 if l.get('listing_type') == 'for_rent']
print("  For sale: %d" % len(for_sale_50))
print("  For rent: %d" % len(for_rent_50))

with open('real_estate_ai_pipeline/output/aqarati_50_selected.json', 'w', encoding='utf-8') as f:
    json.dump(top_50, f, ensure_ascii=False, indent=2)

print("Saved top 50 to aqarati_50_selected.json")

# Show top 50 details
for i, l in enumerate(top_50[:15]):
    print("  %d: %s, %s, city=%s, area=%s, beds=%s, price=%s, images=%d" % (
        i+1, l.get('listing_type'), l.get('property_type'),
        l.get('city'), l.get('area_sqm'), l.get('bedrooms'),
        l.get('price'), l.get('image_count')))
