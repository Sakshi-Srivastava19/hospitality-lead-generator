# Issues Log

Documentation of bugs found and fixed in the hotel lead-generation scraper.

| # | Issue | Status |
|---|-------|--------|
| 1 | Prices not matching / wrong prices | ✅ Fixed |
| 2 | MMT hotel names garbage / mostly missing | ✅ Fixed |

**Files touched:** `main.py` (matching logic), `price_extractor.py` (MMT extraction).

---

## Issue 1 — Prices not matching (and then wrong prices)

### Symptom

Every row in the CSV had an empty `PRICE PER DAY`, even for famous hotels that
clearly exist on MakeMyTrip:

```
NO PRICE MATCH: The Park Chennai (Best Score: 45.28)
NO PRICE MATCH: Supreme Stay - Hotel Chepauk (Best Score: 50.0)
```

### Root cause

Prices come from fuzzy-matching the Google hotel name against the MMT hotel name.
The original logic in `main.py` was:

```python
score = fuzz.token_sort_ratio(name.lower().strip(), mmt_name.lower().strip())
...
if best_score >= 85:
```

Two compounding problems:

1. **`token_sort_ratio` is too strict.** Google returns long names
   (`"The Hydel Park (Business Class Hotel) Chennai"`); MMT lists them shorter
   (`"the hydel park"`). Every extra/missing word is penalised, so even a correct
   match capped around 45–50 — nothing could ever reach 85.

2. **Noise words** (city suffix `chennai`, parentheticals `(Business Class Hotel)`,
   punctuation) were never stripped.

#### The over-correction (a second bug)

The first fix attempt switched to `token_set_ratio` with a low threshold. That was
**too loose** — it scores 100 whenever one name's tokens are a subset of the
other. MMT's `"the park chennai"` then wrongly matched *every* hotel sharing the
generic words `the` / `park` / `chennai`:

```
PRICE MATCHED: The Park Chennai        -> ₹7,499   (correct)
PRICE MATCHED: The Hydel Park ...       -> ₹7,499   (WRONG)
PRICE MATCHED: Raj Park Hotel Chennai   -> ₹7,499   (WRONG)
PRICE MATCHED: Park Avenue Hotel        -> ₹7,499   (WRONG)
PRICE MATCHED: The Leela Palace ...     -> ₹7,499   (WRONG)
```

Assigning a wrong price is worse than leaving it blank, so this was unacceptable.

### Fix

Final approach in `main.py`: **strip generic words, then use `token_sort_ratio`
with threshold 80.**

```python
GENERIC_WORDS = {
    "the", "a", "an", "in", "on", "by", "near", "and",
    "hotel", "hotels", "chennai", "brand", "accor", "business"
}

def normalize_hotel_name(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", " ", name)      # drop parentheticals
    name = re.sub(r"[^a-z0-9\s]", " ", name)  # drop punctuation
    tokens = [t for t in name.split() if t and t not in GENERIC_WORDS]
    return " ".join(tokens)
```

```python
google_norm = normalize_hotel_name(name)
for mmt_name, mmt_price in mmt_prices.items():
    mmt_norm = normalize_hotel_name(mmt_name)
    if not google_norm or not mmt_norm:   # guard: empty name never matches
        continue
    score = fuzz.token_sort_ratio(google_norm, mmt_norm)
    if score > best_score:
        best_score, best_price = score, mmt_price
if best_score >= 80:
    price_per_day = best_price
```

#### Why this works

- Stripping **only generic** words (never location/brand words like `omr`,
  `sipcot`, `ibis`) removes the shared noise that caused false subset matches,
  while keeping the distinctive core.
- `token_sort_ratio` then **penalises the remaining extra words**, so
  `"hydel park"` vs `"park"` scores 57 (rejected) while `"the park chennai"` vs
  `"the park chennai"` scores 100 (matched).
- The empty-string guard prevents a name made entirely of generic words from
  scoring 100 against another empty name.

#### Validation across all real pairs (20 Google × 10 MMT)

