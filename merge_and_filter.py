import json
from datetime import datetime, timezone, timedelta
import re
import sys
sys.path.insert(0, 'real_estate_ai_pipeline')

# Load all batches
all_posts = []
batch_files = [
    'apify_batch_1_results.json',
    'apify_batch_2_results.json',
    'apify_batch_3_results.json',
    'apify_batch_4_results.json',
]

for bf in batch_files:
    try:
        with open(bf, encoding='utf-8-sig') as f:
            data = json.load(f)
        if isinstance(data, list):
            all_posts.extend(data)
        else:
            all_posts.extend(data.get('items', []))
        print(f"Loaded {bf}: {len(data) if isinstance(data, list) else len(data.get('items', []))} posts")
    except Exception as e:
        print(f"Error loading {bf}: {e}")

print(f"\nTotal raw posts: {len(all_posts)}")

# Remove exact URL duplicates
seen_urls = set()
unique_posts = []
for p in all_posts:
    url = p.get('url') or p.get('source_url') or p.get('permalinkUrl', '')
    if url and url not in seen_urls:
        seen_urls.add(url)
        unique_posts.append(p)
    elif not url:
        # Posts without URL - keep them but mark
        unique_posts.append(p)

print(f"After URL dedup: {len(unique_posts)} posts")

# Filter by date (last 60 days)
now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=60)

dated_posts = []
no_date_posts = []
for p in unique_posts:
    time_str = p.get('time') or p.get('publishedAt') or p.get('createdAt', '')
    if not time_str:
        no_date_posts.append(p)
        continue
    try:
        post_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        if post_time >= cutoff:
            dated_posts.append(p)
        # else: older than 60 days - exclude
    except:
        no_date_posts.append(p)

print(f"Posts with valid date within 60 days: {len(dated_posts)}")
print(f"Posts without date or invalid date: {len(no_date_posts)}")

# Check for images
posts_with_images = []
posts_without_images = []
for p in dated_posts:
    attachments = p.get('attachments', [])
    images = []
    for att in attachments:
        # Structure type 1: att.get('type') == 'Photo' with url/imageUri
        if att.get('type') == 'Photo':
            u = att.get('url') or att.get('imageUri')
            if u:
                images.append(u)
        # Structure type 2: att.get('__typename') == 'Photo' with image.uri or thumbnail
        elif att.get('__typename') == 'Photo' or att.get('__isMedia') == 'Photo':
            u = None
            if att.get('image', {}).get('uri'):
                u = att['image']['uri']
            elif att.get('thumbnail'):
                u = att['thumbnail']
            if u:
                images.append(u)
    if images:
        p['_extracted_images'] = images
        posts_with_images.append(p)
    else:
        posts_without_images.append(p)

print(f"Posts with at least one image: {len(posts_with_images)}")
print(f"Posts without images: {len(posts_without_images)}")

# Save all filtered posts
with open('apify_all_filtered.json', 'w', encoding='utf-8') as f:
    json.dump(posts_with_images, f, ensure_ascii=False, indent=2)

print("\nSaved filtered posts to apify_all_filtered.json")

# Show sample
for i, p in enumerate(posts_with_images[:3]):
    print(f"\n--- Post {i+1} ---")
    print(f"  Text: {(p.get('text') or '')[:100]}")
    print(f"  Time: {p.get('time')}")
    print(f"  Images: {len(p.get('_extracted_images', []))}")
