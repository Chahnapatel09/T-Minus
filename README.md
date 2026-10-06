# T-Minus

Illegal gold mining is eating into the rainforest of Madre de Dios in southern Peru, and one of the worst-hit places, La Pampa, is also one of the hardest to watch from space. It sits under cloud for most of the year. On 29 August 2021 a Sentinel-2 optical satellite passed over the same ground that a radar satellite imaged that day, and the optical picture is almost entirely white. Radar does not care about cloud, so that is what T-Minus is built on.

It takes RADARSAT-2 radar images of La Pampa from different dates, finds the places where forest turned into bare ground or mining ponds, and ranks them as alerts that someone could go and check, each with a size, a type and coordinates. It also asks a question the alerts make possible: did the 2019 crackdown, Operation Mercury, actually slow the clearing, or did the mining simply move? The results are shown in a web page with a before and after slider, a ranked list of alerts, and an analytics view that compares the crackdown area with the land around it.

## What the radar sees

C-band radar returns a strong echo from standing forest, a weaker one from bare ground, and almost nothing from still water. In our images forest sits around -8 dB, and the flooded pits that gold mining leaves behind show up as dark clusters strung along the mining corridors. Comparing two dates therefore turns "where did the forest go?" into "where did the echo get weaker, and stay weaker?". That is the whole idea, and the rest of the project is about making it trustworthy.

## How it works

The raw material is two RADARSAT-2 scenes (February 2017 and August 2021) in single look complex format, which is not an image yet but complex numbers. Preprocessing turns each into calibrated backscatter in decibels on one shared 10 m map grid, either with ESA SNAP (terrain corrected) or with a plain Python route that needs no extra software. Both land in the same place and the rest of the pipeline cannot tell them apart.

Two detectors then look at the pair. The first is a simple rule: a pixel that was forest and later got at least 3 dB darker, or fell low enough to be water, is flagged, and when a later image exists it must stay that way. The second is a random forest that learns what mining looks like from Amazon Mining Watch, a map of Amazon mining made from optical imagery and so independent of the radar. It can optionally use features from a pretrained radar network as well. Where both detectors fire, the alert is high confidence. Where only one does, it is medium.

Flagged pixels are grouped into patches, typed as a pond, bare sand and tailings, or a fresh clearing, and scored for priority from their size, how fast they grew, whether they touch a protected area or Indigenous land, how far they are from a road or river, and the confidence. The pipeline then checks itself against held-out map blocks, Hansen forest loss, and points we checked by eye in Google Earth, and builds the crackdown tables that the page displays.

## Architecture

```
RADARSAT-2 SLC zips (EODMS)
          |
   preprocessing: SNAP route or tminus/slc.py
          |
   sigma0 images in dB, one 10 m grid  <----  helper maps: Amazon Mining Watch,
          |                                   Hansen forest loss, elevation, ...
    +-----+-------------------+
    |                         |
 rule detector          random forest (+ optional ResNet50 features)
    |                         |
    +-----------+-------------+
                |
   combine: both agree = high, one = medium
                |
   alert patches: type, size, priority
        |                    |
   accuracy checks     crackdown tables (inside vs outside La Pampa)
        |                    |
        +---------+----------+
                  |
         outputs/  ->  Streamlit page (app/web)
```

Everything between the stages is a single-band GeoTIFF on the same UTM 19S grid, which is what lets each stage be developed and tested on its own. The page is plain HTML, CSS and JavaScript in `app/web/`, wrapped by Streamlit, and it reads whatever the pipeline wrote to `outputs/`.

## Results

Scored on 2 km map blocks that the model never saw during training, against Amazon Mining Watch, the two main images give:

| Detector | Precision | Recall |
|---|---|---|
| Rule-based | 0.82 | 0.21 |
| Random forest, radar only | 0.49 | 0.71 |
| Random forest with ResNet50 features | 0.70 | 0.88 |
| Final alerts map (rule + best forest) | 0.75 | 0.38 |