| Google name | Best MMT match | Score | Result |
|---|---|---|---|
| The Park Chennai | the park chennai | 100 | ✅ matched |
| ibis Chennai City Centre | ibis chennai city centre | 100 | ✅ matched |
| The Hydel Park (...) Chennai | the park chennai | 57 | ✅ rejected |
| Raj Park Hotel Chennai | the park chennai | 67 | ✅ rejected |
| Park Avenue Hotel, Chennai | the park chennai | 53 | ✅ rejected |
| The Leela Palace ... | essentia premier ... | 41 | ✅ rejected |

**100% precision — zero wrong prices assigned.**

### Known edge case

`Hablis` is genuinely on MMT, but Google's record has a typo (`"Chennal"`) plus
extra words (`"A Business Hotel"`), dropping its score to ~60 — *below* a false
positive like Raj Park at 67. No single threshold can catch it cleanly, so it is
intentionally left unmatched rather than risk a wrong match.

---

## Issue 2 — MMT hotel names garbage / mostly missing

### Symptom

Even with matching fixed, some runs produced almost no usable MMT data. The page
loaded fine (`Cards Found: 20`) but only **2 names** were extracted, and one was
not a hotel name at all:

```
Cards Found: 20
MMT hotels found: 2
  MMT: chromepet | 4.4 km drive to kumaran kundram temple => ₹7,298
  MMT: v v grand => ₹4,800
```

`"chromepet | 4.4 km drive to kumaran kundram temple"` is a **location/distance
line**, not a hotel name — so it could never match any Google hotel.

### Root cause

The original `price_extractor.py` guessed the hotel name from the card's visible
text by taking the *first line* that wasn't a skip-word, didn't contain `₹`, and
was longer than 5 characters:

```python
text = card.text
lines = text.split("\n")
for line in lines:
    if any(word in line.lower() for word in skip_words): continue
    if "₹" in line: continue
    if len(line) < 5: continue
    hotel_name = line
    break
```

This heuristic is fragile:
- Card text ordering is not guaranteed → it grabbed location/landmark lines.
- Many cards' real name line was filtered out → most cards yielded no name.
- Result: 2 (mostly junk) names out of 20 cards.

### Fix

Parse the rendered DOM with BeautifulSoup and read MMT's **structured name
element** `p[itemprop='name']` instead of guessing from text lines
(`price_extractor.py`):

```python
from bs4 import BeautifulSoup
...
soup = BeautifulSoup(driver.page_source, "lxml")
cards = soup.select("[class*='listingRow']")

for card in cards:
    name_node = card.select_one("p[itemprop='name']")
    if not name_node:
        continue
    hotel_name = name_node.get_text(strip=True)
    if not hotel_name:
        continue

    text = card.get_text(" ", strip=True)
    matches = re.findall(r'₹\s?[\d,]+', text)
    # ... pick best price > 500, dedupe by name ...
```

This selector was verified against the saved `mmt_page.html`: `p[itemprop='name']`
cleanly returns every hotel name (`Greens Venue`, `The Raintree St. Marys Road`,
`Hotel Savera`, …) with no garbage lines.

### Result

Before vs after, same `Cards Found: 20`:

```
# Before (heuristic)
MMT hotels found: 2
  MMT: chromepet | 4.4 km drive to kumaran kundram temple => ₹7,298   <- junk
  MMT: v v grand => ₹4,800

# After (BeautifulSoup, itemprop=name)
MMT hotels found: 8
  MMT: hotel savera => ₹6,999
  MMT: the park chennai => ₹7,499
  MMT: ibis chennai omr - an accor brand => ₹3,440
  MMT: ginger chennai omr => ₹3,499
  MMT: hablis => ₹15,500
  ...
```

Clean names → reliable matching. In the verified run, `The Park Chennai → ₹7,499`
matched correctly and was written to the CSV.

---

## Known limitation (not a bug)

The number of priced rows per run is **small and variable**. Google returns
Chennai's top-20 *premium* hotels; MakeMyTrip's listing page returns a different,
mostly *budget* set whose size swings between runs (2 → 8 → 40) due to lazy
loading. Prices only appear where the two lists overlap by name. The lever to get
more prices is loading more MMT hotels per run (more aggressive scrolling).
