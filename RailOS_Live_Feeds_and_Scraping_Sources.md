# RAILOS — LIVE FEEDS, TRAIN PLOTTING & ACTIVE BLOCK SOURCES
## Web Scraping Directory, Endpoints & Integration Architecture
**Project:** RailOS (SIH26027)  
**Date:** September 2026  
**Purpose:** Comprehensive directory of official, aggregator, and developer endpoints for live train plotting, active block status, and operational disruption feeds to power real-time data ingestion.

---

# 1. OFFICIAL CRIS / NTES LIVE TRAIN TRACKING ENDPOINTS

The **National Train Enquiry System (NTES)** operated by CRIS (Centre for Railway Information Systems) is the primary operational source for live train running on Indian Railways.

### 1.1 Web Endpoints & Query Parameters

| Feature | Base URL & Query Parameter Structure | Expected Output | Notes & Scraping Tips |
|---|---|---|---|
| **Portal Home** | `https://enquiry.indianrail.gov.in/mntes/` | Main Mobile Web Portal | Provides initial session cookie. Must establish session first. |
| **Spot Your Train (Live Running)** | `https://enquiry.indianrail.gov.in/mntes/q?opt=TrainRunningHistory&subOpt=ShowRunHist&trainNo={TRAIN_NO}&startDate={DD-MM-YYYY}` | HTML Table / Schedule | Returns: Current location, delay in minutes, arrival/departure actual vs scheduled, platform, and last passed station. |
| **Live Station (Upcoming Movements)** | `https://enquiry.indianrail.gov.in/mntes/q?opt=LiveStation&subOpt=showLiveStation&stationCode={STN_CODE}&hours={HOURS}` | HTML / DOM List | Parameters: `hours` can be `2`, `4`, or `8`. Shows all approaching and departing trains with expected delay at the station. |
| **Complete Train Schedule & Route** | `https://enquiry.indianrail.gov.in/mntes/q?opt=TrainSchedule&subOpt=showSchedule&trainNo={TRAIN_NO}` | HTML Table | Full itinerary of stations, day count, distance from origin, and booked timetable timings. |
| **Trains Between Stations** | `https://enquiry.indianrail.gov.in/mntes/q?opt=TBIS&subOpt=showTBIS&srcStation={SRC_CODE}&dstnStation={DST_CODE}` | HTML Table | Lists all scheduled passenger train pairs running between two stations. |

### 1.2 NTES Request Headers & Session Handling
When querying NTES programmatically, the server checks for browser-like session headers. Requests without these headers may be blocked:
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://enquiry.indianrail.gov.in/mntes/",
    "Connection": "keep-alive"
}
```

---

# 2. ACTIVE MAINTENANCE BLOCKS & EXCEPTIONAL OPERATIONAL DISRUPTIONS

Indian Railways announces planned, active, and emergency line possessions across several public and operational feeds.

### 2.1 NTES "Exceptional Trains" Feeds
Whenever maintenance blocks (traffic blocks, mega blocks, or non-interlocked signalling works) disrupt operations, CRIS logs the affected train services with official operational reasons:

| Feed Name | Direct URL | Data Fields Extracted | RailOS Ingestion Mapping |
|---|---|---|---|
| **Diverted Trains** | `https://enquiry.indianrail.gov.in/mntes/q?opt=DivertedTrains` | Train No, Name, Source, Destination, Diverted Route, Reason (e.g. *"Traffic Block between GZB and ALJN"*) | Maps directly to `corridors.json` and active block identification. |
| **Rescheduled Trains** | `https://enquiry.indianrail.gov.in/mntes/q?opt=RescheduledTrains` | Train No, Origin, Scheduled Departure, Rescheduled Time, Delay Minutes | Identifies trains held back to permit maintenance window execution. |
| **Cancelled Trains (Full & Partial)** | `https://enquiry.indianrail.gov.in/mntes/q?opt=CancelledTrains` | Train No, Date, Type (Fully / Partially Cancelled), Origin-Destination, Reason tag | Identifies sections with multi-day mega blocks or major engineering works. |

### 2.2 Zonal Railway Press Release Feeds (Mega Blocks & Jumbo Blocks)
Zonal railways officially publish their weekly maintenance and traffic block circulars through their public media portals every week:

| Railway Zone | Official URL | Typical Block Announcements |
|---|---|---|
| **Central Railway (CR)** | `https://cr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24` | Posts the weekly **"Mega Block on Sunday"** bulletin every Friday. Contains exact line (Up/Down Fast/Slow), station span (e.g. Matunga–Mulund), and start/finish hours (typically 11:00 to 16:00). |
| **Western Railway (WR)** | `https://wr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24` | Publishes **"Jumbo Block"** notices covering track maintenance, signalling overhauls, and OHE maintenance between designated stations (e.g. Churchgate–Mumbai Central). |
| **Northern Railway (NR)** | `https://nr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24` | Publishes traffic block and mega block circulars for Delhi, Moradabad, Lucknow, Ambala, and Firozpur divisions. |
| **Southern Railway (SR)** | `https://sr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24` | Regularly publishes **"Line Block / Power Block"** updates for Chennai, Palakkad, Madurai, and Thiruvananthapuram divisions. |
| **South Central Railway (SCR)** | `https://scr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24` | Details safety-related track renewal and electronic interlocking maintenance blocks. |
| **Press Information Bureau (PIB Railways)** | `https://pib.gov.in/` (Filter: Ministry of Railways) | Publishes national and regional press releases regarding major corridor upgrade blocks, DFCCIL cut-overs, and route remodeling. |

---

# 3. FREIGHT / GOODS OPERATIONS DATA (FOIS)

Because freight movements are largely unscheduled in the public timetable, operational monitoring relies on FOIS summaries:

| System / Portal | URL | Available Public Information |
|---|---|---|
| **FOIS Public Web Portal** | `https://www.fois.indianrail.gov.in/` | Freight Operations Information System landing page. |
| **FOIS Daily Performance** | `https://www.fois.indianrail.gov.in/FOISWeb/FoisDailyPerf` | Daily loading summaries, rake turnaround times, interchange statistics, and commodity throughput across zones. |
| **e-Demand / Terminal Tracking** | `https://www.fois.indianrail.gov.in/FOISWeb/` | Indent status, rake loading status at major siding terminals. |

---

# 4. FAST THIRD-PARTY JSON & REST ENDPOINTS (EASIEST TO SCRAPE)

For real-time testing and rapid prototyping, travel aggregators mirror NTES data and expose cleaner HTML or embedded JSON:

### 4.1 ConfirmTkt Live Running Status
- **URL Pattern:** `https://www.confirmtkt.com/train-running-status/{TRAIN_NO}`
- **Payload Format:** HTML page containing a serialized JSON object inside `<script>` tags (`window.__INITIAL_STATE__` or `data = {...}`).
- **Key Fields Available:**
  - `currentStationCode`: Station code where the train was last reported.
  - `delayInMinutes`: Integer delay (0 for on-time, positive for late).
  - `lastUpdatedTime`: Timestamp of last signal/station passing.
  - `upcomingStations`: Array of stations with expected arrival and departure times.

### 4.2 RailYatri Live Status
- **URL Pattern:** `https://www.railyatri.in/live-train-status/{TRAIN_NO}`
- **Payload Format:** Fast, mobile-responsive HTML with structured table elements detailing platform numbers, delay progression, and average speed.

### 4.3 eTrain.info Live Status & Running History
- **URL Pattern:** `https://etrain.info/in?TRAIN={TRAIN_NO}`
- **Payload Format:** Clean HTML tables showing historical delay performance, live station departures, and crossing trains.

### 4.4 RapidAPI Indian Railways REST APIs
For an officially structured JSON API layer, pre-built endpoints are available on RapidAPI:
- **Collection URL:** `https://rapidapi.com/collection/indian-railway-api`
- **Endpoints Typically Available:**
  - `GET /api/v1/liveTrainStatus?trainNo={TRAIN_NO}`
  - `GET /api/v1/liveStation?stationCode={STN_CODE}&hours={HOURS}`
  - `GET /api/v1/trainSchedule?trainNo={TRAIN_NO}`
- **Format:** Pure JSON. Requires a free RapidAPI key.

---

# 5. OPEN GOVERNMENT DATA PLATFORM (BULK MASTER DATA)

| Dataset | URL | Content & Usage |
|---|---|---|
| **Indian Railways Train Time Table** | `https://data.gov.in/catalog/indian-railways-train-time-table` | Bulk CSV dataset containing all scheduled passenger trains, stop codes, arrival/departure times, and distances. Use as static ground truth. |
| **All Indian Railway Stations** | `https://data.gov.in/resource/indian-railways-stations-data` | CSV containing station codes, English/Hindi names, divisions, zones, and GPS coordinates (Latitude/Longitude). |

---

# 6. SCRAPING SCRIPTS & IMPLEMENTATION BLUEPRINTS

### 6.1 Python Scraper: Live Train Plotting (ConfirmTkt JSON Extractor)
```python
import json
import re
import requests

def get_live_train_status(train_no: str) -> dict:
    """
    Fetches live running status for a train by extracting
    the embedded JSON payload from ConfirmTkt.
    """
    url = f"https://www.confirmtkt.com/train-running-status/{train_no}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        return {"success": False, "error": f"HTTP {response.status_code}"}
    
    # Locate embedded state payload
    match = re.search(r'data\s*=\s*(\{.*?\});', response.text)
    if match:
        try:
            payload = json.loads(match.group(1))
            return {
                "success": True,
                "train_number": train_no,
                "current_station": payload.get("CurrentStation", {}).get("StationCode"),
                "delay_minutes": payload.get("DelayInMinutes", 0),
                "last_updated": payload.get("LastUpdatedTime", ""),
                "raw_data": payload
            }
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {str(e)}"}
            
    return {"success": False, "error": "Could not locate state object in page HTML"}

# Test execution:
# status = get_live_train_status("12004")
# print(json.dumps(status, indent=2))
```