On the crackdown, the Hansen forest-loss timeline of model-detected mining shows La Pampa dropping from 976 hectares a year (2015 to 2018) to 161 (2019 to 2021), a fall of 84 percent, while the land outside La Pampa went from 1,201 to 1,346 hectares a year. That agrees in direction with the independent report by the Monitoring of the Andean Amazon Project, which counted 92 percent less mining deforestation in La Pampa between February and June 2019 and the same months of 2018 (MAAP #104).

## Design decisions

The rule detector and the random forest are deliberately kept as two voices instead of being blended into one score. The rule is the careful one: on the held-out blocks 82 percent of the labelled pixels it flags are mapped mining, though it finds only about a fifth of the mapped mined area. The forest is the generous one and finds most of it at the price of extra false alarms. Someone deciding where to send an inspector wants to know which kind of alert they are looking at, so agreement between the two is what earns the label "high".

Alerts are about change, not about mines. The forest on its own would happily mark every existing mine in the scene, so a pixel only the model flagged has to have darkened by at least 1.5 dB before it becomes an alert. That keeps the list pointed at what is new.

The 3 dB threshold comes from the data. Between our two dates, untouched forest differs by about a third of a decibel on average, and 93 percent of 200 m blocks of it stay within 1 dB. The pixels the rule flags drop by a median of about 4 dB, with the largest changes above 7 dB. Three decibels sits well clear of the natural variation and still low enough to catch most real clearings.

The crackdown is judged by comparing La Pampa with the area around it, not by looking at La Pampa alone. A fall in clearing inside the box means little if it fell everywhere that year, because of weather or the price of gold. An interval that spans 19 February 2019 is left out of both the before and after averages, since it cannot honestly be assigned to either side.

Accuracy is measured on held-out 2 km blocks, not on random pixels, because neighbouring pixels look alike and random splits flatter the score. The labels come from optical imagery that is independent of the radar, and two further checks (Hansen forest loss and hand-checked points) use different sources again.

The first version stays with one polarization, one study area and two dates, so the pipeline is tested end to end on something that can be explained. It is built to get stronger as dates are added: the pipeline sorts scenes by date, confirms each detection against the next scene when one exists, and the RADARSAT-2 revisit of 24 days means clearing could be dated to within weeks. The next version would add the reserve boundary, Indigenous territories and road and river layers to the priority score, which are already wired in and switch on when the maps are supplied, and a way to feed field confirmations back into the labels. The page already records a checked, confirmed or no-mining status for each alert on the device.

Two preprocessing routes are kept on purpose. The Python route runs anywhere with no extra software, which makes the project easy to reproduce. The SNAP route applies terrain correction and produced the two images used here, which matters on the slopes at the edge of the study area.

## Repository layout

```
app/              the web page: app.py (Streamlit wrapper), dashboard.py, web/ (HTML, CSS, JS), assets/
tminus/           the pipeline: preprocessing, detectors, model, alerts, crackdown, accuracy
snap/             SNAP graph and run script for the terrain-corrected route
scripts/          align_stack.py, which puts all scenes on one grid
tests/            synthetic_run.py, an end-to-end test on made-up images
.streamlit/       theme for the page
requirements.txt  Python packages
SETUP.md          install, data, run order, settings, troubleshooting
```

`data/` and `outputs/` hold rasters and results and are not in git, except `data/processed/stack.json` and an empty `data/raw/` to drop the downloaded scenes into. The other folders are created when the pipeline first writes to them. Every setting and threshold lives in `tminus/config.py`. A file-by-file layout is in [SETUP.md](SETUP.md).

## Running it

You need Python 3.12 and the two processed radar images in `data/processed/`. Then, from the project folder:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tminus.labels
python -m tminus.pipeline
streamlit run app/app.py
```

The page opens at http://localhost:8501. There is no hosted version: it runs on your own machine. [SETUP.md](SETUP.md) covers everything else, including where the data comes from, how to preprocess raw radar zips, and what to do when something fails.

## Data and credits

The radar images are RADARSAT-2 Data and Products, from the RADARSAT-2 Tropical Forests dataset, which the Canadian Space Agency makes available through EODMS with Natural Resources Canada and MDA Space.

Neither the raw scenes nor the processed images are in this repository, and a fresh clone has no radar to show until you add your own. The reason is the licence, not file size. RADARSAT-2 imagery is licensed, not sold, and Maxar keeps ownership of it. The scenes in this dataset are single look complex files, which may not be posted on any public site. The clean images we make from them still count as derived image products, because they keep the pixel structure of the original, and those may only be shown in a viewing format that stops anyone manipulating the pixels, with the copyright notice beside them. A GeoTIFF in a public repository is the opposite of that. Work that keeps none of the original pixels, such as change polygons and statistics, falls into a different category that the licence lets us distribute, which is why the code and the method live here and the imagery does not. The team shares the processed images privately, and anyone with their own EODMS access can rebuild them from the raw scenes with the commands in [SETUP.md](SETUP.md).

RADARSAT-2 Data and Products © Maxar Technologies Ltd. (2017, 2021) – All Rights Reserved. RADARSAT is an official mark of the Canadian Space Agency.

Other sources: Amazon Mining Watch (Earth Genome, Pulitzer Center, Amazon Conservation, CC BY 4.0); Hansen/UMD/Google/USGS/NASA Global Forest Change v1.13; pretrained SSL4EO-S12 weights through TorchGeo; Sentinel-2 imagery, contains modified Copernicus Sentinel data 2021; the Copernicus 30 m elevation model for terrain correction; MAAP #104 for the crackdown comparison.

T-Minus was built for the Mission Accepted space hackathon (MDA Space, the Canadian Space Agency and ShiftKey Labs), Challenge 1, RADARSAT-2 for Change.
