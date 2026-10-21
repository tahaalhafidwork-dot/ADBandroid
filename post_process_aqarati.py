import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

with open('real_estate_ai_pipeline/output/aqarati_50_results.json', encoding='utf-8') as f:
    result = json.load(f)

print("Categories:", result['stats']['category_counts'])
print("Unique: %d, Duplicates: %d" % (result['stats']['unique_count'], result['stats']['duplicate_count']))
print("Cost:", result['stats']['cost_summary'])
print("Parse errors: %d" % len(result['stats']['parse_errors']))
print("Truncated: %d" % len(result['stats']['truncated_responses']))
print("Structured listings: %d" % len(result['structured_listings']))

# Filter for sale/rent only
sale_rent = [l for l in result['structured_listings'] if l.get('listing_type') in ('for_sale', 'for_rent')]
print("\nSale/Rent listings: %d" % len(sale_rent))

# Count by listing_type
for_sale = [l for l in sale_rent if l.get('listing_type') == 'for_sale']
for_rent = [l for l in sale_rent if l.get('listing_type') == 'for_rent']
print("  For sale: %d" % len(for_sale))
print("  For rent: %d" % len(for_rent))

# Show first 10
for i, l in enumerate(sale_rent[:10]):
    print("  %d: %s, %s, city=%s, complex=%s, area=%s, beds=%s, price=%s, images=%d" % (
        i, l.get('listing_type'), l.get('property_type'),
        l.get('city'), l.get('complex_name'), l.get('area_sqm'),
        l.get('bedrooms'), l.get('price'), l.get('image_count', 0)))

# Save filtered sale/rent only
with open('real_estate_ai_pipeline/output/aqarati_50_sale_rent.json', 'w', encoding='utf-8') as f:
    json.dump(sale_rent, f, ensure_ascii=False, indent=2)

print("\nSaved sale/rent listings to aqarati_50_sale_rent.json")
