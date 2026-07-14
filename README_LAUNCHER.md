# Getting Started — Lead Generator

This guide explains how to use the Lead Generator, step by step. You do
not need to know how to code. If you can open a program on your computer
and click buttons, you can use this.

---

## What does this tool do?

It searches for hotels, villas, farmhouses, and bungalows in a city you
choose, checks their prices online, and builds you a spreadsheet (CSV
file) with each property's name, location, phone number, email, website,
and social media links — ready to use for outreach.

You don't need to search anything by hand. You just tell it:
- **Which city**
- **What kind of property** (hotels, or villas/farmhouses/bungalows)
- **What price range** you care about

...and it does the rest, then hands you a spreadsheet.

---

## Two ways to use it

Think of these as two doors into the same room — pick whichever feels
easier.

| | **The Window** | **The Webpage** |
|---|---|---|
| What it looks like | A small app window opens on your computer | Opens in your normal web browser (Chrome, Edge, etc.) |
| File to run | `launcher.py` | `app.py` |
| Cities available | Only the one already set up for you | Any city — just type it in |
| Price ranges | Two ready-made options | Ready-made options, or type your own custom range |
| Best for | Quick, no-fuss use of the standard setup | More control — new cities, custom price ranges |

If you're not sure which to pick, **start with the Webpage** — it can do
everything the Window can, plus more.

---

## Option 1: The Webpage (`app.py`)

### Step 1 — Turn it on
Someone technical needs to do this part once: open a terminal in the
project folder and type:
```
python app.py
```
Leave that window open in the background — closing it turns the tool off.

### Step 2 — Open it in your browser
Open Chrome, Edge, or any browser, and go to this address:
```
http://127.0.0.1:5000
```
You'll see a simple form.

### Step 3 — Fill in the form
- **City** — type the city you want, e.g. "Jaipur" or "Udaipur."
- **Property type** — click either "Villas / Farmhouses / Bungalows" or
  "Hotels."
- **Price band** — click the price range(s) you want. You can select more
  than one. If you want a price range that isn't listed, click
  "+ Add a custom price range" and type your own.

### Step 4 — Start it
Click **Start collecting leads**. A box will appear showing what it's
doing, line by line, in real time. This can take anywhere from a few
minutes to over an hour, depending on how many properties it finds —
that's normal, just let it run in the background while you do other
things.

### Step 5 — See your results
When it finishes, click **View leads**. You'll see a table of everything
it found. You can:
- Click the tabs at the top to switch between price ranges.
- Type a name in the search box to find one property quickly.
- Click **Download CSV** to save it as a spreadsheet you can open in
  Excel or Google Sheets.

### Step 6 — Run it again
Click **New search** to start over with a different city, property type,
or price range. Nothing you've already collected gets deleted or
overwritten — every search adds to what you already have.

---

## Option 2: The Window (`launcher.py`)

### Step 1 — Open it
Double-click `launcher.py`. A small window will appear with two buttons.

### Step 2 — Pick a category
Click **Select** under either:
- **Villas / Farmhouses / Bungalows** (₹15,000–₹60,000 a night)
- **Hotels** (₹4,000–₹10,000 a night)

### Step 3 — Start it
Click **Start Collecting Leads**. You'll see the same kind of live
progress box as the Webpage version. Just wait for it to finish.

### Step 4 — See your results
Click **View Leads** to browse what was found in a table. You can search
by name, switch between price ranges using the dropdown, and click
**Open in Excel/Spreadsheet App** to open the results directly.

### What this version can't do
It always searches whichever city is already set up for you — you can't
type a different city into the window itself, and you can only use the
two ready-made price ranges shown above. If you need a different city or
a custom price range, use the Webpage instead.

---

## Where do my results go?

Every search saves a spreadsheet (CSV file) into a folder called
`output`, inside the project folder. You'll get:
- One file with **everything** ever found for that city.
- One file **per price range**, so you can open just the leads you care
  about.

These are normal spreadsheet files — double-click them and they'll open
in Excel, Google Sheets, or whatever spreadsheet program you normally use.

---

## Frequently Asked Questions

**Do I need to understand any of the code?**
No. Everything above only involves clicking buttons and filling in a
form.

**Can I run it for more than one city?**
Yes — using the Webpage, just type a different city each time. Each
city's results are kept separate and nothing gets overwritten.

**What if I run the same city and price range twice?**
Nothing bad happens — it automatically skips any property it already
found before, and only adds new ones.

**How long does a search take?**
It depends on how many matching properties there are — usually somewhere
between a few minutes and an hour. You'll see it working in the live
progress box the whole time, so you'll know it hasn't frozen.

**What if it stops with an error message?**
Copy the last few lines shown in the progress box and send them to
whoever set this up for you (or paste them back into this chat) — the
message usually explains exactly what went wrong.

**Is any of my data sent to the internet, other than the search itself?**
The Webpage only runs on your own computer (`127.0.0.1` means "this
computer" — nothing is put online or made public). It does need internet
access to search Google and Booking.com, the same as any browser would.

---

## If Something Goes Wrong

| What you see | What it means |
|---|---|
| The progress box stops and shows red/error text | Something interrupted the search — most often a slow or broken hotel website. Try running it again. |
| "No leads found" for a price range | There simply weren't any matching properties in that price range for that city — this isn't a malfunction. |
| The Webpage won't open in the browser | Whoever runs `python app.py` for you may not have started it, or it may have been closed. Ask them to check. |
| A downloaded CSV looks empty or half-filled | The search may still be running, or was stopped early. Wait for it to finish, or run it again. |

For anything not covered here, a more detailed technical guide
(`README.md`) is available for whoever manages the technical side of this
tool.