### 6.2 Python Scraper: NTES Cancelled / Diverted Trains (Block Indicator)
```python
import requests
from bs4 import BeautifulSoup

def get_ntes_diverted_trains() -> list:
    """
    Fetches trains currently diverted due to maintenance blocks or operational causes.
    """
    url = "https://enquiry.indianrail.gov.in/mntes/q?opt=DivertedTrains"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://enquiry.indianrail.gov.in/mntes/"
    }
    
    session = requests.Session()
    # Establish session cookie
    session.get("https://enquiry.indianrail.gov.in/mntes/", headers=headers, timeout=10)
    
    resp = session.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return []
        
    soup = BeautifulSoup(resp.text, "html.parser")
    diverted_trains = []
    
    table = soup.find("table")
    if table:
        for row in table.find_all("tr")[1:]:
            cols = [col.text.strip() for col in row.find_all("td")]
            if len(cols) >= 4:
                diverted_trains.append({
                    "train_no": cols[0],
                    "train_name": cols[1],
                    "diverted_from": cols[2],
                    "diverted_to": cols[3],
                    "reason": cols[4] if len(cols) > 4 else "Operational Block"
                })
                
    return diverted_trains
```

### 6.3 Python Scraper: Zonal Mega Block Press Bulletins
```python
import requests
from bs4 import BeautifulSoup
import re

def get_central_railway_mega_blocks() -> list:
    """
    Scrapes the latest press release headlines from Central Railway
    to capture scheduled Sunday Mega Block announcements.
    """
    url = "https://cr.indianrailways.gov.in/view_section.jsp?lang=0&id=0,4,24"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        return []
        
    soup = BeautifulSoup(resp.text, "html.parser")
    block_notices = []
    
    links = soup.find_all("a", href=True)
    for link in links:
        text = link.text.strip()
        if re.search(r'mega\s*block|traffic\s*block|jumbo\s*block|power\s*block', text, re.IGNORECASE):
            full_url = link["href"] if link["href"].startswith("http") else f"https://cr.indianrailways.gov.in/{link['href']}"
            block_notices.append({
                "title": text,
                "url": full_url
            })
            
    return block_notices
```

---

# 7. HOW TO MAP SCRAPED DATA INTO RAILOS DATASETS

To power the RailOS prototype with scraped live data, map the scraped fields into the platform's JSON schemas:

```text
┌─────────────────────────────────────────┐
│              SCRAPED INPUT              │
├─────────────────────────────────────────┤
│ • ConfirmTkt / NTES Live Train Status   │
│   → TrainNo, CurrentStation, Delay      │
│ • NTES Live Station (Upcoming 4 Hours)  │
│   → Approaching Trains, Booked Times    │
│ • Zonal Press Releases / Diverted List  │
│   → Affected Section, Block Time Window │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│        RAILOS INGESTION ADAPTER         │
├─────────────────────────────────────────┤
│ • train_movements.json                  │
│   Interpolate real-time train positions │
│   into section occupancy intervals:     │
│   [t_entry = scheduled + delay,         │
│    t_exit  = scheduled + delay + run]   │
│                                         │
│ • block_windows.json                    │
│   Instantiate candidate windows from:   │
│   1. Scraped official mega block hours  │
│   2. Computed inter-train headway gaps  │
│                                         │
│ • corridors.json                        │
│   Correlate station codes to track IDs  │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│    OR-TOOLS CP-SAT OPTIMIZATION MODEL   │
│ (Assigns pending maintenance to windows)│
└─────────────────────────────────────────┘
```

---

# 8. SUMMARY RECOMMENDATIONS FOR THE 36-HOUR HACKATHON

1. **Seed Topology with data.gov.in:** Download the static station list and timetable for the chosen pilot corridor (e.g. New Delhi $\rightarrow$ Kanpur, 440 km, or Ghaziabad $\rightarrow$ Aligarh, 106 km).
2. **Use ConfirmTkt / RailYatri for Live Train Tracking:** Use the JSON extractor above to grab current delay and location data for prominent trains (e.g. Train 12004 Shatabdi, Train 12301 Rajdhani, Train 22436 Vande Bharat).
3. **Parse Central/Western Railway Press Releases:** Scrape 2 or 3 actual "Mega Block" press release bulletins, convert them into `block_windows.json` inputs, and let RailOS demonstrate how it automatically slots maintenance tasks into those real-world windows.
