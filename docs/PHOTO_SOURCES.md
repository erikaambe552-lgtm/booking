# CampBlazer — Destination Photo Plan

Rule: only use **authentic photos of the actual Biliran destination**. Every photo must have a **credit** and, if someone else took it, a **licence or permission**. Don't use AI images or photos of other places. When no photo has been verified yet, the site shows a labelled illustration and the admin can replace it later.

## Current photos — final approved list (`backend/seed_photos/`, mapping in `photos.json`)
Pictures 1–13 from Nov 19 follow the order you sent them; Napo, Agpangi, Cogon, Alegre and Francis' Place keep the earlier photos. The credit shown comes from each photo's watermark. All are marked **"Permission pending"** until the owner agrees. Run `python manage.py seed_photos --reset` to load exactly this set.

| Destination | Photo | Credit |
|---|---|---|
| VRC Beach Resort | VRC Resort entrance stairway | BiliranIsland.com |
| Paradizu Bayview Resort | Welcome sign | BiliranIsland.com |
| Coco Grove Beach Resort | shaded sandy beach | © BiliranIsland.com |
| Agta Beach Resort | beachfront cottages (+ Commons sunset, Leodb CC BY-SA) | to be confirmed |
| Higatangan Island | aerial of the white sandbar | to be confirmed |
| Dalutan Island | aerial of the white beach with boats | BiliranIsland.com |
| Chamorita Beach Resort | family pool with octopus slide | to be confirmed |
| Napo Beach Resort | aerial of the resort and jetty | to be confirmed |
| Agpangi Brown Beach | brown-sand beach | © BiliranIsland.com |
| Cogon Beach Resort | beach cottages | to be confirmed |
| Alegre Beach Resort | 'Love the Philippines' graphic | photographer to be confirmed |
| Francis' Place | 'Love the Philippines' graphic | photographer to be confirmed |
| Mount Tres Marias | three labelled peaks | to be confirmed |
| Mount Panamao | grassland below the mountain | to be confirmed |
| Mount Suiro (Ascuero) | mountain above golden rice field | BiliranIsland.com |
| Mount Naliwatan | summit sign, 1,314 masl | to be confirmed |
| Mount Sayoa | mountain above rice terraces | BiliranIsland.com |
| Camp Beben | tents at night below the mountain | to be confirmed |

BiliranIsland.com is credited on 7 photos, so one permission request to them covers most of the set.

## Need permission (copyrighted, so don't upload without a yes)
| Destination | Where good photos exist | Ask |
|---|---|---|
| **Higatangan Island sandbar** | Naval LGU (photos supplied to PNA), langyaw.com (2015 sandbar set), biliranisland.com ("Photo by Jalmz") | Email or message the Naval Tourism Office first. A government source is the easiest to get permission from |
| Resorts (VRC, Paradizu, Coco Grove, Agta, Chamorita, Napo, Cogon, Alegre, Francis' Place) | Each resort's Facebook page / biliran.gov.ph listings | Message the resort. Explain it's a BiPSU capstone and that you'll credit them |
| Mountains (Tres Marias, Panamao, Suiro…) | Biliran Provincial Tourism ("Climb Biliran"), adrenalineromance.com, xaydtrips | Provincial Tourism Office |

## Best option: take your own photos
You're in Biliran. Photos the team takes are 100% authentic and free to use. Credit them as "Photo by <name>, CampBlazer team".

## How to attach photos
**One at a time:** log in as admin → Admin dashboard → Destinations → ✎ → Photos → upload the file (or paste a Commons URL), fill in the credit and licence, and tick "Use as cover".

**In bulk:**
```
photos/
  credits.csv
  higatangan-island/sandbar.jpg
  mount-tres-marias/summit.jpg
```
`credits.csv`
```
slug,filename,credit,license,caption,is_cover
higatangan-island,sandbar.jpg,Photo by J. Dela Cruz (CampBlazer team),Own photo,Higatangan shifting sandbar,1
mount-tres-marias,summit.jpg,Biliran Provincial Tourism Office,Used with permission,Tres Marias summit,1
```
```
python manage.py import_photos ../photos
```
Slugs: vrc-beach-resort, paradizu-bayview-resort, coco-grove-beach-resort, agta-beach-resort, higatangan-island, dalutan-island, chamorita-beach-resort, napo-beach-resort, agpangi-brown-beach, cogon-beach-resort, alegre-beach-resort, francis-place, mount-tres-marias, mount-panamao, mount-suiro-ascuero, mount-naliwatan, mount-sayoa, camp-beben
